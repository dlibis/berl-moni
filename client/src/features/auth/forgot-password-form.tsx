import { FormEvent, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import { write } from "../../services/api";
import { Button } from "../../components/ui/button";
import { Field } from "../../components/field";

export function ForgotPasswordForm({ onDone }: { onDone: () => void }) {
  const [email, setEmail] = useState("");
  const request = useMutation({
    mutationFn: () =>
      write("/api/auth/request-password-reset", "POST", {
        email: email.trim(),
        redirectTo: `${location.origin}/reset-password`,
      }),
    onSuccess: () => {
      toast.success("אם הכתובת רשומה, נשלח אליה קישור לאיפוס");
      onDone();
    },
  });
  function submit(event: FormEvent) {
    event.preventDefault();
    request.mutate();
  }
  return (
    <form onSubmit={submit} className="mt-5 space-y-4">
      <Field
        label="כתובת דוא״ל"
        type="email"
        dir="ltr"
        required
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        error={request.isError ? "לא ניתן לשלוח קישור כעת" : undefined}
      />
      <Button type="submit" disabled={request.isPending}>
        {request.isPending ? "שולח…" : "שליחת קישור"}
      </Button>
    </form>
  );
}
