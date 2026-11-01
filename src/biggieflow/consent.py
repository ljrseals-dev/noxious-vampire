"""Consent gate for voice enrollment and generation.

Hard rules (see prompts/biggieflow_voiceclone_master_prompt.md, Section 2):
- No consent record, no enrollment and no generation.
- Enrollment needs a live read-aloud of a random phrase (liveness check).
- Revocation deletes the timbre embedding and blocks future generation.
- Every generation request is audit-logged (prompt hash only, never raw audio).
- Deceased or non-consenting people cannot be enrolled; style-only use is fine.
"""

from __future__ import annotations

import hashlib
import json
import secrets
import time
from dataclasses import dataclass, field
from datetime import date

_WORDS = (
    "river", "copper", "lantern", "meadow", "falcon", "marble", "ember", "harbor",
    "willow", "thunder", "velvet", "compass", "orchid", "granite", "saffron", "tundra",
)


class ConsentError(Exception):
    """Raised whenever a consent rule blocks an action."""


@dataclass
class ConsentRecord:
    speaker_id: str
    name: str
    signed_on: date
    expires_on: date
    permitted_uses: tuple[str, ...]
    revocation_contact: str
    deceased: bool = False

    def is_active(self, today: date | None = None) -> bool:
        today = today or date.today()
        return (not self.deceased) and self.signed_on <= today <= self.expires_on


@dataclass
class ConsentRegistry:
    records: dict[str, ConsentRecord] = field(default_factory=dict)
    embeddings: dict[str, list[float]] = field(default_factory=dict)
    revoked: set[str] = field(default_factory=set)
    audit_log: list[dict] = field(default_factory=list)
    _pending_phrases: dict[str, str] = field(default_factory=dict)

    # -- consent records -------------------------------------------------
    def register(self, record: ConsentRecord) -> None:
        if record.deceased:
            raise ConsentError("C3: deceased people cannot consent; use style-only output")
        if not record.permitted_uses:
            raise ConsentError("C1: consent record must list permitted uses")
        if record.expires_on <= record.signed_on:
            raise ConsentError("C1: consent expiry must be after signing date")
        if not record.revocation_contact:
            raise ConsentError("C1: consent record needs a revocation contact")
        self.records[record.speaker_id] = record
        self.revoked.discard(record.speaker_id)
        self._log("register", record.speaker_id)

    # -- liveness --------------------------------------------------------
    def start_liveness(self, speaker_id: str) -> str:
        """Return a random phrase the speaker must read aloud live."""
        self._require_active(speaker_id)
        phrase = " ".join(secrets.choice(_WORDS) for _ in range(4))
        self._pending_phrases[speaker_id] = phrase
        return phrase

    def enroll(self, speaker_id: str, embedding: list[float], spoken_phrase: str) -> None:
        """Store a timbre embedding only after consent and a matching live phrase."""
        self._require_active(speaker_id)
        expected = self._pending_phrases.pop(speaker_id, None)
        if expected is None:
            raise ConsentError("C2: no liveness challenge was issued")
        if spoken_phrase.strip().lower() != expected:
            raise ConsentError("C2: liveness phrase mismatch; enrollment rejected")
        if not embedding:
            raise ConsentError("empty embedding")
        self.embeddings[speaker_id] = list(embedding)
        self._log("enroll", speaker_id)

    # -- generation ------------------------------------------------------
    def authorize_generation(self, speaker_id: str, prompt: str, use: str) -> list[float]:
        """Gate for every generation call. Returns the timbre embedding."""
        self._require_active(speaker_id)
        record = self.records[speaker_id]
        if use not in record.permitted_uses:
            self._log("denied_use", speaker_id, prompt)
            raise ConsentError(f"C1: use '{use}' is not permitted by this consent record")
        if speaker_id not in self.embeddings:
            raise ConsentError("speaker is not enrolled")
        self._log("generate", speaker_id, prompt)
        return self.embeddings[speaker_id]

    # -- revocation ------------------------------------------------------
    def revoke(self, speaker_id: str) -> None:
        self.embeddings.pop(speaker_id, None)
        self._pending_phrases.pop(speaker_id, None)
        self.revoked.add(speaker_id)
        self._log("revoke", speaker_id)

    # -- internals -------------------------------------------------------
    def _require_active(self, speaker_id: str) -> None:
        if speaker_id in self.revoked:
            raise ConsentError("C5: consent was revoked")
        record = self.records.get(speaker_id)
        if record is None:
            raise ConsentError("C1: no consent record for this speaker")
        if not record.is_active():
            raise ConsentError("C1: consent record is expired or not yet valid")

    def _log(self, event: str, speaker_id: str, prompt: str | None = None) -> None:
        entry = {"t": time.time(), "event": event, "speaker_id": speaker_id}
        if prompt is not None:
            entry["prompt_sha256"] = hashlib.sha256(prompt.encode()).hexdigest()
        self.audit_log.append(entry)

    def export_audit_log(self) -> str:
        return json.dumps(self.audit_log, indent=2)
