# Quick VCA

**Live:** https://quickghost.streamlit.app

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

Live at **https://quickghost.streamlit.app** — deployed from `main`, branch tracked automatically.

To redeploy from scratch:

- **Main file path:** `quickvca/quick_vca.py`
- **Requirements:** `quickvca/requirements.txt` (auto-discovered)
- **Secrets required:** `SUPABASE_URL` and `SUPABASE_ANON_KEY` (for persistent feedback logging)

> ⚠ **NOT HIPAA COMPLIANT.** On first load, users must acknowledge this before
> the form renders. Do not enter real patient data. Use fabricated or fully
> anonymized scenarios only.

## What it does

- **Presets** (sidebar) load known-answer scenarios, including the NCSDDC
  training's Carmela/Johannes example, an ambiguous asymptomatic-partner case,
  and an unrelated case. Each preset states the expected outcome so you can spot
  when a code change shifts a known answer.
- **Single Pair** mode — evaluate two people head-to-head.
- **Multi-Partner** mode — enter an index patient once and up to 5 contacts;
  results are ranked by plausibility as source.
- **Analysis modes** — *Traditional VCA* (average constants, NCSDDC methodology)
  and *Comprehensive* (5 natural-history tiers with confidence score).
- **Feedback** — testers rate each verdict (Reasonable / Unsure / Wrong) with an
  optional note. Feedback is written to `quickvca/feedback_log.jsonl` on the
  server and persists across sessions. Download all entries as CSV from the
  **Admin / Beta export** expander in the sidebar.

## Beta testing

1. Each tester enters their name/ID in the sidebar before running scenarios.
2. Use only the provided presets or invented data — no real patient information.
3. Rate each verdict after reviewing it.
4. The session operator downloads all feedback from **Admin / Beta export** at the
   end of the session. `feedback_log.jsonl` is git-ignored and never committed.

## Reading the result honestly

- The "tiers" count (`n/5`) is how many of five natural-history constant sets keep
  a scenario plausible — a **plausibility** signal, not a probability or
  statistical confidence.
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
