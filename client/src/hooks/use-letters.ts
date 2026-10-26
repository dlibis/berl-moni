import { keepPreviousData, useQuery } from "@tanstack/react-query";
import type {
  LettersPage,
  LetterStatusFilter,
} from "../features/letters/types";
import { get } from "../services/api";

export const LETTERS_PAGE_SIZE = 10;

export function useLetters({
  page,
  status,
  search,
}: {
  page: number;
  status?: LetterStatusFilter;
  search?: string;
}) {
  return useQuery({
    queryKey: ["letters", page, status, search],
    queryFn: () =>
      get<LettersPage>(
        `/api/v1/letters?page=${page + 1}&page_size=${LETTERS_PAGE_SIZE}${status ? `&status=${status}` : ""}${search ? `&search=${encodeURIComponent(search)}` : ""}`,
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
