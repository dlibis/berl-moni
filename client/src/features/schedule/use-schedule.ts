import { useQuery } from "@tanstack/react-query";
import { get } from "../../lib/api";
import type { ScheduleData } from "./types";

export function useSchedule() {
  return useQuery({ queryKey: ["schedule"], queryFn: () => get<ScheduleData>("/api/v1/schedule") });
}
