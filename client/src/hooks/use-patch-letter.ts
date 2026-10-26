import { useMutation, useQueryClient } from "@tanstack/react-query";
import type { LetterDetail } from "../features/letters/types";
import { write } from "../services/api";

type PatchBody = { requires_review?: boolean; passed?: boolean };

export function usePatchLetter() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ slug, ...body }: { slug: string } & PatchBody) =>
      write<LetterDetail>(`/api/v1/letters/${slug}`, "PATCH", body),
    onSuccess: (letter) => {
      queryClient.invalidateQueries({ queryKey: ["letters"] });
      queryClient.setQueryData(["letter", letter.slug], letter);
    },
  });
}
