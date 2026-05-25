import type { UseFormRegister } from "react-hook-form";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type AnyRegister = UseFormRegister<any>;

import {
  EMPTY_SYMPTOM_DRAFT,
  SYMPTOM_DATE_KIND_OPTIONS,
  SYMPTOM_TYPE_OPTIONS,
  type SymptomEntryDraft,
} from "../../symptoms/types";

export function SymptomEntriesEditor({
  fields,
  append,
  remove,
  register,
  disabled,
}: {
  fields: Array<SymptomEntryDraft & { formId: string }>;
  append: (value: SymptomEntryDraft) => void;
  remove: (index: number) => void;
  register: AnyRegister;
  disabled: boolean;
}) {
  return (
    <section className="stack-md">
      <div className="page-header-row">
        <div>
          <p className="eyebrow">Symptoms</p>
          <h3>Symptom entries</h3>
        </div>
        <button
          className="button"
          type="button"
          onClick={() => append({ ...EMPTY_SYMPTOM_DRAFT })}
          disabled={disabled}
        >
          Add symptom
        </button>
      </div>

      <p className="muted small-text">
        Use <strong>Onset or observation date</strong>. If onset is unknown and
        the symptom was observed during exam, choose that date type. Leaving
        duration blank in that case tells the backend to assume the maximum
        duration and derive <code>ongoing</code> automatically.
      </p>

      {fields.length === 0 ? (
        <p className="muted small-text">
          No symptom rows yet. Add one if you need to capture onset/observation
          timing for this case. The same editor shape can be reused for future
          partner forms.
        </p>
      ) : null}

      <div className="stack-md">
        {fields.map((field, index) => (
          <div className="entry-card stack-md" key={field.formId}>
            <div className="page-header-row">
              <strong>Symptom {index + 1}</strong>
              <button
                className="button button-danger"
                type="button"
                onClick={() => remove(index)}
                disabled={disabled}
              >
                Remove
              </button>
            </div>

            <div className="two-column-grid">
              <label className="field">
                <span>Type</span>
                <select {...register(`symptoms.${index}.symptom_type`)}>
                  <option value="">Select a symptom or lesion type</option>
                  {SYMPTOM_TYPE_OPTIONS.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
              </label>

              <label className="field">
                <span>Date type</span>
                <select {...register(`symptoms.${index}.date_kind`)}>
                  {SYMPTOM_DATE_KIND_OPTIONS.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
              </label>

              <label className="field">
                <span>Onset or observation date</span>
                <input
                  type="date"
                  {...register(`symptoms.${index}.onset_date`)}
                />
              </label>

              <label className="field">
                <span>Duration (days, if known)</span>
                <input
                  type="number"
                  min="0"
                  step="1"
                  placeholder="Leave blank to let the backend derive when allowed"
                  {...register(`symptoms.${index}.duration_days`)}
                />
              </label>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
