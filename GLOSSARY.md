# VCA Monitor — Public Health Terminology Standard (Glossary)

This glossary ensures that the application's internal naming (variables, functions, database columns) is grounded in professional public health and epidemiological terminology. 

When introducing new features or refactoring, prefer the **Standard PH Term** over the **Internal/Draft Term**.

---

## 🏥 Core Terminology Mapping

| Internal/Draft Term | Standard PH Term | Context / Notes |
| :--- | :--- | :--- |
| `Clinical Engine` | **Epidemiology Engine** | The core logic determining transmission. |
| `Ghosting Analysis` | **Source/Spread Analysis** | "Ghosting" is kept as an operational term, but "Source/Spread" is used for formal reporting/API. |
| `Symptom Location` | **Anatomical Site** | The physical location of a primary chancre. |
| `Sex Types` | **Exposure Modality** | The nature of the contact (e.g., anal, oral, vaginal). |
| `Original Patient (OP)` | **Index Case** | The primary case from which a cluster is traced. |
| `Contact Partner` | **Contact** | Any person identified as having potential exposure. |
| `Ghosted Lesion` | **Inferred Primary Chancre** | A calculated lesion window not directly observed. |
| `Exposure Window` | **Contact Period** | The timeframe during which two individuals had contact. From the first sexual exposure (FSE) to last sexual exposure(LSE) |
| `Infectious Period` | **Interview Period** | The window during which the person can transmit syphilis. |
|``|**Critical Period**| The period in which a person can was likely infected. It spans from the minimun inoculation date to maximun inoculation date|
| `T-Bar` | **Treatment Bar** | The anchor point on a VCA chart representing the date of test/treatment. |
| `Partner Services` | **Partner Services** | Broad social service actions (beyond direct contacts) to prevent transmission and reduce suffering. |
| `Contact Tracing` | **Contact Tracing** | The physical action of identifying and locating sexual partners to refer them for care. |
| `Name First` | **Name-First Methodology** | CDC-recommended strategy to prioritize name collection to build networks quickly. |
| `Primary Intervention`| **Primary Disease Intervention** | The goal of reaching partners before they develop symptoms. |

---

## 📏 Naming Guidelines

### 1. Variable & Function Naming
- **Prefer Specificity:** Use `anatomical_site` instead of `location`.
- **Avoid Framework Slang:** Use `exposure_modality` instead of `sex_type_string`.
- **Consistency:** If a term is defined in the glossary, it must be used consistently across the DB, the Epidemiology Engine, and the UI.

### 2. File Naming
- `app/utils/clinical.py` $\rightarrow$ `app/utils/epidemiology.py` (Planned)
- `app/db/models.py` (Ensure columns use PH terms, e.g., `anatomical_site` instead of `location`)

---

## 🔄 Transition Strategy
We will not perform a global "search-and-replace" instantly to avoid breaking the live beta. Instead:
1. **New Code:** Must follow the glossary strictly.
2. **Refactors:** When touching a module, align its internal naming with the glossary.
3. **Aliases:** Keep legacy aliases (e.g., `select_p1`) in the engine for a transitional period, but mark them as `@deprecated`.
