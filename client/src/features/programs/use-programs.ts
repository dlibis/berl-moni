import { useQuery } from "@tanstack/react-query";
import { get } from "../../lib/api";
import type { Program } from "./types";

export function usePrograms() {
  return useQuery({
    queryKey: ["programs"],
    queryFn: () => get<{ programs: Program[] }>("/api/v1/master"),
  });
}
