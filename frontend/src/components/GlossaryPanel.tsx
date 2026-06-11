const GLOSSARY_TERMS = [
  {
    term: "OP / Original Patient",
    definition:
      "The index case — the first diagnosed patient in the cluster from which the investigation starts.",
  },
  {
    term: "VCA",
    definition:
      "Visual Case Analysis — a CDC DIS field methodology (codified 1992; NCSD 2022 training) for establishing probable transmission links from clinical timing data.",
  },
  {
    term: "Ghosting / Ghosted lesion",
    definition:
      "A calculated lesion window inferred from clinical constants when the actual lesion was not directly observed during interviews.",
  },
  {
    term: "MAP",
    definition:
      "Major Analytical Points — a 46-item systematic checklist for documenting key case information.",
  },
  {
    term: "Interview period",
    definition:
      "The look-back window during which contacts are elicited: 125 days before primary onset, 237 days before secondary onset.",
  },
  {
    term: "Inoculation date",
    definition:
      "The estimated date of infection, back-calculated from symptom onset using clinical constants (avg: 21 days before chancre onset).",
  },
  {
    term: "Infectious window",
    definition:
      "The period from maximum inoculation date to treatment during which the patient could have transmitted to contacts.",
  },
  {
    term: "Stage code",
    definition:
      "CDC morbidity reporting code for syphilis stage at diagnosis: 700 = Unknown, 710 = Primary, 720 = Secondary, 730 = Early non-primary non-secondary, 755 = Unknown duration or late.",
  },
  {
    term: "LX / Lesion",
    definition:
      "Lesion — shorthand for a syphilitic sore. Primary: chancre. Secondary: rash or mucous patch.",
  },
  {
    term: "Titer",
    definition:
      "Antibody concentration from a non-treponemal test (RPR/VDRL), expressed as a dilution ratio: 1:1, 1:2, 1:4, 1:8, etc.",
  },
];

export function GlossaryPanel() {
  return (
    <details className="glossary-panel">
      <summary>Glossary — VCA terms</summary>
      <dl className="glossary-list">
        {GLOSSARY_TERMS.map(({ term, definition }) => (
          <div key={term} className="glossary-entry">
            <dt>{term}</dt>
            <dd>{definition}</dd>
          </div>
        ))}
      </dl>
    </details>
  );
}
