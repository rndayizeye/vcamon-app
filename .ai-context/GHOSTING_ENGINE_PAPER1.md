# Ghosting Engine Paper 1 — Methods / Informatics / Design
_Last updated: 2026-05-22_

Working file for the first paper focused on the VCA ghosting engine as a computable,
explainable implementation of visual case analysis. This file is meant to preserve
research state, literature review progress, writing decisions, and open questions
across sessions.

---

## 1. Paper identity

- **Working label:** Paper 1
- **Paper type:** Methods / informatics / design paper
- **Primary contribution:** The ghosting engine, not the Streamlit UI
- **Core framing:** A computable, explainable expression of VCA for syphilis source-spread analysis
- **Secondary framing:** Reusable engine for case management and surveillance augmentation

---

## 2. Draft thesis

We translated the CDC Visual Case Analysis (VCA) ghosting methodology from a manual,
expert-driven plotting process into a reusable, explainable computational engine
that can support both routine syphilis case management and future surveillance-scale
source-spread analysis.

Short version:

> This is not just a case management app; it is a computable implementation of VCA.

---

## 3. Claims

### Claims supported now
- The engine operationalizes VCA ghosting logic in software.
- The engine is deterministic, explainable, and testable.
- The engine is decoupled from UI and persistence layers.
- The engine can be used in Streamlit, FastAPI, and future batch analytics workflows.
- The engine provides structured source/spread plausibility outputs.

### Claims requiring validation before strong use
- The engine reduces investigator time.
- The engine improves inter-investigator consistency.
- The engine flags clusters missed by routine surveillance.
- The engine plugs directly into all surveillance systems or CDC NBS without translation work.

### Writing guardrail
Prefer: **could support**, **may enable**, **is designed to**, **creates a foundation for**
unless validation evidence exists.

---

## 4. Core paper sections

1. Problem: manual VCA is clinically useful but hard to scale and standardize
2. Background: VCA / ghosting as an expert public health reasoning method
3. System design: framework-free engine architecture
4. Computational method: date inference, windowing, criteria evaluation, verdict generation
5. Explainability and reproducibility advantages
6. Application to routine case management
7. Potential application to surveillance augmentation
8. Interoperability direction, including FHIR-aligned representation possibilities
9. Limitations and safeguards
10. Future validation work

---

## 5. Literature review goals

### Goal A: Situate VCA and syphilis partner services
Find literature on:
- syphilis partner services / disease intervention specialist workflow
- visual case analysis and manual transmission reasoning
- temporal reasoning in STI investigation

### Goal B: Situate the informatics contribution
Find literature on:
- computable epidemiology / computable clinical logic
- explainable rule-based public health decision support
- digital case investigation and surveillance informatics

### Goal C: Situate interoperability potential
Find literature on:
- FHIR in public health surveillance
- FHIR for case reporting, STI surveillance, or case management
- interoperability approaches involving CDC/NNDSS/NBS ecosystems

### Goal D: Identify comparison language
Find literature on:
- manual vs computational workflow burden
- structured analytic engines vs black-box ML
- outbreak detection / source-spread inference / transmission plausibility tools

---

## 6. Search strategy scaffold

### Databases to search
- PubMed / MEDLINE
- Google Scholar
- Scopus or Web of Science (if available)
- IEEE Xplore (for informatics / architecture papers)
- ACM Digital Library (optional, for health informatics / decision support methods)
- CDC / public health agency websites for grey literature
- HL7 FHIR implementation guide repositories / documentation for interoperability context

### Search buckets

#### Bucket 1: Syphilis / VCA / partner services
- "syphilis" AND ("partner services" OR "contact tracing" OR "disease intervention specialist")
- "visual case analysis"
- "syphilis" AND ("source spread" OR transmission plausibility OR transmission network)
- "syphilis" AND (timeline OR temporal reasoning OR lesion onset)

