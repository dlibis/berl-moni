import { dateTime, day } from "../../utils/date-time";
import { useStatus } from "../../hooks/use-status";
import { CalendarClock, CircleAlert, CircleCheck, RefreshCw } from "lucide-react";

const STATUS: Record<string, string> = {
  sent: "נשלח",
  nothing_new: "אין חדש",
  failed: "נכשל",
};
const REASON: Record<string, string> = {
  feed_unreachable: "אתר הכנסת לא זמין",
  missing_settings: "חסרות הגדרות",
  list_over_cap: "רשימת התפוצה גדולה מדי",
  quota: "המכסה נוצלה",
  over_budget: "חריגה ממכסת השליחה",
  resend_error: "שגיאת שליחה",
  send_run_stuck: "השליחה נעצרה",
};

export function LastScanLine() {
  const status = useStatus();
  if (status.isPending || status.isError || !status.data) return null;
  const scan = status.data.latest_scan;
  const ResultIcon = scan?.status === "failed" ? CircleAlert : CircleCheck;
  return (
    <div className="flex min-w-0 flex-wrap items-center gap-x-4 gap-y-2 text-sm text-muted-foreground">
      <span className="inline-flex flex-wrap items-center gap-1.5">
        {scan && <ResultIcon size={16} className={scan.status === "failed" ? "text-destructive" : undefined} aria-hidden />}
        <span className="font-medium text-foreground">
          בדיקת שליחה: {scan ? (STATUS[scan.status] ?? scan.status) : "אין נתונים"}
        </span>
        {scan?.reason && <span>— {REASON[scan.reason] ?? scan.reason}</span>}
        {scan?.failed ? <span>· {scan.failed} נכשלו</span> : null}
        {scan && <span>· {dateTime(scan.ran_at)}</span>}
      </span>
      {status.data.next_scheduled_send_day && (
        <span className="inline-flex items-center gap-1.5">
          <CalendarClock size={16} aria-hidden />
          שליחה הבאה: {day(status.data.next_scheduled_send_day)}
        </span>
      )}
      <span className="inline-flex items-center gap-1.5">
        <RefreshCw size={16} aria-hidden />
        רענון: {status.data.last_feed_refresh_at ? dateTime(status.data.last_feed_refresh_at) : "אין נתונים"}
      </span>
    </div>
  );
}
