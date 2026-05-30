# Quick VCA

A standalone, single-page tool for **testing the VCA syphilis ghosting
methodology with users**. No database, no login, no case management — you enter
two people's symptoms and exposure history and see who the method points to as
source vs. spread.

It deliberately reuses the production clinical engine
(`app/utils/clinical.py` + `app/utils/ghosting_plot.py`) rather than copying it,
so any fix to the methodology shows up here automatically.

## Run locally

From the repository root:

```bash
conda run -n ai_coding_env_311 streamlit run quickvca/quick_vca.py
# or, with the standalone deps only:
pip install -r quickvca/requirements.txt
streamlit run quickvca/quick_vca.py
```

Opens at http://localhost:8501.

## Deploy (Streamlit Community Cloud)

Point the app at this repo with:

- **Main file path:** `quickvca/quick_vca.py`
- **Requirements:** `quickvca/requirements.txt`

No secrets are required (unlike the full v1 app, there is no password gate).

## What it does

- **Presets** (sidebar) load known-answer scenarios, including the NCSDDC
  training's Carmela/Johannes example, an ambiguous asymptomatic-partner case,
  and an unrelated case. Each preset states the expected outcome so you can spot
  when a code change shifts a known answer.
- **Run** evaluates both directions across minimum/average/maximum
  natural-history constants and reports a verdict plus per-criterion results,
  scenario diagrams, the step-by-step log, and the interview period.
- **Feedback** — testers rate each verdict (Reasonable / Unsure / Wrong) with an
  optional note; download the accumulated session feedback as CSV.

## Reading the result honestly

- The "tiers" count (`n/3`) is how many natural-history settings keep a scenario
  plausible — a **plausibility** signal, not a probability or statistical
  confidence.
- ⚠ **Warnings** do not fail a scenario but weaken the story; always read them.
- **Known limitation:** when *both* people have a confirmed primary chancre, the
  engine does not yet cross-check a ghosted source chancre against the other
  person's actual chancre date, so the direction can be unreliable in that case.
  Lean on the dates and exposure windows. (Tracked as a follow-up in the
  engine review.)

## Notes

- Runs against an in-memory SQLite URL set at startup; the database is never
  created or written. SQLAlchemy is a dependency only because the shared engine
  imports a few enums from `app/db/models.py`.