#### Bucket 2: Rule-based / computable epidemiologic reasoning
- (computable OR rule-based OR algorithmic) AND (epidemiology OR public health) AND (reasoning OR inference)
- "clinical decision support" AND explainable AND rule-based
- "public health informatics" AND (decision support OR workflow automation)
- ("temporal reasoning" OR "time-based inference") AND public health

#### Bucket 3: Surveillance / outbreak analytics
- (surveillance OR outbreak detection) AND (transmission inference OR cluster detection)
- STI AND surveillance AND analytics
- syphilis AND surveillance AND cluster
- pairwise transmission AND epidemiology

#### Bucket 4: Interoperability / FHIR
- FHIR AND "public health"
- FHIR AND surveillance
- FHIR AND case reporting
- FHIR AND syphilis
- FHIR AND STI
- (NBS OR "National Electronic Disease Surveillance System" OR NEDSS) AND interoperability

### Search log template
| Date | Database | Query string | Filters | Hits | Notes |
|---|---|---|---|---:|---|
| YYYY-MM-DD | PubMed | "..." | last 10 years; English | 0 | |

---

## 7. Screening criteria

### Include
- Syphilis partner services, case investigation, or transmission analysis papers
- Public health informatics papers on computable or rule-based workflows
- Explainable decision-support or temporal inference methods relevant to epidemiology
- FHIR/public health interoperability papers relevant to surveillance or case workflows
- Methods, framework, implementation, review, or policy papers that help position the engine

### Exclude
- Purely molecular/genomic transmission papers with no workflow or analytic relevance
- Purely treatment/clinical management papers with no informatics or investigation relevance
- Black-box prediction papers unless useful as a contrast point
- Papers with no abstract/full text access unless clearly important and recoverable elsewhere

### Prioritization
1. Directly about syphilis investigation or partner services
2. Directly about public health informatics / computable surveillance workflows
3. Directly about FHIR in public health
4. Broader decision-support / explainability papers used only for framing

---

## 8. Data abstraction plan

### Minimum abstraction fields per paper
| Field | What to capture |
|---|---|
| Citation key | Short ID, e.g. `author_year_shorttitle` |
| Full citation | APA/Vancouver/plain text |
| Link / DOI | Persistent URL |
| Source type | Journal / conference / report / standard / grey lit |
| Domain | Syphilis / STI / PH informatics / FHIR / decision support |
| Study type | Methods / review / implementation / evaluation / commentary |
| Setting | Case management / surveillance / outbreak / informatics platform |
| Objective | Main purpose of paper |
| Data / workflow described | What process/system was studied |
| Relevance to Paper 1 | Why it matters to our manuscript |
| Key methods / concepts | Terms, models, or methods to reuse |
| Key findings | One to three bullet points |
| Quotable claim | Exact line or near-quote with page if useful |
| Limitations | Important constraints |
| Use in manuscript | Intro / background / discussion / interoperability / limitations |
| Priority | High / Medium / Low |
| Status | To screen / included / excluded / abstracted / cited |

### Synthesis fields for high-priority papers
- What gap does this paper leave open?
- Does it support the need for standardization, explainability, or scalability?
- Does it provide language for framing public health workflow burden?
- Does it support the interoperability argument?
- Is it a comparison point, supporting citation, or conceptual anchor?

---

## 9. Recommended tooling

### Reference management
- **Zotero** as the primary library manager
- Use folders/collections:
  - `Paper1_Methods`
  - `Paper1_Syphilis_VCA`
  - `Paper1_Public_Health_Informatics`
  - `Paper1_FHIR_Interoperability`
  - `Paper1_Maybe`
- Add tags:
  - `background`
  - `methods-positioning`
  - `comparison`
  - `FHIR`
  - `surveillance`
  - `case-management`

### PDF reading / annotation
- Zotero PDF reader, or
- Readwise / Highlights / built-in PDF annotations if already part of your workflow

### Extraction workspace
Choose one of the following:

1. **Spreadsheet-first**
   - Google Sheets / Excel / Airtable
   - Best for quick screening, sorting, and synthesis tables

