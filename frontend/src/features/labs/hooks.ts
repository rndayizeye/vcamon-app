import { useQuery } from "@tanstack/react-query";
import { listCaseLabs, listPartnerLabs } from "./api";

export function useCaseLabs(caseId: number) {
  return useQuery({
    queryKey: ["cases", caseId, "labs"],
    queryFn: () => listCaseLabs(caseId),
    enabled: caseId > 0,
  });
}

export function usePartnerLabs(partnerId: number) {
  return useQuery({
    queryKey: ["partners", partnerId, "labs"],
    queryFn: () => listPartnerLabs(partnerId),
    enabled: partnerId > 0,
  });
}
