import { useQuery } from "@tanstack/react-query";
import { get } from "../services/api";
import type { Status } from "../features/status/types";

export function useStatus() {
  return useQuery({ queryKey: ["status"], queryFn: () => get<Status>("/api/v1/status") });
}