2. **Notes-first**
   - Obsidian or Notion linked to Zotero citations
   - Best if you want concept notes and writing fragments tied to sources

3. **Hybrid (recommended)**
   - Zotero for library
   - Google Sheet or Airtable for abstraction table
   - This `.ai-context` file for strategy, gaps, and session continuity

### AI-assisted efficiency tools
Use cautiously and always verify against the source.
- Zotero + Better BibTeX for clean citation keys
- Zotero + annotation extraction plugins if you already use them
- AI assistant for:
  - turning abstracts into 3-bullet summaries
  - extracting candidate quotes
  - clustering papers by theme
  - drafting synthesis matrices

Rule: never cite from AI output unless the quote and claim were checked in the paper itself.

---

## 10. Suggested abstraction workflow

### Phase 1: broad capture
- Save papers liberally into Zotero
- Screen title/abstract only
- Mark status as `To screen`, `Included`, or `Excluded`

### Phase 2: focused abstraction
- Fully abstract only High-priority papers
- Capture one concise paragraph per included paper
- Assign each paper to a manuscript role:
  - problem framing
  - method framing
  - surveillance context
  - interoperability context
  - limitations / contrast

### Phase 3: synthesis
Group included papers into 5 buckets:
1. Manual VCA / syphilis investigation workflow
2. Decision-support / computable reasoning
3. Temporal / transmission plausibility methods
4. Surveillance analytics / cluster detection
5. FHIR / public health interoperability

### Phase 4: writing support
For each bucket, write:
- what is already known
- what is missing
- how our engine contributes

---

## 11. Candidate manuscript positioning statement

This paper presents a methods and informatics contribution: a framework-free,
explainable computational engine that operationalizes VCA ghosting logic for syphilis
source-spread plausibility analysis. Rather than replacing investigator judgment,
it standardizes the temporal and rule-based reasoning that has traditionally been
performed manually.

---

## 12. Open questions

- Which journal/outlet is the best fit for a methods-first paper?
- How much VCA history should appear in the background section?
- Should FHIR be a major section or a short future-direction section?
- Which engine outputs are best represented as FHIR `RiskAssessment` vs `Observation`?
- What comparison literature best contrasts explainable rule-based logic with black-box ML?

---

## 13. Draft abstract (v1 — 2026-06-08)

**Background:** Syphilis incidence in the United States increased approximately 80% between 2018 and 2022, intensifying demand for reproducible, scalable case investigation methods. Visual Case Analysis (VCA) is a seven-step source-spread reasoning methodology developed by the National Coalition of STD Directors that enables disease intervention specialists to determine transmission plausibility between index cases and partners through structured temporal analysis of lesion windows. In practice, VCA is performed manually, making it difficult to standardize across investigators or extend to high-caseload surveillance environments.

**Objective:** To describe the design and implementation of a computational engine that operationalizes the VCA ghosting methodology as deterministic, explainable, framework-free software.

**Methods:** The engine accepts case and partner clinical data — symptom onset, lesion type, exposure windows, and laboratory staging — and executes VCA's seven-step pipeline: inferring key clinical dates, constructing ghosted source and spread lesion windows from published syphilis natural history constants, evaluating four transmission criteria, and generating a structured plausibility verdict. The engine is implemented in pure Python with no framework dependencies, enabling deployment across interactive interfaces, web APIs, and batch analytics pipelines.

**Results:** For each evaluated case-partner dyad, the engine produces deterministic, auditable outputs: source and spread plausibility tiers, a confidence score, and per-criterion rationale strings. All logic is unit-tested and decoupled from persistence and presentation layers.

**Conclusions:** This engine translates expert VCA reasoning into a standardized, reproducible computational form, creating a foundation for consistent case management and future surveillance-scale source-spread analysis. Its output structure is designed to align with the `qualitativeRisk` element of the HL7 FHIR RiskAssessment resource to support integration with public health data exchange systems.

_Confirmed: seven-step pipeline (matches 7 key entry points in code); four transmission criteria (exposure overlap, anatomical compatibility, latency to secondary, natural progression order) each evaluated across five range scenarios._

