import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ApiError, write } from "../services/api";

export function useSendLetter() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ slug, resend }: { slug: string; resend?: boolean }) =>
      write(`/api/v1/letters/${slug}/send`, "POST", { resend: !!resend }),
    onSuccess: (_, { slug }) => {
      toast.success("הפנייה נשלחה");
      queryClient.invalidateQueries({ queryKey: ["letters"] });
      queryClient.invalidateQueries({ queryKey: ["letter", slug] });
    },
    onError: (error) => {
      if (
        error instanceof ApiError &&
        error.status === 409 &&
        error.message === "confirm_resend"
      ) {
        return;
      }
      if (error instanceof ApiError && error.message === "run_open") {
        toast.error("יש שליחה פתוחה של הפנייה הזו. יש להשלים או לבטל אותה בכרטיס בעמוד הראשי");
        queryClient.invalidateQueries({ queryKey: ["status"] });
      } else if (error instanceof ApiError && error.status === 429) {
        toast.error("הגעתם למכסת המיילים היומית");
      } else {
        toast.error("השליחה נכשלה");
      }
    },
  });
}
