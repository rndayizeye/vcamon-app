import { useQuery } from "@tanstack/react-query";
import {
  getRelationshipReports,
  createRelationshipReport,
  updateRelationshipReport,
  deleteRelationshipReport,
} from "./api";
import type { RelationshipReportRead, RelationshipReportWriteInput } from "./types";

export function useRelationshipReports(relationshipId: number) {
  return useQuery({
    queryKey: ["relationships", relationshipId, "reports"],
    queryFn: () => getRelationshipReports(relationshipId),
    enabled: relationshipId > 0,
  });
}

export async function syncRelationshipReports(
  relationshipId: number,
  existingReports: RelationshipReportRead[],
  nextReports: RelationshipReportWriteInput[],
) {
  const nextIds = new Set(
    nextReports
      .map((r) => r.id)
      .filter((value): value is number => typeof value === "number"),
  );

  await Promise.all(
    existingReports
      .filter((r) => !nextIds.has(r.id))
      .map((r) => deleteRelationshipReport(r.id)),
  );

  const savedReports: RelationshipReportRead[] = [];
  for (const report of nextReports) {
    if (typeof report.id === "number") {
      savedReports.push(await updateRelationshipReport(report.id, report));
    } else {
      savedReports.push(await createRelationshipReport(relationshipId, report));
    }
  }
  return savedReports;
}
