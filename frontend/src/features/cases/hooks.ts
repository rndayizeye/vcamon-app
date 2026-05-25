import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createCase,
  getCase,
  listCasePartners,
  listCases,
  updateCase,
} from "./api";
import type { CaseCreateInput, CaseRead, CaseUpdateInput } from "./types";

export function useCases(search?: string) {
  return useQuery({
    queryKey: ["cases", { search: search?.trim() || null }],
    queryFn: () => listCases(search),
  });
}

export function useCase(caseId: number) {
  return useQuery({
    queryKey: ["cases", caseId],
    queryFn: () => getCase(caseId),
    enabled: caseId > 0,
  });
}

export function useCasePartners(caseId: number) {
  return useQuery({
    queryKey: ["cases", caseId, "partners"],
    queryFn: () => listCasePartners(caseId),
    enabled: caseId > 0,
  });
}

export function useCreateCase() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: CaseCreateInput) => createCase(payload),
    onSuccess: async (createdCase: CaseRead) => {
      queryClient.setQueryData(["cases", createdCase.id], createdCase);
      await queryClient.invalidateQueries({ queryKey: ["cases"] });
    },
  });
}

export function useUpdateCase(caseId: number) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: CaseUpdateInput) => updateCase(caseId, payload),
    onSuccess: async (updatedCase: CaseRead) => {
      queryClient.setQueryData(["cases", caseId], updatedCase);
      await queryClient.invalidateQueries({ queryKey: ["cases"] });
    },
  });
}
