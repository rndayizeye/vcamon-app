import { useQuery } from "@tanstack/react-query";
import { listPartnerLabs } from "./labs-api";

export function usePartnerLabs(partnerId: number) {
  return useQuery({
    queryKey: ["partners", partnerId, "labs"],
    queryFn: () => listPartnerLabs(partnerId),
    enabled: partnerId > 0,
  });
}
