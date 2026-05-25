import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createCasePartnerRelationship,
  createPartner,
  getCasePartnerRelationship,
  getPartner,
  getPartnersForCase,
  updateCasePartnerRelationship,
  updatePartner,
} from "./api";
import type {
  CasePartnerRelationshipCreate,
  CasePartnerRelationshipUpdate,
  PartnerCreateInput,
  PartnerUpdateInput,
} from "./types";

export function useCasePartners(caseId: number) {
  return useQuery({
    queryKey: ["cases", caseId, "partners"],
    queryFn: () => getPartnersForCase(caseId),
    enabled: !!caseId && caseId > 0,
  });
}

export function usePartner(partnerId: number) {
  return useQuery({
    queryKey: ["partners", partnerId],
    queryFn: () => getPartner(partnerId),
    enabled: !!partnerId && partnerId > 0,
  });
}

export function useCreatePartner(caseId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: PartnerCreateInput) => createPartner(caseId, data),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: ["cases", caseId, "partners"],
      });
    },
  });
}

export function useUpdatePartner() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      partnerId,
      data,
    }: {
      partnerId: number;
      data: PartnerUpdateInput;
    }) => updatePartner(partnerId, data),
    onSuccess: (data) => {
      void queryClient.invalidateQueries({
        queryKey: ["partners", data.id],
      });
      void queryClient.invalidateQueries({
        queryKey: ["cases", data.case_id, "partners"],
      });
    },
  });
}

export function useCasePartnerRelationship(caseId: number, partnerId: number) {
  return useQuery({
    queryKey: ["cases", caseId, "partners", partnerId, "relationship"],
    queryFn: () => getCasePartnerRelationship(caseId, partnerId),
    enabled: !!caseId && caseId > 0 && !!partnerId && partnerId > 0,
  });
}

export function useSaveCasePartnerRelationship() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      caseId,
      partnerId,
      data,
      isUpdate,
    }: {
      caseId: number;
      partnerId: number;
      data: CasePartnerRelationshipCreate | CasePartnerRelationshipUpdate;
      isUpdate: boolean;
    }) =>
      isUpdate
        ? updateCasePartnerRelationship(
            caseId,
            partnerId,
            data as CasePartnerRelationshipUpdate,
          )
        : createCasePartnerRelationship(
            caseId,
            partnerId,
            data as CasePartnerRelationshipCreate,
          ),
    onSuccess: (data) => {
      void queryClient.invalidateQueries({
        queryKey: ["cases", data.case_id, "partners", data.partner_id, "relationship"],
      });
    },
  });
}
