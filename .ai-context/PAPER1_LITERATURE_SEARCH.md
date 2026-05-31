# Paper 1 Literature Search Worksheet
_Last updated: 2026-05-22_

This worksheet supports the methods / informatics / design paper on the VCA ghosting engine.
Use it to run a structured, reproducible, targeted literature search and feed results into
`PAPER1_ARTICLE_TRACKER.csv`.

Related files:
- `GHOSTING_ENGINE_PAPER1.md` — paper framing, claims, and synthesis plan
- `PAPER1_ARTICLE_TRACKER.csv` — screening + abstraction table

---

## 1. Search objective

Identify literature that helps position the ghosting engine as:

1. a computable implementation of manual VCA reasoning,
2. an explainable public health informatics method,
3. a potentially scalable analytic engine for surveillance augmentation, and
4. a future interoperability candidate for FHIR-aligned public health systems.

This is a **targeted narrative / methods-positioning search**, not a formal systematic review.

---

## 2. Search domains

### Domain A — Syphilis investigation and partner services
Focus:
- syphilis case investigation
- partner services
- contact tracing
- disease intervention specialists
- transmission/source-spread reasoning
- visual case analysis / ghosting

### Domain B — Public health informatics and explainable decision support
Focus:
- computable public health reasoning
- rule-based systems
- explainable decision support
- workflow automation
- temporal reasoning in epidemiology

### Domain C — Surveillance analytics and transmission inference
Focus:
- surveillance analytics
- cluster identification
- outbreak detection
- temporal/plausibility inference
- digital case investigation support

### Domain D — Interoperability / FHIR / NBS context
Focus:
- FHIR in public health
- electronic case reporting
- surveillance interoperability
- NBS / NEDSS / CDC ecosystem relevance

---

## 3. Databases and sources

### Core databases
1. **PubMed / MEDLINE**
2. **Google Scholar**

### Secondary databases
3. **Scopus** or **Web of Science**
4. **IEEE Xplore**
5. **ACM Digital Library**

### Grey literature / standards
6. **CDC / MMWR / partner services guidance**
7. **HL7 FHIR documentation and implementation guides**
8. **APHL, CSTE, ONC, CDC interoperability resources**

---

## 4. Search execution plan

## Pass 1 — Anchor paper search
Goal: find 10–15 high-value anchor sources across the 4 domains.

Target:
- 3–5 papers/reports on syphilis investigation / partner services / VCA-related workflow
- 2–4 on public health informatics / explainable decision support
- 2–4 on surveillance / transmission inference / cluster detection
- 2–4 on FHIR / public health interoperability

## Pass 2 — Citation chaining
For each anchor paper:
- scan reference list
- use cited-by tools
- search author names
- search key phrases that recur

## Pass 3 — Gap filling
Search only for missing concepts:
- explainability language
- workflow standardization
- temporal reasoning methods
- FHIR/public health implementation specifics

---

## 5. Exact starter queries

## PubMed queries

### Query A1 — Syphilis partner services / contact tracing
```text
("Syphilis"[Mesh] OR syphilis[tiab])
AND
("Partner Notification"[Mesh] OR "partner services"[tiab] OR "contact tracing"[tiab] OR "disease intervention specialist"[tiab] OR "case investigation"[tiab])
```

Suggested filters:
- English
- Humans
- No date limit initially; narrow later if too broad

### Query A2 — Syphilis + temporal or source-spread reasoning
```text
(syphilis[tiab])
AND
("visual case analysis"[tiab] OR ghosting[tiab] OR "source spread"[tiab] OR "transmission plausibility"[tiab] OR "temporal reasoning"[tiab] OR timeline[tiab])
```

### Query B1 — Public health informatics + rule-based / computable support
```text
("public health informatics"[tiab] OR "decision support"[tiab] OR "clinical decision support systems"[Mesh])
AND
(rule-based[tiab] OR explainable[tiab] OR computable[tiab] OR algorithmic[tiab])
AND
("public health"[tiab] OR surveillance[tiab] OR epidemiology[tiab])
```

### Query B2 — Temporal reasoning in public health or epidemiology
```text
(("temporal reasoning"[tiab] OR "time-based inference"[tiab] OR timeline[tiab])
AND
("public health"[tiab] OR epidemiology[tiab] OR surveillance[tiab]))
```

