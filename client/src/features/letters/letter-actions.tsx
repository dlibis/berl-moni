import { useState } from "react";
import { Link } from "react-router-dom";
import { ApiError } from "../../services/api";
import { Button } from "../../components/ui/button";
import { AlertDialog } from "../../components/ui/alert-dialog";
import { useAnalyzeLetter } from "../../hooks/use-analyze-letter";
import { useSendLetter } from "../../hooks/use-send-letter";
import { ReanalyzeMenu } from "./reanalyze-menu";
import { SendConfirmDialog } from "./send-confirm-dialog";
import type { LetterItem } from "./types";

export function LetterActions({ letter }: { letter: LetterItem }) {
  const [confirmSend, setConfirmSend] = useState(false);
  const analyze = useAnalyzeLetter();
  const send = useSendLetter();
  const { slug, analysis_status: status } = letter;
  const analyzed = status === "analyzed";
  const canAnalyze =
    ["discovered", "failed"].includes(status) ||
    (analyzed && letter.needs_analysis);
  const canReanalyze = analyzed || letter.legacy;
  const hasReport = analyzed && !letter.legacy;
  const canSend =
    analyzed && letter.relevant && letter.complete && !letter.legacy;
  const sendBlocker = !analyzed
    ? "יש לנתח את המכתב לפני שליחה"
    : letter.legacy
      ? "יש לנתח מחדש לפני שליחה"
      : !letter.relevant
        ? "המכתב לא רלוונטי"
        : "הניתוח לא הושלם";
  const sendNow = (resend = false) =>
    send.mutate(
      { slug, resend },
      {
        onSuccess: () => setConfirmSend(false),
        onError: (error) => {
          if (
            error instanceof ApiError &&
            error.status === 409 &&
            error.message === "confirm_resend"
          )
            setConfirmSend(true);
        },
      },
    );
  return (
    <div className="flex flex-wrap justify-end gap-1">
      {hasReport ? (
        <Button asChild variant="outline" size="sm">
          <Link to={`/letters/${slug}`}>צפייה</Link>
        </Button>
      ) : null}
      {canAnalyze ? (
        <Button
          variant="outline"
          size="sm"
          disabled={analyze.isPending}
          onClick={() => analyze.mutate({ slug })}
        >
          ניתוח
        </Button>
      ) : null}
      <span title={canSend ? undefined : sendBlocker}>
        <Button
          size="sm"
          disabled={!canSend || send.isPending}
          onClick={() =>
            letter.send_count > 0 ? setConfirmSend(true) : sendNow()
          }
        >
          שליחה
        </Button>
      </span>
      <AlertDialog open={confirmSend} onOpenChange={setConfirmSend}>
        <SendConfirmDialog
          pending={send.isPending}
          onConfirm={() => sendNow(true)}
        />
      </AlertDialog>
      {canReanalyze ? <ReanalyzeMenu slug={slug} /> : null}
    </div>
  );
}
