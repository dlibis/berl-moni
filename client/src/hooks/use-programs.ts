import { useQuery } from "@tanstack/react-query";
import { get } from "../services/api";
import type { Program } from "../features/programs/types";

export function usePrograms() {
  return useQuery({
    queryKey: ["programs"],
    queryFn: () => get<{ programs: Program[] }>("/api/v1/master"),
  });
}