### Query C1 — Surveillance / transmission / cluster detection
```text
((surveillance[tiab] OR "outbreak detection"[tiab] OR "cluster detection"[tiab])
AND
("transmission inference"[tiab] OR "transmission network"[tiab] OR "pairwise transmission"[tiab] OR plausibility[tiab]))
```

### Query C2 — STI surveillance analytics
```text
((syphilis[tiab] OR STI[tiab] OR "sexually transmitted infection"[tiab])
AND
(surveillance[tiab] OR analytics[tiab] OR cluster[tiab] OR outbreak[tiab]))
```

### Query D1 — FHIR + public health
```text
(FHIR[tiab] OR "Fast Healthcare Interoperability Resources"[tiab])
AND
("public health"[tiab] OR surveillance[tiab] OR "case reporting"[tiab] OR epidemiology[tiab])
```

### Query D2 — NBS / NEDSS + interoperability
```text
(NBS[tiab] OR NEDSS[tiab] OR "National Electronic Disease Surveillance System"[tiab])
AND
(interoperability[tiab] OR FHIR[tiab] OR surveillance[tiab] OR "case reporting"[tiab])
```

---

## Google Scholar queries

Use Scholar for broader capture, cited-by expansion, conference papers, reports, and standards-adjacent material.

### Scholar search set
```text
"visual case analysis" syphilis
"syphilis" "partner services"
"syphilis" "contact tracing" workflow
"disease intervention specialist" syphilis
"public health informatics" rule-based decision support surveillance
"temporal reasoning" epidemiology public health
FHIR public health surveillance
FHIR case reporting public health
"National Electronic Disease Surveillance System" interoperability
NBS surveillance interoperability FHIR
```

Use filters:
- Sort by relevance first
- Then repeat with sort by date for recent interoperability work
- Use custom date range for FHIR work (e.g. 2015-present)

---

## 6. Scopus / Web of Science strategy

Use broader phrase-based queries, then refine by title/abstract/keyword.

### Example search 1
```text
TITLE-ABS-KEY ( syphilis AND ("partner services" OR "contact tracing" OR "disease intervention specialist" OR "case investigation") )
```

### Example search 2
```text
TITLE-ABS-KEY ( ("public health informatics" OR "decision support") AND (rule-based OR explainable OR computable) AND (surveillance OR epidemiology OR "public health") )
```

### Example search 3
```text
TITLE-ABS-KEY ( (FHIR OR "Fast Healthcare Interoperability Resources") AND ("public health" OR surveillance OR "case reporting") )
```

---

## 7. Grey literature targets

These are especially important for public health workflow and interoperability context.

### Search directly on:
- CDC syphilis partner services pages
- CDC STI treatment / investigation guidance
- MMWR
- APHL interoperability and surveillance informatics materials
- CSTE resources on surveillance modernization
- HL7 FHIR implementation guides relevant to public health
- ONC public health interoperability materials

### Example web searches
```text
site:cdc.gov syphilis partner services disease intervention specialist
site:cdc.gov syphilis contact tracing workflow
site:cdc.gov NBS interoperability surveillance
site:hl7.org FHIR public health case reporting
site:aphl.org FHIR surveillance public health
site:cste.org surveillance interoperability FHIR
```

---

## 8. Inclusion criteria

Include sources that are clearly relevant to at least one of the following:
- syphilis case investigation, partner services, or transmission workflow
- visual/manual analytic reasoning for STI or public health investigation
- public health informatics methods using computable, rule-based, or explainable logic
- surveillance analytics or temporal/plausibility reasoning methods
- FHIR/public health interoperability relevant to surveillance or case management

Prioritize sources that:
- define terms or workflow problems clearly
- support the need for standardization and reproducibility
- help frame explainable decision support
- give credible language for interoperability discussion

---

## 9. Exclusion criteria

Exclude or deprioritize:
- purely molecular/genomic transmission papers with no workflow or informatics relevance
- purely therapeutic or clinical treatment papers unrelated to case investigation or analytic methods
- black-box prediction studies with no explainability or workflow angle
- papers too far outside public health workflow to contribute meaningfully to framing

