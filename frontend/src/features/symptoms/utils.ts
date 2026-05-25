import {
  PRIMARY_SYMPTOM_TYPE_OPTIONS,
  SECONDARY_SYMPTOM_TYPE_OPTIONS,
  type SymptomEntryDraft,
  type SymptomEntryRead,
  type SymptomEntryWriteInput,
} from "./types";

const PRIMARY_MAX_DURATION_DAYS = 35;
const SECONDARY_MAX_DURATION_DAYS = 42;

function isBlank(value: string | null | undefined) {
  return !value || value.trim().length === 0;
}

export function isPrimarySymptomType(symptomType: string) {
  return PRIMARY_SYMPTOM_TYPE_OPTIONS.includes(
    symptomType as (typeof PRIMARY_SYMPTOM_TYPE_OPTIONS)[number],
  );
}

export function isSecondarySymptomType(symptomType: string) {
  return SECONDARY_SYMPTOM_TYPE_OPTIONS.includes(
    symptomType as (typeof SECONDARY_SYMPTOM_TYPE_OPTIONS)[number],
  );
}

export function getMaxDurationDays(symptomType: string) {
  if (isPrimarySymptomType(symptomType)) {
    return PRIMARY_MAX_DURATION_DAYS;
  }

  if (isSecondarySymptomType(symptomType)) {
    return SECONDARY_MAX_DURATION_DAYS;
  }

  return null;
}

export function toSymptomDraft(symptom: SymptomEntryRead): SymptomEntryDraft {
  return {
    id: symptom.id,
    symptom_type: symptom.symptom_type,
    onset_date: symptom.onset_date || "",
    date_kind: symptom.date_kind,
    duration_days:
      symptom.duration_days === null || symptom.duration_days === undefined
        ? ""
        : String(symptom.duration_days),
  };
}

export function normalizeSymptomDrafts(
  symptoms: SymptomEntryDraft[],
): SymptomEntryWriteInput[] {
  const normalized: SymptomEntryWriteInput[] = [];

  for (const [index, symptom] of symptoms.entries()) {
    const symptomType = symptom.symptom_type.trim();
    const onsetDate = symptom.onset_date.trim();
    const durationText = symptom.duration_days.trim();
    const hasAnyValue = Boolean(
      symptom.id || symptomType || onsetDate || durationText,
    );

    if (!hasAnyValue) {
      continue;
    }

    if (!symptomType) {
      throw new Error(`Symptom ${index + 1}: type is required.`);
    }

    if (!onsetDate) {
      throw new Error(
        `Symptom ${index + 1}: onset or observation date is required.`,
      );
    }

    const durationDays = durationText ? Number(durationText) : null;
    if (
      durationText &&
      (durationDays === null ||
        !Number.isInteger(durationDays) ||
        durationDays < 0)
    ) {
      throw new Error(`Symptom ${index + 1}: duration must be a whole number.`);
    }

    normalized.push({
      id: symptom.id,
      symptom_type: symptomType,
      onset_date: onsetDate,
      date_kind: symptom.date_kind,
      duration_days: durationDays,
    });
  }

  return normalized;
}

export function resolveSymptomTiming(symptom: {
  symptom_type: string;
  onset_date: string | null;
  date_kind: string;
  duration_days: number | null;
}) {
  if (isBlank(symptom.onset_date)) {
    return {
      derivedOnsetDate: null,
      effectiveDurationDays: symptom.duration_days,
    };
  }

  if (symptom.date_kind === "Observed during exam (onset unknown)") {
    const effectiveDurationDays =
      symptom.duration_days ?? getMaxDurationDays(symptom.symptom_type);

    if (effectiveDurationDays === null) {
      return {
        derivedOnsetDate: symptom.onset_date,
        effectiveDurationDays: null,
      };
    }

    const anchorDate = new Date(`${symptom.onset_date}T00:00:00`);
    anchorDate.setDate(anchorDate.getDate() - effectiveDurationDays);

    return {
      derivedOnsetDate: anchorDate.toISOString().slice(0, 10),
      effectiveDurationDays,
    };
  }

  return {
    derivedOnsetDate: symptom.onset_date,
    effectiveDurationDays: symptom.duration_days,
  };
}

export function deriveHistoricalPrimary(
  symptoms: SymptomEntryWriteInput[],
  treatmentDate: string | null,
) {
  if (isBlank(treatmentDate)) {
    return {
      historical_primary_chancre: false,
      historical_primary_date: null,
    };
  }

  const treatmentDateValue = new Date(`${treatmentDate}T00:00:00`);

  for (const symptom of symptoms) {
    if (
      !isPrimarySymptomType(symptom.symptom_type) ||
      isBlank(symptom.onset_date)
    ) {
      continue;
    }

    const anchorDate = new Date(`${symptom.onset_date}T00:00:00`);
    const { derivedOnsetDate, effectiveDurationDays } =
      resolveSymptomTiming(symptom);
    if (!derivedOnsetDate) {
      continue;
    }

    let symptomEndDate: Date | null = null;
    if (symptom.date_kind === "Observed during exam (onset unknown)") {
      symptomEndDate = anchorDate;
    } else if (effectiveDurationDays !== null) {
      symptomEndDate = new Date(`${symptom.onset_date}T00:00:00`);
      symptomEndDate.setDate(symptomEndDate.getDate() + effectiveDurationDays);
    }

    if (symptomEndDate && symptomEndDate < treatmentDateValue) {
      return {
        historical_primary_chancre: true,
        historical_primary_date: derivedOnsetDate,
      };
    }
  }

  return {
    historical_primary_chancre: false,
    historical_primary_date: null,
  };
}
