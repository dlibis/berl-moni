import { FormEvent, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { write } from "../../lib/api";
import { Button } from "../../components/ui/button";
import { Field } from "../../components/field";

const validEmail = (value: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
export function EmailForm({ initial, onDone }: { initial?: string; onDone: () => void }) {
  const queryClient = useQueryClient();
  const [email, setEmail] = useState(initial ?? "");
  const [error, setError] = useState("");
  const save = useMutation({
    mutationFn: async () => {
      // No update endpoint: add the new address first so a failed add never loses the old one.
      const next = email.trim().toLowerCase();
      if (initial === next) return;
      await write("/api/v1/mailing_list", "POST", { email: next });
      if (initial) await write(`/api/v1/mailing_list/${encodeURIComponent(initial)}`, "DELETE");
    },
    onSuccess: () => {
      toast.success("הנמען נשמר");
      queryClient.invalidateQueries({ queryKey: ["mailing"] });
      onDone();
    },
    onError: () => setError(initial ? "לא ניתן לעדכן את הנמען" : "לא ניתן להוסיף את הנמען. ייתכן שהוא קיים."),
  });
  function submit(event: FormEvent) {
    event.preventDefault();
    if (!validEmail(email)) {
      setError("יש להזין כתובת דוא״ל תקינה");
      return;
    }
    save.mutate();
  }
  return (
    <form onSubmit={submit} className="mt-5 space-y-4">
      <Field
        label="כתובת דוא״ל"
        type="email"
        dir="ltr"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        error={email && !validEmail(email) ? "יש להזין כתובת דוא״ל תקינה" : error}
      />
      {initial ? <p className="text-xs text-muted-foreground">העדכון מחליף את הכתובת הקיימת.</p> : null}
      <Button type="submit" disabled={save.isPending}>
        {save.isPending ? "שומר…" : "שמירה"}
      </Button>
    </form>
  );
}
