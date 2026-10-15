import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { write, ApiError } from "../../lib/api";

export function useRecover() {
  const queryClient = useQueryClient();
  const refresh = () => queryClient.invalidateQueries({ queryKey: ["status"] });
  return useMutation({
    mutationFn: ({ path }: { path: string }) => write<{ status: string }>(path, "POST"),
    onSuccess: () => {
      toast.success("הפעולה נשמרה");
      refresh();
    },
    onError: (error) => {
      if (error instanceof ApiError && error.status === 409) {
        toast.error("הנתונים השתנו, הכרטיס רוענן");
        refresh();
      } else toast.error("הפעולה נכשלה");
    },
  });
}
