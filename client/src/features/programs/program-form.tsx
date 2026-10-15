import { FormEvent, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { write } from "../../services/api";
import type { Program } from "./types";
import { Button } from "../../components/ui/button";
import { Field } from "../../components/field";

const validCode = (value: string) => /^\d{1,6}$/.test(value);
export function ProgramForm({
  initial,
  onDone,
}: {
  initial?: Program;
  onDone: () => void;
}) {
  const queryClient = useQueryClient();
  const [code, setCode] = useState(initial?.code ?? "");
  const [name, setName] = useState(initial?.name ?? "");
  const [error, setError] = useState("");
  const save = useMutation({
    mutationFn: () =>
      initial
        ? write<Program>(`/api/v1/master/${initial.code}`, "PUT", {
            code,
            name,
          })
        : write<Program>("/api/v1/master", "POST", { code, name }),
    onSuccess: () => {
      toast.success("התוכנית נשמרה");
      queryClient.invalidateQueries({ queryKey: ["programs"] });
      onDone();
    },
    onError: () => setError("לא ניתן לשמור את התוכנית. ייתכן שהקוד כבר קיים."),
  });
  function submit(event: FormEvent) {
    event.preventDefault();
    if (!validCode(code) || !name.trim()) {
      setError("יש למלא קוד בן עד שש ספרות ושם תוכנית");
      return;
    }
    save.mutate();
  }
  return (
    <form className="mt-5 space-y-4" onSubmit={submit}>
      <Field
        label="קוד תוכנית"
        value={code}
        maxLength={6}
        inputMode="numeric"
        onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
        error={
          !validCode(code) && code ? "קוד התוכנית מכיל ספרות בלבד" : undefined
        }
      />
      <Field
        label="שם התוכנית"
        value={name}
        onChange={(e) => setName(e.target.value)}
      />
      {error ? <p className="text-sm text-destructive">{error}</p> : null}
      <Button type="submit" disabled={save.isPending}>
        {save.isPending ? "שומר…" : "שמירה"}
      </Button>
    </form>
  );
}
