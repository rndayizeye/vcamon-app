import { useMemo, useState } from "react";
import { useParams } from "react-router-dom";

import { RequirePermission } from "../../auth/RequirePermission";
import { GlossaryPanel } from "../../components/GlossaryPanel";
import { EmptyState } from "../../components/feedback/EmptyState";
import { ErrorState } from "../../components/feedback/ErrorState";
import { LoadingState } from "../../components/feedback/LoadingState";
import { useCasePartners } from "../cases/hooks";
import type { PartnerRead } from "../partners/types";
import { MapSection } from "./components/MapSection";
import { MapSummaryCards } from "./components/MapSummaryCards";
import { useClearMapSheet, useMapSheet, useSaveMapSheet } from "./hooks";
import type { MAPSheet, MAPSheetItem, MAPSheetUpsert } from "./types";

type SubjectOption = {
  value: string;
  label: string;
  partnerId: number | null;
};

function toPayload(sheet: MAPSheet): MAPSheetUpsert {
  return {
    items: sheet.items.map((item) => ({
      item_number: item.item_number,
      p_value: item.p_value,
      c_value: item.c_value,
      notes: item.notes,
      high_priority: item.high_priority,
    })),
    high_priority_comment: sheet.high_priority_comment,
  };
}

function isPartnerSubject(value: string) {
  return value.startsWith("partner:");
}

function buildPartnerOption(partner: PartnerRead): SubjectOption {
  return {
    value: `partner:${partner.id}`,
    label: `Partner ${partner.partner_number} — ${partner.name || "Unnamed"}`,
    partnerId: partner.id,
  };
}

