Partner form: DONE (2026-05-25) — Removed manual historical_primary_chancre / historical_primary_date dropdowns from PartnerForm. Now derived automatically via deriveHistoricalPrimary(symptoms, treatment_date) on submit, matching CaseForm behaviour.
General: DONE (2026-05-25) — Non-reactive treponemal guard added to analyze_case_partner_ghosting. If either case or partner has a confirmed Non-reactive treponemal result, the endpoint returns 422 with a message naming the person and the test type before analysis runs.
Analytics: DONE (2026-05-25) — All analytics components updated to use layman's terms with technical terms in parentheses. Summary cards, centrality table (columns renamed + expandable definitions), cluster panel (renamed sections + descriptions), and node table (role column humanized) all have plain-language labels and explanations.
VCA chart: DONE (2026-05-25) — All primary (red) and secondary (purple) symptoms now plotted per person. `buildSymptomBars()` reads `classification` field directly from SymptomEntry and renders every classified symptom with its own onset marker, duration bar, and inoculation points. Chart enforces a 12-month minimum window centered on the data midpoint. Legend updated to distinguish primary vs secondary colors.
Sex type: DONE (2026-05-25) — RelationshipEditor now collects op_body_parts / partner_body_parts via side-by-side checkbox grid (penis, vagina/vulva, anus/rectum, mouth). Clinical engine replaced _exposure_modality_compatible with _sex_type_compatible using per-person body-part lists. DB migration ec2923821476 applied.
Ghosting: DONE (2026-05-25)
- Hypothesis text added to each scenario tab: explains in plain language who infected whom and what the ghosted lesion represents.
- Inoculation date sub-row added under the Exposure criterion: shows avg inoculation date back-calculated from case1's symptom onset and whether it falls within the ghosted lesion window.
- Latency now shown in 3 rows (Optimistic/min, Expected/avg, Conservative/max); all other criteria show expected range only.
- VerdictContext panel added below verdict badge: per-criterion plain-language explanation of each failure (e.g. "ghosted source lesion would have occurred after secondary — violates primary-before-secondary order").
- QuickGhostPage SymptomEditor: changed from grid to flex-wrap layout; onset date and duration inputs no longer overlap on narrow containers.
05-26-2026
VCA chart redesign: PLANNED — approved plan at `.claude/plans/read-ai-context-feedback-md-new-feedback-async-canyon.md`. Implement at start of next session.
- Inoculation: one set per person (primary preferred, secondary fallback). Primary → ► max, ▲ avg, ◄ min. Secondary → ▲ avg only.
- Draw line from max inoculation point to treatment date, labeled "Infectious window".
- Treatment date: vertical line (replaces ★ star marker).
- Non-reactive labs: gray dashed vertical line per non-reactive result (RPR titer=Neg or treponemal result=Non-reactive).
- Overlap fix: exposure/interview at y-22, symptoms at y, inoculation at y+22, ghosted lesions at y+34.
- Reference screenshot: documents/Screenshot_vca.png

05-30-2026 — DONE (commit 6ed7596)
- Checkbox alignment: CSS width:auto fix for input[type="checkbox"]; .badge-pass/.badge-fail/.badge-warn/.badge-na color classes added.
- VCA Timeline subtitle removed (case #/partner count/symptom count line gone from header).
- "Source Spread Analysis" label: already present; Why? block surfaces passing criteria detail strings.
- Anchor symptom: eyebrow uses actual patient name ("ANCHOR SYMPTOM — SMITH, JOHN"), no P1.
- "What this scenario tests": one sentence using actual names ("This scenario tests whether Bob infected Alice."), no "Hypothesis:" prefix.
- All user-facing text uses actual names: criteria detail strings use patient names (not "Case2"), log uses "Anchor patient — [name]" / "Comparison patient — [name]", range descriptions plain-language, confidence summary uses names.
- Save ghosted rendering fixed: savedOk resets on new analysis run; placeholder hidden when savedOk=true.
- Log: "Processing Range" replaced with plain descriptions ("Optimistic range — minimum constants", etc.); criterion keys humanized ("Latency to secondary", "Anatomical compatibility", etc.).
- Ambiguous verdict: VerdictBanner turns amber when verdict contains "⚠" (overlap warning) — was showing green confusingly.
- Partner Add button overlap: fixed with inline flex + space-between (commit dd084c7).
