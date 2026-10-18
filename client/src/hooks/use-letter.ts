import { useQuery } from "@tanstack/react-query";
import type { LetterDetail } from "../features/letters/types";
import { get } from "../services/api";

export function useLetter(slug: string) {
  return useQuery({
    queryKey: ["letter", slug],
    queryFn: () => get<LetterDetail>(`/api/v1/letters/${slug}`),
    refetchInterval: (query) =>
      query.state.data &&
      ["queued", "analyzing"].includes(query.state.data.analysis_status)
        ? 5000
        : false,
  });
}