export function CaseMapPage() {
  const { caseId } = useParams();
  const parsedCaseId = Number(caseId);
  const safeCaseId =
    Number.isInteger(parsedCaseId) && parsedCaseId > 0 ? parsedCaseId : 0;

  const partnersQuery = useCasePartners(safeCaseId);
  const [subjectValue, setSubjectValue] = useState("case");
  const [draftSheet, setDraftSheet] = useState<MAPSheet | null>(null);

  const subjectOptions = useMemo<SubjectOption[]>(() => {
    const options: SubjectOption[] = [
      { value: "case", label: "Index patient (OP)", partnerId: null },
    ];

    for (const partner of partnersQuery.data || []) {
      options.push(buildPartnerOption(partner));
    }

    return options;
  }, [partnersQuery.data]);

  const effectiveSubjectValue = subjectOptions.some(
    (option) => option.value === subjectValue,
  )
    ? subjectValue
    : "case";

  const selectedPartnerId = isPartnerSubject(effectiveSubjectValue)
    ? Number(effectiveSubjectValue.split(":")[1])
    : null;

  const mapQuery = useMapSheet(safeCaseId, selectedPartnerId);
  const saveMutation = useSaveMapSheet(safeCaseId, selectedPartnerId);
  const clearMutation = useClearMapSheet(safeCaseId, selectedPartnerId);

  const workingSheet = draftSheet ?? mapQuery.data ?? null;

  const groupedSections = useMemo(() => {
    if (!workingSheet) {
      return [] as Array<{ section: string; items: MAPSheetItem[] }>;
    }

    return workingSheet.section_order.map((section) => ({
      section,
      items: workingSheet.items.filter((item) => item.section === section),
    }));
  }, [workingSheet]);

  const liveSummary = useMemo(() => {
    if (!workingSheet) {
      return null;
    }

    return {
      total_items: workingSheet.items.length,
      checked_p: workingSheet.items.filter((item) => item.p_value).length,
      checked_c: workingSheet.items.filter((item) => item.c_value).length,
      high_priority_flags: workingSheet.items.filter(
        (item) => item.high_priority,
      ).length,
    };
  }, [workingSheet]);

  const isDirty = useMemo(() => {
    if (!draftSheet || !mapQuery.data) {
      return false;
    }

    return (
      JSON.stringify(toPayload(draftSheet)) !==
      JSON.stringify(toPayload(mapQuery.data))
    );
  }, [draftSheet, mapQuery.data]);

  if (safeCaseId === 0) {
    return (
      <ErrorState title="Invalid case" message="The case id is not valid." />
    );
  }

  if (partnersQuery.isError) {
    return (
      <ErrorState
        title="Unable to load partners"
        message={partnersQuery.error.message}
        onRetry={() => void partnersQuery.refetch()}
      />
    );
  }

  if (mapQuery.isLoading || partnersQuery.isLoading) {
    return <LoadingState message="Loading MAP sheet…" />;
  }

  if (mapQuery.isError) {
    return (
      <ErrorState
        title="Unable to load MAP sheet"
        message={mapQuery.error.message}
        onRetry={() => void mapQuery.refetch()}
      />
    );
  }

  if (!workingSheet) {
    return <EmptyState title="MAP sheet unavailable" />;
  }

  function updateItem(
    itemNumber: number,
    updater: (item: MAPSheetItem) => MAPSheetItem,
  ) {
    setDraftSheet((current) => {
      const source = current ?? workingSheet;
      if (!source) {
        return current;
      }

      return {
        ...source,
        items: source.items.map((item) =>
          item.item_number === itemNumber ? updater(item) : item,
        ),
      };
    });
  }

  function handleToggle(
    itemNumber: number,
    field: "p_value" | "c_value" | "high_priority",
  ) {
    updateItem(itemNumber, (item) => ({
      ...item,
      [field]: !item[field],
    }));
  }

  function handleNotesChange(itemNumber: number, notes: string) {
    updateItem(itemNumber, (item) => ({
      ...item,
      notes,
    }));
  }

  async function handleSave() {
    if (!workingSheet) {
      return;
    }

    const savedSheet = await saveMutation.mutateAsync(toPayload(workingSheet));
    setDraftSheet(savedSheet);
  }

  async function handleClear() {
    const confirmed = window.confirm(
      "Clear all MAP entries for the selected subject?",
    );
    if (!confirmed) {
      return;
    }

    await clearMutation.mutateAsync();
    await mapQuery.refetch();
  }

  return (
    <section className="stack-lg">
      <header className="panel stack-md">
        <div>
          <p className="eyebrow">MAP</p>
          <h2>Major analytical points</h2>
          <p className="muted">
            Capture the 46-item MAP checklist for the index patient (OP) or a selected partner.
          </p>
        </div>

        <div className="map-toolbar">
          <label className="field map-subject-field">
            <span>Subject</span>
            <select
              value={effectiveSubjectValue}
              onChange={(event) => {
                setSubjectValue(event.target.value);
                setDraftSheet(null);
              }}
            >
              {subjectOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>

          <div className="map-actions">
            <button
              className="button"
              type="button"
              onClick={() => setDraftSheet(null)}
              disabled={!isDirty}
            >
              Reset changes
            </button>

            <RequirePermission permission="can_write">
              <button
                className="button button-primary"
                type="button"
                onClick={() => void handleSave()}
                disabled={saveMutation.isPending || !isDirty}
              >
                {saveMutation.isPending ? "Saving…" : "Save MAP sheet"}
              </button>
            </RequirePermission>

            <RequirePermission permission="can_clear_map">
              <button
                className="button button-danger"
                type="button"
                onClick={() => void handleClear()}
                disabled={clearMutation.isPending}
              >
                {clearMutation.isPending ? "Clearing…" : "Clear sheet"}
              </button>
            </RequirePermission>
          </div>
        </div>

        <div className="stack-xs">
          <strong>{workingSheet.subject_label}</strong>
          {saveMutation.isError ? (
            <p className="error-text">{saveMutation.error.message}</p>
          ) : null}
          {clearMutation.isError ? (
            <p className="error-text">{clearMutation.error.message}</p>
          ) : null}
        </div>
      </header>

      <GlossaryPanel />

      {liveSummary ? <MapSummaryCards summary={liveSummary} /> : null}

      <section className="panel stack-sm">
        <div>
          <p className="eyebrow">High priority comment</p>
          <h2>Supervisor/context note</h2>
        </div>
        <textarea
          rows={4}
          value={workingSheet.high_priority_comment}
          onChange={(event) =>
            setDraftSheet((current) =>
              (current ?? workingSheet)
                ? {
                    ...(current ?? workingSheet),
                    high_priority_comment: event.target.value,
                  }
                : current,
            )
          }
          placeholder="Add a case-level note for high-priority items…"
        />
      </section>

      {groupedSections.map(({ section, items }) => (
        <MapSection
          key={section}
          section={section}
          items={items}
          onToggle={handleToggle}
          onNotesChange={handleNotesChange}
        />
      ))}
    </section>
  );
}
