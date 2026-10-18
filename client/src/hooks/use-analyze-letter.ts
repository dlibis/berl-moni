import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ApiError, write } from "../services/api";

type AnalyzeResult = { status: "queued" | "done"; dispatch_failed?: boolean };

export function useAnalyzeLetter() {
  const queryClient = useQueryClient();
  const refresh = (slug: string) => {
    queryClient.invalidateQueries({ queryKey: ["letters"] });
    queryClient.invalidateQueries({ queryKey: ["letter", slug] });
  };
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
      if (result.status === "done") {
        toast.success("המכתב כבר נותח, התוצאה השמורה מוצגת");
      } else {
        toast.success("הניתוח נכנס לתור", {
          description: result.dispatch_failed
            ? "הניתוח יתחיל עד שעה"
            : undefined,
        });
      }
      refresh(slug);
    },
    onError: (error, { slug }) => {
      refresh(slug); // the row shows the letter's real status, not a stale one
      if (error instanceof ApiError && error.status === 409) {
        toast.error("הניתוח כבר בתהליך");
      } else {
        toast.error("הניתוח נכשל");
      }
    },
  });
}
