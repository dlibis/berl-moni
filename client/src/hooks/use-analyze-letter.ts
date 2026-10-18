import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ApiError, write } from "../services/api";

type AnalyzeResult = { dispatch_failed?: boolean };

export function useAnalyzeLetter() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      slug,
      reanalyze,
    }: {
      slug: string;
      reanalyze?: boolean;
    }) =>
      write<AnalyzeResult>(
        `/api/v1/letters/${slug}/${reanalyze ? "reanalyze" : "analyze"}`,
        "POST",
      ),
    onSuccess: (result, { slug }) => {
      toast.success("הניתוח נכנס לתור", {
        description: result.dispatch_failed
          ? "הניתוח יתחיל עד שעה"
          : undefined,
      });
      queryClient.invalidateQueries({ queryKey: ["letters"] });
      queryClient.invalidateQueries({ queryKey: ["letter", slug] });
    },
    onError: (error) => {
      if (error instanceof ApiError && error.status === 409) {
        toast.error("הניתוח כבר בתהליך");
      } else {
        toast.error("הניתוח נכשל");
      }
    },
  });
}
