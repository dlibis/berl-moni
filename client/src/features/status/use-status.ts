import { useQuery } from "@tanstack/react-query";
import { get } from "../../lib/api";
import type { Status } from "./types";

export function useStatus() {
  return useQuery({ queryKey: ["status"], queryFn: () => get<Status>("/api/v1/status") });
}
