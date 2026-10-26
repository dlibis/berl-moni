import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ApiError, write } from "../services/api";

type RefreshResult = { new: number; seen: number };

export function useRefreshLetters() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () =>
      write<RefreshResult>("/api/v1/letters/refresh", "POST"),
    onSuccess: (result) => {
      toast.success(`נמצאו ${result.new} פניות חדשות`);
      queryClient.invalidateQueries({ queryKey: ["letters"] });
    },
    onError: (error) => {
      if (error instanceof ApiError && error.status === 502) {
        toast.error("אתר הכנסת אינו זמין כעת");
      } else {
        toast.error("הרענון נכשל");
      }
    },
  });
}