You may still keep a few black-box papers if they are useful as a contrast point in the discussion.

---

## 10. Screening workflow

## Stage 1 — Title and abstract screen
For each result, ask:
1. Is the domain relevant?
2. Does it help the problem framing, methods framing, surveillance framing, or interoperability framing?
3. Is it likely citable in the paper?

Decision:
- `Include`
- `Maybe`
- `Exclude`

## Stage 2 — Full-text screen
For included/high-value papers, ask:
1. What exact role could this source play in the manuscript?
2. What specific claim or concept does it support?
3. Does it provide a quotable definition, rationale, or limitation?
4. Is it high-priority enough for full abstraction?

---

## 11. Search log

### Session 1 — 2026-05-31 (AI-assisted Pass 1 anchor search)

| Search Date | Database | Query Name | Exact Query | Filters | Hits | Notes |
|---|---|---|---|---|---:|---|
| 2026-05-31 | Google Scholar / PubMed | A1-DIS-Systematic-Review | syphilis DIS disease intervention specialist systematic review partner services effectiveness 2024 | English; humans | 30 included | Peterman et al. 2024, Am J Prev Med, PMC11663095 |
| 2026-05-31 | PubMed | A2-DIS-On-Site-Outcomes | partner notification outcomes disease intervention specialist STD clinic PLOS One 2018 | English; humans | 1 primary | Hurt et al. 2018, PLOS One, DOI 10.1371/journal.pone.0194041 |
| 2026-05-31 | PubMed / CDC Stacks | A3-Partner-Notification-Effectiveness | effectiveness syphilis partner notification 7 jurisdictions adjusting treatment dates 2022 | English; US data | 1 primary | Peterman et al. 2022, STD journal, PMID 34310526 |
| 2026-05-31 | NCSDDC Website | A4-VCA-Training | visual case analysis syphilis source spread ghosting methodology NCSDDC 2022 | Grey literature | 1 primary | NCSDDC/Fussell 2022 training document — archive copy recommended |
| 2026-05-31 | Google Scholar | A5-Changing-Role-DIS | changing role disease intervention specialist modern public health programs 2019 | English | 1 primary | Cope et al. 2019, Public Health Reports |
| 2026-05-31 | PubMed / Semantic Scholar | B1-PHI-Yasnoff-2000 | public health informatics definition Yasnoff O'Carroll 2000 | English | 1 primary | Yasnoff et al. 2000, J Public Health Mgmt Practice, PMID 18019962 |
| 2026-05-31 | CDC / MMWR | B2-CDC-MMWR-PHI-Surveillance | role public health informatics enhancing surveillance MMWR 2012 | Grey literature | 1 primary | Thacker et al. 2012, MMWR Suppl 61(03):20–24 |
| 2026-05-31 | PLOS Digital Health | B3-Explainability-CDSS | explainability clinical decision support AI rule-based versus black-box 2022 | English | 1 primary | Amann et al. 2022, PLOS Digital Health, DOI 10.1371/journal.pdig.0000016 |
| 2026-05-31 | NCBI Bookshelf | B4-Syphilis-Natural-History | syphilis natural history incubation primary secondary clinical constants | English; clinical | Multiple | StatPearls NBK534780; PMC10211027 for incubation period specifics |
| 2026-05-31 | PubMed | C1-Sexual-Networks-NC | sexual networks surveillance geographical space syphilis outbreaks rural North Carolina 2012 | English; humans | 1 primary | Doherty et al. 2012, Epidemiology, PMID 23007041, PMC4074028 |
| 2026-05-31 | PLOS Computational Biology | C2-STI-Mapping-Forsyth | syphilis STI spatial mapping Forsyth County PLOS computational biology 2024 | English | 1 primary | Fox et al. 2024, PLOS Comp Biol, DOI 10.1371/journal.pcbi.1012464 |
| 2026-05-31 | Scientific Reports / PubMed | C3-Network-Centric-SF | network centric interventions syphilis epidemic San Francisco 2017 | English | 1 primary | Klovdahl et al. 2017, Scientific Reports, PMC5527084 |
| 2026-05-31 | CSTE Website | C4-CSTE-Outbreak-Guidance | syphilis outbreak detection guidance CSTE STD subcommittee | Grey literature | 1 primary | CSTE STD Subcommittee ~2019 guidance document |
| 2026-05-31 | OJPHI / PubMed | D1-NBS-Workflow | NEDSS NBS electronic data exchange workflow decision support 2017 OJPHI | English | 1 primary | Ward, Hildebrandt, Patel 2017, OJPHI, PMC5462203 |
| 2026-05-31 | JMIR Medical Informatics | D2-FHIR-Systematic-Review | FHIR health research interoperability systematic review 2022 | English | 1 primary | Vorisek et al. 2022, JMIR Med Inform, DOI 10.2196/35724 |
| 2026-05-31 | HL7 / ONC | D3-HL7-eCR-IG | FHIR electronic case reporting implementation guide US realm v2 | Standards | 1 primary | HL7 FHIR eCR US Realm v2.1.2, https://hl7.org/fhir/us/ecr/ |
| 2026-05-31 | CDC Data Interoperability | D4-CDC-FHIR-Playbook | CDC public health FHIR playbook 2023 | Grey literature | 1 primary | CDC 2023, Public Health FHIR Playbook |

