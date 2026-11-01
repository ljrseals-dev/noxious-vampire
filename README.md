# BiggieFlow

Consent-first tooling for rap-cadence research: a 6-field cadence control vector, a consent gate for voice enrollment and generation, and a cost-capped parameter search.

This repo is the **safety and control layer plus the prompts**. It does not include a TTS model, tokenizer, vocoder or pretrained weights; those are described in the master prompt as the next build steps.

## What is here

| Path | What it does |
|---|---|
| `prompts/biggieflow_llm_prompt.md` | Text-only LLM system prompt: writes original verses with bar, syllable, stress and timing annotations |
| `prompts/biggieflow_voiceclone_master_prompt.md` | Full architecture prompt (consent-first) for a coding agent or architect model |
| `src/biggieflow/cadence.py` | `CadenceVector` with range validation, and swing-offset math |
| `src/biggieflow/consent.py` | Consent records, liveness challenge, enrollment, revocation, hash-only audit log |
| `src/biggieflow/search.py` | `plan()` cost guard, hard caps (64 nodes, 10^9 combos, default $5), `kill()`, `run_search()` |
| `tests/` | pytest suite for all three modules |

## Quick start

```bash
pip install -e ".[dev]"
pytest
```

```python
from biggieflow import CadenceGrid, plan, run_search

grid = CadenceGrid()
approved = plan(grid, cost_per_eval_usd=0.01)          # refuses if over $5
best = run_search(approved, grid, score_fn=my_scorer)   # top 5 by your metric
```

## Consent rules (enforced in code)

- No consent record means no liveness challenge, no enrollment, no generation.
- Enrollment needs a live read-aloud of a random phrase, so replayed recordings fail.
- Deceased people cannot be registered. The Notorious B.I.G. cannot consent: the project models cadence as a *style* only, never his timbre.
- Each generation call must match a permitted use in the consent record.
- `revoke()` deletes the embedding and blocks all later use.
- The audit log stores a SHA-256 of each prompt, never the text or audio.

## Not verified

- The NVIDIA DeepSeek-V4.1-Flash reference in the prompts is a design heuristic only; its details are unverified.
- `search.py` is a local implementation of the plan/kill/cost-ceiling contract. It does not use `ljrseals-dev/redesigned-fiesta`, whose interface is unverified.
- Cadence defaults are working estimates, not measured values.
- Watermarking (rule C4) is specified in the prompt but not implemented here yet.

## Data and licensing

Use lyric and audio sources only within their terms and robots.txt. Do not commit copyrighted lyrics, audio or embeddings (see `.gitignore`). Add a LICENSE of your choice before publishing.
