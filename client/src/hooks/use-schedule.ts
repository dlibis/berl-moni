import { useQuery } from "@tanstack/react-query";
import { get } from "../services/api";
import type { ScheduleData } from "../features/schedule/types";

export function useSchedule() {
  return useQuery({ queryKey: ["schedule"], queryFn: () => get<ScheduleData>("/api/v1/schedule") });
}