---

## 14. Near-term next actions

- [ ] Draft a 150-250 word abstract for Paper 1
- [x] Build the initial search strings in PubMed and Google Scholar — done 2026-05-31
- [ ] Set up Zotero collections and tags — import from `PAPER1_ARTICLE_TRACKER.csv`
- [x] Create a screening / abstraction spreadsheet — `PAPER1_ARTICLE_TRACKER.csv` populated 2026-05-31; 30 sources as of 2026-06-07
- [x] Identify 10-15 anchor papers for the first pass — 24 confirmed sources entered 2026-05-31
- [ ] Draft a background section skeleton from the literature buckets
- [x] Pass 2 gap fill — completed 2026-06-07:
  - [x] CDC STI Treatment Guidelines 2021 (Workowski et al.) — `workowski_2021_sti_guidelines`; natural history constants confirmed (incubation 10–90 days; primary lesion 2–6 weeks; secondary onset 2–24 weeks after primary; early latent = within 1 year)
  - [x] Temporal reasoning methods — `peleg_2003_comparing_cig_models` (JAMIA; canonical CIG model comparison) + `madkour_2016_temporal_data_clinical` (CMPB review; Allen's interval algebra)
  - [x] Rule-based computable phenotyping — `banda_2018_electronic_phenotyping` (Annual Review BDS; primary) + `richesson_2013_ehr_phenotyping_collaboratory` (JAMIA; definitional anchor)
  - [x] FHIR RiskAssessment resource — `hl7_2019_fhir_r4_riskassessment`; resource confirmed in R4; strong fit for VCA outputs; gap: probability[x] needs ordinal mapping or custom extension for tier scores
- [ ] **CRITICAL ACTION: locate CDC 1992 VCA DIS training document** — contact CDC archives or NCSD/NACCHO directly
- [ ] Full-text abstraction: complete "To abstract" High-priority papers in tracker (pavia_2019, keshavjee_2022, cope_2022, cdc_1992, rankin_2025, workowski_2021, peleg_2003, banda_2018)
- [ ] Run formal PubMed queries B1/B2/C1/C2/D1/D2 (exact strings in § 5 of PAPER1_LITERATURE_SEARCH.md) with filter logs before submission
- [x] ~~Recent syphilis surveillance 2020–2026~~ — resolved by Rankin 2025
- [x] ~~DIS history backbone~~ — resolved by Pavia 2019 + Keshavjee 2022
- [x] ~~FHIR RiskAssessment verification~~ — resolved 2026-06-07

---

## 14. Session log

### 2026-05-22
- Created a dedicated persistent workspace for Paper 1.
- Confirmed the methods / informatics / design framing as the primary article direction.
- Defined initial literature search buckets: syphilis/VCA, public health informatics, surveillance analytics, and FHIR interoperability.
- Defined a minimum data abstraction schema and recommended a Zotero + spreadsheet hybrid workflow.

### 2026-05-31
- Completed Pass 1 anchor literature search across all 4 domains (A–D) using AI-assisted web search harness.
- 17 sources identified, confirmed, and entered into `PAPER1_ARTICLE_TRACKER.csv`.
- Search log recorded in `PAPER1_LITERATURE_SEARCH.md` § 11.
- Key anchors secured per domain:
  - **A (Syphilis/DIS/VCA):** Peterman 2024 systematic review; Hurt 2018 on-site DIS outcomes; Peterman 2022 PN effectiveness; NCSD 2022 VCA training; Cope 2019 DIS changing roles
  - **B (PHI/Decision Support):** Yasnoff 2000 PHI definition; CDC MMWR 2012 PHI surveillance; Amann 2022 explainability in CDSS; StatPearls syphilis natural history (engine constants grounding)
  - **C (Surveillance/Transmission):** Doherty 2012 sexual networks NC; Fox 2024 STI mapping Forsyth County; Klovdahl 2017 network SF; CSTE outbreak detection guidance
  - **D (FHIR/Interoperability):** Ward 2017 NBS workflow; Vorisek 2022 FHIR systematic review; HL7 eCR IG v2.1.2; CDC 2023 FHIR Playbook
- Pass 2 gaps identified: peer-reviewed VCA methodology companion; CDC STI guidelines 2021 for natural history constants; FHIR RiskAssessment resource verification; additional syphilis surveillance recency (2020–2026); computable phenotyping methods papers for Domain B.
- Next action: import tracker rows into Zotero; obtain full texts for 9 High-priority papers marked "To abstract"; run Pass 2 targeted gap-fill searches.

### 2026-06-07
- Pass 2 gap-fill completed via AI-assisted web search (WebSearch + WebFetch).
- 6 new sources added; tracker now has 30 entries.
- **Gap 1 (CDC STI Guidelines):** `workowski_2021_sti_guidelines` — MMWR 2021, DOI 10.15585/mmwr.rr7004a1, PMID 34292926. Natural history constants confirmed: incubation 10–90 days, primary lesion 2–6 weeks, secondary onset 2–24 weeks after primary, early latent = within 1 year.
- **Gap 2 (Temporal reasoning):** `peleg_2003_comparing_cig_models` (JAMIA 2003, PMID 12509357) — canonical CIG model comparison; shows all six formalisms support start-time constraints but diverge on end-time/duration, directly framing the VCA engine's temporal constraint approach. Secondary: `madkour_2016_temporal_data_clinical` (CMPB 2016, PMID 27040831) — Allen's interval algebra review.
- **Gap 3 (Computable phenotyping):** `banda_2018_electronic_phenotyping` (Annual Review BDS 2018, PMID 31218278) — primary; rule-based phenotyping paradigm, >95% accuracy for structured-criteria conditions. Secondary: `richesson_2013_ehr_phenotyping_collaboratory` (JAMIA 2013) — definitional anchor for "computable phenotype."
- **Gap 4 (FHIR RiskAssessment):** `hl7_2019_fhir_r4_riskassessment` — resource verified in R4; prediction.qualitativeRisk + prediction.rationale + basis cover the VCA output structure; minor gap on ordinal tier scores (needs extension or mapping).
- Remaining open gaps: CDC 1992 VCA training document (still not located); formal PubMed query execution for reproducible search log.

### 2026-05-31 (Session 2 — integrated from parallel chat)
- Integrated 7 new sources from a parallel research session into `PAPER1_ARTICLE_TRACKER.csv`; tracker now has 24 entries.
- Enriched `ncsddc_2022_vca_training` entry: confirmed author Emily Fussell; added NACCHO VCA chart citation note; added 1930s contact tracing history detail from slide deck.
- Key new finds:
  - `cdc_1992_vca_dis_training` — VCA provenance traces to CDC 1992 DIS training document (cited via Oregon PH Division); full document not yet located — flagged as critical action item.
  - `rankin_2025_syphilis_trends` — Rankin et al. 2025, BMC Inf Dis — resolves Domain C recency gap; 80% syphilis resurgence 2018–2022.
  - `pavia_2019_dis_history` — DIS workforce history from 1930s; 1940s CDC federalization.
  - `keshavjee_2022_ct_history` — Contact tracing history syphilis to COVID-19; ethical evolution framing.
  - `rothenberg_2003_social_network` — Havlak 1960s "lot system" as intellectual precursor to VCA cluster reasoning.
  - `cope_2022_unnamed_partners` — Unnamed partners study; directly motivates index-case-level VCA analysis.
  - `golden_2010_dis_embedded` — DIS embedding effectiveness; lower priority supporting citation.
- Identified methodology limitation: both AI-assisted sessions used web-snippet-level search, not formal PubMed queries. PubMed B/C/D bucket queries must be run formally before submission.
- Updated Pass 2 gap list: 4 gaps remain (CDC 1992 document, CDC STI guidelines 2021, temporal reasoning methods, rule-based case identification).