**Session 1 summary:** 17 sources identified; 14 High priority, 3 Medium priority. All 4 domains have anchor coverage. All sources confirmed via multi-query verification. Tracker populated in `PAPER1_ARTICLE_TRACKER.csv`.

**Pass 2 gaps to address next:**
- Formal peer-reviewed companion to NCSDDC VCA methodology (Fussell citation needs a published peer-reviewed equivalent or corroboration from CDC STI treatment guidelines)
- Temporal reasoning methods in epidemiology — more specific citations needed (current B2/B3 are adjacent but not specifically temporal windowing in STI context)
- Computable phenotyping / rule-based algorithm papers relevant to case identification (CARPEDIEM-style papers for Domain B)
- FHIR `RiskAssessment` resource documentation — verify as applicable to source-spread plausibility output representation
- More recent syphilis surveillance papers (2020–2026) — current C-domain papers are 2012/2017/2024
- CDC STI Treatment Guidelines 2021 as a natural history reference for engine constants

---

## 12. Target output after first search session

By the end of your first focused session, aim to have:
- 30–50 total saved records in Zotero
- 10–15 anchor papers/reports
- 15–25 title/abstract screened records
- 5–10 high-priority full texts ready for abstraction

---

## 13. Recommended folder and tag structure in Zotero

### Collections
- `Paper1_Methods`
- `Paper1_Syphilis_VCA`
- `Paper1_Public_Health_Informatics`
- `Paper1_Surveillance`
- `Paper1_FHIR_Interoperability`
- `Paper1_Maybe`

### Tags
- `problem-framing`
- `syphilis`
- `partner-services`
- `VCA`
- `temporal-reasoning`
- `decision-support`
- `explainability`
- `surveillance`
- `cluster-detection`
- `FHIR`
- `NBS`
- `future-work`

---

## 14. Fast abstraction guidance

When you open a full text, do not read linearly at first.

Skim in this order:
1. Abstract
2. Introduction first 2 paragraphs
3. Methods / system description
4. Discussion / conclusion
5. Pull only the lines that support manuscript framing

Then record the paper in `PAPER1_ARTICLE_TRACKER.csv`.

---

## 15. AI-assisted workflow rules

AI can help with:
- 3-bullet summaries
- identifying likely manuscript role
- clustering papers into themes
- drafting synthesis notes by bucket

Always verify:
- direct quotes
- definitions
- page-specific claims
- interpretation of methods and findings

Never cite a paper based only on an AI summary.

---

## 16. First-session checklist

- [ ] Set up Zotero collections and tags
- [ ] Run PubMed queries A1, A2, B1, D1
- [ ] Run Google Scholar queries for VCA, partner services, and FHIR
- [ ] Save broadly to Zotero
- [ ] Screen titles/abstracts into `PAPER1_ARTICLE_TRACKER.csv`
- [ ] Mark 5–10 high-priority papers for full abstraction
- [ ] Note missing concepts for Pass 2 searching
