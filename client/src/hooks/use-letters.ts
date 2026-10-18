import { keepPreviousData, useQuery } from "@tanstack/react-query";
import type {
  LettersPage,
  LetterStatusFilter,
} from "../features/letters/types";
import { get } from "../services/api";

export function useLetters({
  page,
  status,
}: {
  page: number;
  status?: LetterStatusFilter;
}) {
  return useQuery({
    queryKey: ["letters", page, status],
    queryFn: () =>
      get<LettersPage>(
        `/api/v1/letters?page=${page + 1}&page_size=25${status ? `&status=${status}` : ""}`,
      ),
    placeholderData: keepPreviousData,
    refetchInterval: (query) =>
      query.state.data?.items.some(({ analysis_status }) =>
        ["queued", "analyzing"].includes(analysis_status),
      )
        ? 5000
        : false,
  });
}
