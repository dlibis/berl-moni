import { RotateCcw } from "lucide-react";
import { Button } from "../../components/ui/button";
import {
  AlertDialog,
  AlertDialogTrigger,
} from "../../components/ui/alert-dialog";
import { ConfirmDialog } from "../../components/confirm-dialog";
import { dateTime } from "../../utils/date-time";
import { useRecover } from "../../hooks/use-recover";
import { useStatus } from "../../hooks/use-status";

export function FailedLettersList() {
  const letters = useStatus().data?.failed_letters ?? [];
  const recover = useRecover();
  if (letters.length === 0) return null;
  return (
    <section className="mt-8">
      <h2 className="text-xl font-semibold">מכתבים שנכשלו</h2>
      <div className="mt-4 space-y-3">
        {letters.map((letter) => (
          <div
            key={letter.slug}
            className="flex flex-wrap items-center justify-between gap-3 rounded-lg border bg-card p-4"
          >
            <div className="min-w-0">
              <p className="truncate font-mono text-sm">{letter.slug}</p>
              <p className="text-xs text-muted-foreground">
                {letter.reason} · {dateTime(letter.scanned_at)}
              </p>
            </div>
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button variant="outline">
                  <RotateCcw size={16} />
                  סריקה מחדש
                </Button>
              </AlertDialogTrigger>
              <ConfirmDialog
                title="לסרוק מחדש?"
                description={`המכתב ${letter.slug} יוסר מההמתנה וייסרק שוב בהפעלה הבאה.`}
                action="סריקה מחדש"
                pending={recover.isPending}
                onConfirm={() =>
                  recover.mutate({
                    path: `/api/v1/letters/${encodeURIComponent(letter.slug)}/retry`,
                  })
                }
              />
            </AlertDialog>
          </div>
        ))}
      </div>
    </section>
  );
}
