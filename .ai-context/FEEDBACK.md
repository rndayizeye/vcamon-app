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

05-30-2026
the text is shifted such that check boxes are next to the wong label on the VCA chat and quick ghost page.
Remove the subtitle under Ghosting Analysis :"Case #1 — Test Patient · NCSDDC Visual Case Analysis (2022)"

Use Source Spread Analysis instead of "VERDICT". In the next text block use the "Why?" use Detail from the Criteria table that correspond to all that passed. This brings helps support the Verdict/ Source Spread analysis.
Under "Anchor symptoms" avoid using P1 since it means sex partner but we used it here to refer to patient 1- with the highest ranking symptoms or case 1. Use "Patient 1" instead. You dont need to specify that we are calling anchor patient "P1' in calclations. 

Under "What this scenario test" remove "Hypothesis" and make it one sentence. This scenario test whether [patient without sx name] infected [name of patient with symptoms]

For any text that is prsented to the user- use actual names not the variable name used to calculate VCA or ghosting.
Save ghosted in no rendering correctly.

Define Processing range in the "VCA Range-Based Ghosting Analysis" log also avoid variable names use actual names instead in the log.
Verdict that is ambiguous should not have a green color, its confusing.
Partner page: Add partner button is overlapping with the title Partners.
