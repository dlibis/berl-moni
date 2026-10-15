import { FormEvent, useEffect, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { write } from "../../lib/api";
import { Button } from "../../components/ui/button";
import { Field } from "../../components/field";
import { ErrorState } from "../../components/error-state";
import { Loading } from "../../components/loading";
import { useMailbox, type MailboxData } from "./use-mailbox";

const email = (value: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
export function MailboxForm() {
  const queryClient = useQueryClient();
  const box = useMailbox();
  const [from, setFrom] = useState("");
  const [replyTo, setReplyTo] = useState("");
  const [error, setError] = useState("");
  useEffect(() => {
    if (box.data) {
      setFrom(box.data.from_address);
      setReplyTo(box.data.reply_to_address);
    }
  }, [box.data]);
  const save = useMutation({
    mutationFn: () =>
      write<MailboxData>("/api/v1/notifier", "POST", { from_address: from, reply_to_address: replyTo }),
    onSuccess: () => {
      toast.success("תיבת הדואר נשמרה");
      setError("");
      queryClient.invalidateQueries({ queryKey: ["mailbox"] });
    },
    onError: () => setError("לא ניתן לשמור את הכתובות"),
  });
  if (box.isPending) return <Loading />;
  if (box.isError) return <ErrorState />;
  function submit(event: FormEvent) {
    event.preventDefault();
    if (!email(from) || !from.toLowerCase().endsWith("@berl.site") || !email(replyTo)) {
      setError("יש למלא כתובת שולח ב־@berl.site וכתובת מענה תקינה");
      return;
    }
    save.mutate();
  }
  return (
    <form className="max-w-[560px] space-y-5 rounded-lg border bg-card p-5" onSubmit={submit}>
      <Field
        label="כתובת שולח"
        type="email"
        dir="ltr"
        value={from}
        onChange={(e) => setFrom(e.target.value)}
        helper="כתובת זו חייבת להסתיים ב־@berl.site."
        error={
          from && (!email(from) || !from.toLowerCase().endsWith("@berl.site"))
            ? "יש להזין כתובת ב־@berl.site"
            : undefined
        }
      />
      <Field
        label="תיבת מענה"
        type="email"
        dir="ltr"
        value={replyTo}
        onChange={(e) => setReplyTo(e.target.value)}
        helper="תשובות למכתבים יגיעו לתיבה זו."
        error={replyTo && !email(replyTo) ? "יש להזין כתובת דוא״ל תקינה" : undefined}
      />
      <p className="text-sm text-muted-foreground">
        המכתבים נשלחים מכתובת השולח, ותשובות מגיעות לתיבת המענה.
      </p>
      {error ? <p className="text-sm text-destructive">{error}</p> : null}
      <Button type="submit" disabled={save.isPending}>
        {save.isPending ? "שומר…" : "שמירה"}
      </Button>
    </form>
  );
}
