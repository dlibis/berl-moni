import { dateTime } from "../../utils/date-time";
import { useStatus } from "../../hooks/use-status";
import { RefreshCw } from "lucide-react";

export function LastScanLine() {
  const status = useStatus();
  if (status.isPending || status.isError || !status.data) return null;
  return (
    <div className="flex min-w-0 flex-wrap justify-end items-center gap-x-4 gap-y-2 text-sm text-muted-foreground">
      <span className="inline-flex items-center gap-1.5">
        <RefreshCw size={16} aria-hidden />
        עדכון אחרון:{" "}
        {status.data.last_feed_refresh_at
          ? dateTime(status.data.last_feed_refresh_at)
          : "אין נתונים"}
      </span>
    </div>
  );
}
