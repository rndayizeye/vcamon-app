import { useQuery } from "@tanstack/react-query";

import { listCaseSymptoms, listPartnerSymptoms } from "./api";

export function useCaseSymptoms(caseId: number) {
  return useQuery({
    queryKey: ["cases", caseId, "symptoms"],
    queryFn: () => listCaseSymptoms(caseId),
    enabled: caseId > 0,
  });
}

export function usePartnerSymptoms(partnerId: number) {
  return useQuery({
    queryKey: ["partners", partnerId, "symptoms"],
    queryFn: () => listPartnerSymptoms(partnerId),
    enabled: partnerId > 0,
  });
}
