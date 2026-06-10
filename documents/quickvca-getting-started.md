# Quick VCA — Getting Started

**Live app:** https://quickghost.streamlit.app

Quick VCA is a sandbox for testing the NCSDDC ghosting methodology against real-world timing scenarios. It runs the same clinical engine used in VCA Monitor, but requires no login and stores nothing — you enter two people's data and get an immediate result.

---

## Before you begin

**This tool is NOT HIPAA compliant.** You must acknowledge this on first load. Use fabricated or fully anonymized scenarios only — no names, real DOBs, or any PHI.

Enter your name or tester ID in the sidebar before running scenarios. It attaches to your feedback entries so responses can be attributed during analysis.

---

## Investigation modes

**Single Pair** — the standard workflow. You evaluate one pair head-to-head: who infected whom?

**Multi-Partner (OP + up to 5 contacts)** — enter the index patient once, then fill in up to five contacts across separate tabs. The app runs a pairwise analysis for each contact and ranks them by how strongly the timing supports them as the source. Use this when you have a cluster and want to quickly triage which contact the timeline points to first.

---

## Entering data

### Symptoms

Add one row per symptom. The fields map directly to VCA chart inputs:

| Field | What to enter |
|---|---|
| **Symptom type** | The stage of the lesion observed or reported. "Historical Primary" = patient recalls a chancre but it has healed. "Ghosted Primary/Secondary" = derived, not observed — only the engine should generate these, not you. |
| **Onset date** | The date the lesion *began*, per patient report. If the patient presented to the clinic and the chancre was observed that day (not self-reported), enter the exam date and set Duration to 0 — the engine will back-calculate a probable onset using the max primary duration. |
| **Duration (days)** | How many days the lesion lasted. Enter **0** to tell the engine to use the average for that stage. Enter a known value (e.g. 7 days) if it's charted. |
| **Anatomical site** | Required only for the anatomical compatibility criterion. Select the site of a primary chancre. Leave blank for secondary symptoms. |

### Exposure window

Enter the date range during which the two people had sexual contact with each other — this is each person's own account. In a typical interview you get one set of dates per pair; enter the same window on both sides unless the accounts differ materially.

### Sex type(s)

Multiselect. Drives the anatomical compatibility check: a penile chancre in someone who reports only oral contact will warn or fail that criterion.

### Treatment date

Enter if known. The engine uses this to clip the infectious window — a person is only infectious up to treatment. Leaving it blank is safe; the window will be left open.

### Last negative test *(optional)*

If the person had a documented negative treponemal or RPR test before symptoms, enter that date. The engine applies a floor: the inoculation date cannot be placed earlier than 90 days before the test (the maximum incubation period). This shortens implausibly long infectious windows without overstating certainty. It only applies if it would make the window *shorter*, never longer.

---

## Analysis modes

**Traditional VCA** runs the four criteria once, using average natural-history constants — this is the standard NCSDDC methodology you recognize from training.

**Comprehensive** re-runs all four criteria five times, each time using a different set of constants (minimum, average, maximum, fast-infection/slow-disease, slow-infection/fast-disease). It reports a tier score (0–5) and a confidence label. Use this when you want to see how sensitive the conclusion is to timing assumptions, or when a case is borderline under average constants alone.

---

## How the engine reasons

Understanding what the app is actually computing helps you evaluate whether its output is clinically sensible.

**Case1 selection.** The engine picks the person with the highest-ranked symptom as the "anchor" — Primary Chancre outranks Historical Primary, which outranks Secondary. When both people have a primary chancre, the one with the earlier onset wins. The anchor patient's symptom is used to work backward through the natural-history chain.

**Date1 — inoculation date.** Back-calculated from the anchor symptom's onset by subtracting the incubation period (10–21–90 days). Under average constants: onset − 21 days. This is the estimated date Case1 was infected.

**Ghosted source lesion.** Centered on Date1 ± half the primary duration. This represents the inferred window when the *source* (Case2) was infectious — the chancre the source would have had around the time they transmitted to Case1. The source scenario asks: does this window overlap the reported contact window?

**Ghosted spread lesion.** Centered on Date2 (the midpoint of Case1's infectious period). This represents Case1's potential infectious window *toward* the comparison patient. The spread scenario asks: does *this* window overlap the contact window?

**The four criteria.** Both scenarios are evaluated against:

1. **Exposure overlap** — the relevant infectious window must intersect the reported contact dates. A miss of ≤10 days warns rather than fails (half the average incubation, per the NCSDDC margin).
2. **Anatomical compatibility** — each person's primary chancre site must match a body part they reported using. Evaluated for both parties independently.
3. **Latency to secondary** — if the comparison patient has secondary symptoms, enough time (0–70 days) must separate the ghosted chancre's end from secondary onset.
4. **Natural progression order** — the comparison patient's symptoms must follow the expected sequence. If secondary symptoms appear before the ghosted primary window resolves, the scenario violates known disease biology.

A **⚠ Warn** does not fail a scenario — it flags a weak point. Read warn detail before dismissing it.

**Important Dates** (shown below the verdict) gives you:
- When Case1 was likely infected (Date1)
- How far back to elicit contacts (the interview period: 125 days for primary, 237 days for secondary)
- The source's estimated infectious window

---

## Reading the verdict

| Label | Meaning |
|---|---|
| **SOURCE** | The timing supports Case2 infecting Case1 |
| **SPREAD** | The timing supports Case1 infecting Case2 |
| **AMBIGUOUS** | Both directions pass under the same constants — manual review required |
| **UNRELATED** | Neither direction is supported on this timeline |

The verdict is a **plausibility check, not a probability.** It tells you whether the dates are consistent with the proposed transmission — not that transmission definitely occurred. Clinical and behavioral context always takes precedence.

Known limitation: when both people have a confirmed primary chancre, double-check that the ghosted source window actually overlaps the comparison patient's own chancre dates. The engine does cross-check this, but when the windows are close it may warn rather than fail — lean on the raw dates in that case.

---

## Presets

The sidebar includes built-in scenarios for testing. Each preset states the expected outcome so you can spot if the engine gives an unexpected answer. The **Carmela/Johannes** preset is drawn from NCSDDC training slide 17. Use presets to orient yourself before entering your own scenarios.

---

## Recording feedback

After any result, a feedback panel appears below the VCA chart.

1. Select **Reasonable**, **Unsure**, or **Wrong**.
2. Add a note — especially for Unsure and Wrong. Useful notes include: what the clinical picture suggested vs. what the engine returned, whether a date was uncertain, or whether you think a criterion result is wrong.
3. Click **Record feedback**.

Your entries are stored to a shared log. You can also download your session's feedback as a CSV from the button that appears after your first submission.

**For session coordinators:** all feedback across all testers is downloadable from the **Admin / Beta export** expander in the sidebar. Export at the end of each testing session. Feedback is keyed by tester ID, scenario, analysis mode, and verdict — the log is the primary instrument for evaluating whether the engine's conclusions match DIS clinical judgment.
