import { AlertTriangle, RefreshCw } from "lucide-react";
import { Button } from "../../components/ui/button";
import {
  AlertDialog,
  AlertDialogTrigger,
} from "../../components/ui/alert-dialog";
import { ConfirmDialog } from "../../components/confirm-dialog";
import { day } from "../../utils/date-time";
import { useRecover } from "../../hooks/use-recover";
import { useStatus } from "../../hooks/use-status";

export function FailedSendRunCard() {
  const run = useStatus().data?.failed_send_run;
  const recover = useRecover();
  if (!run) return null;
  return (
    <section className="mb-8 rounded-lg border border-destructive/30 bg-destructive/5 p-5">
      <div className="flex items-center gap-2 text-destructive">
        <AlertTriangle size={20} />
        <h2 className="text-xl font-semibold">שליחה שנכשלה</h2>
      </div>
      <p className="mt-4 text-sm">
        תאריך: {day(run.day)} · נשלחו {run.sent_messages} הודעות · נותרו{" "}
        {run.unsent_messages}
      </p>
      <p className="mt-2 text-sm">שגיאה: {run.error}</p>
      {/^4(?!29)/.test(run.error) ? (
        <p className="mt-2 text-sm">
          יש לתקן תחילה את כתובות השליחה או את רשימת התפוצה, משום שההשלמה משחזרת
          את אותה תמונת מצב.
        </p>
      ) : null}
      <div className="mt-5 flex flex-wrap gap-2">
        {!run.keys_expired ? (
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button>
                <RefreshCw size={16} />
                השלמת השליחה
              </Button>
            </AlertDialogTrigger>
            <ConfirmDialog
              title="להשלים את השליחה?"
              description="השליחה תמשיך רק אל הנמענים שטרם קיבלו את ההודעות בתמונת המצב הקיימת."
              action="השלמת השליחה"
              pending={recover.isPending}
              onConfirm={() =>
                recover.mutate({ path: `/api/v1/send-runs/${run.id}/resume` })
              }
            />
          </AlertDialog>
        ) : null}
        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button variant="outline">ביטול ושליחה ביום השליחה הבא</Button>
          </AlertDialogTrigger>
          <ConfirmDialog
            title="לבטל את השליחה?"
            description="המכתבים יישלחו ביום השליחה הבא לכל הנמענים, גם למי שכבר קיבלו אותם."
            action="ביטול השליחה"
            destructive
            pending={recover.isPending}
            onConfirm={() =>
              recover.mutate({ path: `/api/v1/send-runs/${run.id}/abandon` })
            }
          />
        </AlertDialog>
      </div>
    </section>
  );
}
