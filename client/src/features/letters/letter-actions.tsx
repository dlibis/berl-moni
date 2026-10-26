import { useState } from "react";
import { MoreVertical, Send } from "lucide-react";
import { ApiError } from "../../services/api";
import { Button } from "../../components/ui/button";
import { AlertDialog } from "../../components/ui/alert-dialog";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "../../components/ui/popover";
import { ConfirmDialog } from "../../components/confirm-dialog";
import { useAnalyzeLetter } from "../../hooks/use-analyze-letter";
import { usePatchLetter } from "../../hooks/use-patch-letter";
import { useSendLetter } from "../../hooks/use-send-letter";
import { SendConfirmDialog } from "./send-confirm-dialog";
import type { LetterItem } from "./types";

export function LetterActions({
  letter,
  compact = false,
}: {
  letter: LetterItem;
  compact?: boolean;
}) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [confirmSend, setConfirmSend] = useState(false);
  const [confirmReanalyze, setConfirmReanalyze] = useState(false);
  const analyze = useAnalyzeLetter();
  const patch = usePatchLetter();
  const send = useSendLetter();
  const { slug, analysis_status: status } = letter;
  const analyzed = status === "analyzed";
  const canAnalyze =
    ["discovered", "failed"].includes(status) ||
    (analyzed && letter.needs_analysis);
  const canReanalyze = analyzed || letter.legacy;
  const canSend =
    analyzed && letter.relevant && letter.complete && !letter.legacy;
  const analyzeReady = canAnalyze || canReanalyze;
  const analyzeBlocker = analyzeReady
    ? undefined
    : "הניתוח כבר בתהליך";
  const sendBlocker = !analyzed
    ? "יש לנתח את הפנייה לפני שליחה"
    : letter.legacy
      ? "יש לנתח מחדש לפני שליחה"
      : !letter.relevant
        ? "הפנייה לא רלוונטית"
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
  const closeMenu = () => setMenuOpen(false);
  const overflow = (
    <Popover open={menuOpen} onOpenChange={setMenuOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          className={compact ? "h-8 w-8 p-0" : undefined}
          aria-label="פעולות נוספות"
        >
          <MoreVertical />
        </Button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-auto p-1">
        {compact ? (
          <>
            <span title={analyzeBlocker} className="block">
              <Button
                variant="ghost"
                size="sm"
                className="w-full justify-start"
                disabled={analyze.isPending || !analyzeReady}
                onClick={() => {
                  closeMenu();
                  if (canAnalyze) analyze.mutate({ slug });
                  else setConfirmReanalyze(true);
                }}
              >
                ניתוח
              </Button>
            </span>
            <span title={canSend ? undefined : sendBlocker} className="block">
              <Button
                variant="ghost"
                size="sm"
                className="w-full justify-start"
                disabled={!canSend || send.isPending}
                onClick={() => {
                  closeMenu();
                  letter.send_count > 0 ? setConfirmSend(true) : sendNow();
                }}
              >
                שליחה
              </Button>
            </span>
          </>
        ) : null}
        {!compact && canReanalyze ? (
          <Button
            variant="ghost"
            size="sm"
            className="w-full justify-start"
            onClick={() => {
              closeMenu();
              setConfirmReanalyze(true);
            }}
          >
            ניתוח מחדש
          </Button>
        ) : null}
        <Button
          variant="ghost"
          size="sm"
          className="w-full justify-start"
          disabled={patch.isPending}
          onClick={() => {
            closeMenu();
            patch.mutate({
              slug,
              requires_review: !letter.requires_review,
            });
          }}
        >
          {letter.requires_review ? "בטל דורש עיון" : "דורש עיון"}
        </Button>
        <Button
          variant="ghost"
          size="sm"
          className="w-full justify-start"
          disabled={patch.isPending}
          onClick={() => {
            closeMenu();
            patch.mutate({ slug, passed: !letter.passed });
          }}
        >
          {letter.passed ? "לא עברה" : "סמן כעברה"}
        </Button>
      </PopoverContent>
    </Popover>
  );
  const dialogs = (
    <>
      <AlertDialog open={confirmSend} onOpenChange={setConfirmSend}>
        <SendConfirmDialog
          pending={send.isPending}
          onConfirm={() => sendNow(true)}
        />
      </AlertDialog>
      <AlertDialog open={confirmReanalyze} onOpenChange={setConfirmReanalyze}>
        <ConfirmDialog
          title="לנתח מחדש?"
          description="ניתוח מחדש יעלה קריאה נוספת למודל"
          action="ניתוח מחדש"
          pending={analyze.isPending}
          onConfirm={() => analyze.mutate({ slug, reanalyze: true })}
        />
      </AlertDialog>
    </>
  );
  if (compact)
    return (
      <div className="flex justify-end">
        {overflow}
        {dialogs}
      </div>
    );
  return (
    <div className="flex flex-wrap justify-end gap-1">
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
      <span title={canSend ? undefined : sendBlocker} className="inline-flex">
        <Button
          size="sm"
          className="size-8 p-0 leading-none"
          aria-label="שליחה"
          disabled={!canSend || send.isPending}
          onClick={() =>
            letter.send_count > 0 ? setConfirmSend(true) : sendNow()
          }
        >
          <Send className="text-white" />
        </Button>
      </span>
      {overflow}
      {dialogs}
    </div>
  );
}
