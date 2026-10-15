import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, RefreshCw, RotateCcw } from "lucide-react";
import { toast } from "sonner";
import { get, write, ApiError } from "../lib/api";
import { Button } from "../components/ui/button";
import { AlertDialog, AlertDialogTrigger, ConfirmDialog } from "../components/ui/alert-dialog";
import { ErrorState, Loading, PageHeader } from "../components/states";

type Scan = {
  ran_at: string;
  status: string;
  reason?: string;
  letters_in_feed?: number;
  new_letters?: number;
  relevant?: number;
  failed?: number;
  emails_sent?: number;
};
type FailedLetter = { slug: string; reason: string; scanned_at: string };
type FailedRun = {
  id: number;
  day: string;
  failed_at: string;
  error: string;
  sent_messages: number;
  unsent_messages: number;
  keys_expired: boolean;
};
type Status = {
  latest_scan: Scan | null;
  next_scheduled_send_day: string | null;
  failed_letters: FailedLetter[];
  failed_send_run: FailedRun | null;
};
const dateTime = (value?: string) =>
  value
    ? new Intl.DateTimeFormat("he-IL", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value))
    : "—";

export function Home() {
  const queryClient = useQueryClient();
  const status = useQuery({ queryKey: ["status"], queryFn: () => get<Status>("/api/v1/status") });
  const refresh = () => queryClient.invalidateQueries({ queryKey: ["status"] });
  const recover = useMutation({
    mutationFn: ({ path }: { path: string }) => write<{ status: string }>(path, "POST"),
    onSuccess: () => {
      toast.success("הפעולה נשמרה");
      refresh();
    },
    onError: (error) => {
      if (error instanceof ApiError && error.status === 409) {
        toast.error("הנתונים השתנו, הכרטיס רוענן");
        refresh();
      } else toast.error("הפעולה נכשלה");
    },
  });
  if (status.isPending) return <Loading />;
  if (status.isError || !status.data) return <ErrorState />;
  const { latest_scan: scan, failed_letters: letters, failed_send_run: run } = status.data;
  return (
    <>
      <PageHeader title="ראשי" />
      <div className="grid gap-4 xl:grid-cols-2">
        <section className="rounded-lg border bg-card p-5 shadow-sm">
          <h2 className="text-xl font-semibold">סריקה אחרונה</h2>
          {scan ? (
            <dl className="mt-5 grid grid-cols-2 gap-4 text-sm">
              <div>
                <dt className="text-muted-foreground">מועד</dt>
                <dd>{dateTime(scan.ran_at)}</dd>
              </div>
              <div>
                <dt className="text-muted-foreground">סטטוס</dt>
                <dd>{scan.status}</dd>
              </div>
              <div>
                <dt className="text-muted-foreground">מכתבים חדשים</dt>
                <dd>{scan.new_letters ?? 0}</dd>
              </div>
              <div>
                <dt className="text-muted-foreground">רלוונטיים</dt>
                <dd>{scan.relevant ?? 0}</dd>
              </div>
              <div>
                <dt className="text-muted-foreground">נכשלו</dt>
                <dd>{scan.failed ?? 0}</dd>
              </div>
              <div>
                <dt className="text-muted-foreground">הודעות שנשלחו</dt>
                <dd>{scan.emails_sent ?? 0}</dd>
              </div>
              {scan.reason ? <div className="col-span-2 text-destructive">סיבה: {scan.reason}</div> : null}
            </dl>
          ) : (
            <p className="mt-4 text-muted-foreground">עדיין לא בוצעה סריקה</p>
          )}
          <p className="mt-5 text-sm text-muted-foreground">
            יום השליחה הבא: {status.data.next_scheduled_send_day ?? "לא נקבע"}
          </p>
        </section>
        {run ? (
          <section className="rounded-lg border border-destructive/30 bg-destructive/5 p-5">
            <div className="flex items-center gap-2 text-destructive">
              <AlertTriangle size={20} />
              <h2 className="text-xl font-semibold">שליחה שנכשלה</h2>
            </div>
            <p className="mt-4 text-sm">
              תאריך: {run.day} · נשלחו {run.sent_messages} הודעות · נותרו {run.unsent_messages}
            </p>
            <p className="mt-2 text-sm">שגיאה: {run.error}</p>
            {/^4(?!29)/.test(run.error) ? (
              <p className="mt-2 text-sm">
                יש לתקן תחילה את תיבת הדואר או את רשימת התפוצה, משום שההשלמה משחזרת את אותה תמונת מצב.
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
                    onConfirm={() => recover.mutate({ path: `/api/v1/send-runs/${run.id}/resume` })}
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
                  onConfirm={() => recover.mutate({ path: `/api/v1/send-runs/${run.id}/abandon` })}
                />
              </AlertDialog>
            </div>
          </section>
        ) : null}
      </div>
      {letters.length > 0 ? (
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
                      recover.mutate({ path: `/api/v1/letters/${encodeURIComponent(letter.slug)}/retry` })
                    }
                  />
                </AlertDialog>
              </div>
            ))}
          </div>
        </section>
      ) : null}
    </>
  );
}
