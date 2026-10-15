import { ErrorState } from "../../components/error-state";
import { Loading } from "../../components/loading";
import { dateTime, day } from "../../utils/date-time";
import { useStatus } from "../../hooks/use-status";

export function LastScanCard() {
  const status = useStatus();
  if (status.isPending) return <Loading />;
  if (status.isError || !status.data) return <ErrorState />;
  const scan = status.data.latest_scan;
  return (
    <section className="rounded-lg border bg-card p-5">
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
          {scan.reason ? (
            <div className="col-span-2 text-destructive">
              סיבה: {scan.reason}
            </div>
          ) : null}
        </dl>
      ) : (
        <p className="mt-4 text-muted-foreground">עדיין לא בוצעה סריקה</p>
      )}
      <p className="mt-5 text-sm text-muted-foreground">
        יום השליחה הבא:{" "}
        {status.data.next_scheduled_send_day
          ? day(status.data.next_scheduled_send_day)
          : "לא נקבע"}
      </p>
    </section>
  );
}
