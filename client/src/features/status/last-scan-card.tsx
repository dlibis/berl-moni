import { dateTime, day } from "../../utils/date-time";
import { useStatus } from "../../hooks/use-status";

const STATUS: Record<string, string> = {
  sent: "נשלח",
  nothing_new: "אין חדש",
  failed: "נכשל",
};

export function LastScanLine() {
  const status = useStatus();
  if (status.isPending || status.isError || !status.data) return null;
  const scan = status.data.latest_scan;
  const next = status.data.next_scheduled_send_day
    ? `שליחה הבאה ${day(status.data.next_scheduled_send_day)}`
    : null;
  const parts = scan
    ? [
        dateTime(scan.ran_at),
        STATUS[scan.status] ?? scan.status,
        scan.failed ? `${scan.failed} נכשלו` : null,
        scan.reason,
        next,
      ]
    : ["לא בוצעה", next];
  return (
    <p className="mt-1 text-sm text-muted-foreground">
      סריקה אחרונה {parts.filter(Boolean).join(" · ")}
    </p>
  );
}
