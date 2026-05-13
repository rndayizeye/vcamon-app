# Contributing

```bash
git checkout -b feat/your-feature-name
make test
git push origin feat/your-feature-name
```

All pull requests run the CI pipeline (lint + tests) before merge.

---

# Provenance and Attribution

This project draws on three distinct sources, each contributing different
layers. The original software expression — the architecture, code, automation
logic, and implementation decisions — was created by the project author.

---

## Layer 1 — Clinical methodology

**Source:** Fussell, E. (2022). *Visual Case Analysis.*
National Coalition of STD Directors (NCSDDC) / Marion County Public Health Department.
https://www.ncsddc.org/wp-content/uploads/2022/07/VCA-Training-7.2022.pdf

**What was contributed:** The VCA ghosting methodology — the seven-step
analytical pipeline, the ghosting hierarchy (primary chancre → historical →
ghosted → secondary), the syphilis natural history constants (incubation,
primary, latency, secondary durations), the source/spread/ambiguous/unrelated
verdict logic, and the interview period calculations.

**What this project did with it:** The methodology was studied, interpreted,
and independently expressed as an automated computational engine in
`app/utils/clinical.py`. No text, diagrams, or slide content from the
training material was reproduced. The engine is an original software
implementation of the clinical reasoning described in the training, not a
copy or derivative of the training document itself.

---

## Layer 2 — Legacy workflow and field structure

**Source:** `vcamon-launch-v1.xlsm` — a legacy Excel workbook used for
VCA contact tracing case management. Origin and ownership to be confirmed
(internally developed or CDC-distributed tool — see note below).

**What was contributed:** The case management workflow structure — the
concept of Original Patient (OP) and partner records, the Major Analytical
Points (MAP) 46-item assessment checklist and its section groupings, the
field names and dropdown option sets (lab results, lesion types, symptoms,
treatments, reason for exam), the ghosting record types (source, spread
ghost, spread), and the transmission arrow link concept.

**What this project did with it:** The workflow was analysed and re-expressed
as a structured relational database schema (`app/db/models.py`), a set of
validated ORM queries (`app/db/queries.py`), and a multipage Streamlit
web application. No Excel code, VBA macros, or file content was copied.
The data model is an original software design informed by the workflow
structure of the legacy tool.

> **Note on CDC provenance:** If `vcamon-launch-v1.xlsm` was distributed
> by the Centers for Disease Control and Prevention (CDC) as a program tool,
> it was likely produced as a US federal government work and is in the public
> domain under 17 U.S.C. § 105. Confirmation of the workbook's origin and
> any associated data use agreements is pending. This section will be updated
> once confirmed.

---

## Layer 3 — Development assistance

**Source:** Claude (Anthropic)

**What was contributed:** Code scaffolding, architecture guidance,
documentation drafting, and iterative debugging support during development.

**What this project did with it:** All generated code was reviewed,
modified, and integrated by the project author. Claude was used as a
development tool — the design decisions, clinical interpretation, workflow
knowledge, and authorship of the project remain with the project author.

---

## Original contribution — software expression and automation

The project author's original contribution is the expression of the above
sources into working software:

- The database schema design and ORM models
- The computational implementation of the VCA ghosting engine as testable,
  pure Python logic decoupled from any UI framework
- The scenario-specific exposure criterion logic (Date1 for source,
  Date2 for spread, with a clinically-informed warn margin)
- The Streamlit multipage application architecture and navigation design
- The Plotly VCA timeline chart and scenario visualisation diagrams
- The quick ghosting analysis tool (no case required)
- The test suite covering the ghosting engine against the slide 17 training scenario
- The deployment and containerisation configuration

---

## Live app

**Beta:** [https://visualcaseanalysis.streamlit.app](https://visualcaseanalysis.streamlit.app)

Quick ghosting (no login required):
[https://visualcaseanalysis.streamlit.app/quick_ghost](https://visualcaseanalysis.streamlit.app/quick_ghost)
