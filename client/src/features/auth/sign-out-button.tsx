import { useMutation, useQueryClient } from "@tanstack/react-query";
import { LogOut } from "lucide-react";
import { toast } from "sonner";
import { write } from "../../services/api";

export function SignOutButton() {
  const queryClient = useQueryClient();
  const signOut = useMutation({
    mutationFn: () => write("/api/auth/sign-out", "POST", {}),
    onSuccess: () => {
      queryClient.clear();
      queryClient.setQueryData(["session"], null);
    },
    onError: () => toast.error("היציאה נכשלה"),
  });
  return (
    <button
      type="button"
      onClick={() => signOut.mutate()}
      disabled={signOut.isPending}
      className="flex min-h-12 w-full items-center gap-3 rounded-md px-3 text-sm text-muted-foreground hover:bg-accent/60 hover:text-foreground lg:min-h-10"
    >
      <LogOut size={16} />
      יציאה
    </button>
  );
}
