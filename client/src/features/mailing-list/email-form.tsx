import { FormEvent, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { write } from "../../services/api";
import { Button } from "../../components/ui/button";
import { Field } from "../../components/field";

const validEmail = (value: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
export function EmailForm({
  initialEmail,
  initialName,
  onDone,
}: {
  initialEmail?: string;
  initialName?: string;
  onDone: () => void;
}) {
  const queryClient = useQueryClient();
  const [email, setEmail] = useState(initialEmail ?? "");
  const [name, setName] = useState(initialName ?? "");
  const [error, setError] = useState("");
  const save = useMutation({
    mutationFn: async () => {
      // No update endpoint: add the new address first so a failed add never loses the old one.
      const next = email.trim().toLowerCase();
      const nextName = name.trim();
      if (initialEmail === next && initialName === nextName) return;
      if (initialEmail === next) {
        await write("/api/v1/mailing_list", "PATCH", { email: next, name: nextName });
        return;
      }
      await write("/api/v1/mailing_list", "POST", { email: next, name: nextName });
      if (initialEmail)
        await write("/api/v1/mailing_list", "DELETE", { email: initialEmail });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["mailing"] });
      onDone();
    },
    onError: () =>
      setError(
        initialEmail
          ? "לא ניתן לעדכן את הנמען"
          : "לא ניתן להוסיף את הנמען. ייתכן שהוא קיים.",
      ),
  });
  function submit(event: FormEvent) {
    event.preventDefault();
    if (!validEmail(email)) {
      setError("יש להזין כתובת דוא״ל תקינה");
      return;
    }
    if (!name.trim()) {
      setError("יש להזין שם");
      return;
    }
    save.mutate();
  }
  return (
    <form onSubmit={submit} className="mt-5 space-y-4">
      <Field
        label="שם"
        value={name}
        onChange={(e) => setName(e.target.value)}
        error={name && !name.trim() ? "יש להזין שם" : undefined}
      />
      <Field
        label="כתובת דוא״ל"
        type="email"
        dir="ltr"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        error={
          email && !validEmail(email) ? "יש להזין כתובת דוא״ל תקינה" : error
        }
      />
      {initialEmail ? (
        <p className="text-xs text-muted-foreground">
          העדכון מחליף את הכתובת הקיימת.
        </p>
      ) : null}
      <Button type="submit" disabled={save.isPending}>
        {save.isPending ? "שומר…" : "שמירה"}
      </Button>
    </form>
  );
}
