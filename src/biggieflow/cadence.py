"""The 6-field cadence control vector.

Defaults are working estimates to be fitted from data, not measured facts.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

ALLOWED_RHYME_BEATS = (2.0, 4.0, 2.5, 4.5)


@dataclass(frozen=True)
class CadenceVector:
    swing_8th: float = 0.20
    swing_16th: float = 0.10
    anacrusis_prob: float = 0.6
    cross_bar_span: int = 2
    rhyme_pair_beat: float = 4.5
    unstressed_accent: float = 0.4

    def __post_init__(self) -> None:
        if not 0.0 <= self.swing_8th <= 0.6:
            raise ValueError("swing_8th must be in [0.0, 0.6]")
        if not 0.0 <= self.swing_16th <= 0.5:
            raise ValueError("swing_16th must be in [0.0, 0.5]")
        if not 0.0 <= self.anacrusis_prob <= 1.0:
            raise ValueError("anacrusis_prob must be in [0.0, 1.0]")
        if self.cross_bar_span not in (1, 2, 3):
            raise ValueError("cross_bar_span must be 1, 2 or 3")
        if float(self.rhyme_pair_beat) not in ALLOWED_RHYME_BEATS:
            raise ValueError(f"rhyme_pair_beat must be one of {ALLOWED_RHYME_BEATS}")
        if not 0.0 <= self.unstressed_accent <= 1.0:
            raise ValueError("unstressed_accent must be in [0.0, 1.0]")

    def to_list(self) -> list[float]:
        """Flat numeric form for feeding a control module."""
        return [
            self.swing_8th,
            self.swing_16th,
            self.anacrusis_prob,
            float(self.cross_bar_span),
            float(self.rhyme_pair_beat),
            self.unstressed_accent,
        ]

    def to_dict(self) -> dict:
        return asdict(self)


def swing_offset_ms(bpm: float, swing_ratio: float) -> float:
    """Delay applied to an off-beat 8th note.

    A straight 8th off-beat sits half a beat after the downbeat. Swing ratio r
    pushes it later by r * (half-beat duration).
    """
    if bpm <= 0:
        raise ValueError("bpm must be positive")
    beat_ms = 60_000.0 / bpm
    return swing_ratio * (beat_ms / 2.0)
