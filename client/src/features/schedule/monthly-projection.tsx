import { useSchedule } from "../../hooks/use-schedule";
import { month as monthName } from "../../utils/date-time";

export function MonthlyProjection() {
  const schedule = useSchedule();
  if (!schedule.data) return null;
  const { projected_monthly_emails: projected, monthly_limit: limit } =
    schedule.data;
  return (
    <aside className="h-fit rounded-lg border bg-card p-5">
      <h2 className="text-xl font-semibold">מכסת מיילים חודשית</h2>
      <p className="mt-2 text-sm text-muted-foreground">
        צפי לפי מועדי השליחה השמורים
      </p>
      <dl className="mt-5 grid grid-cols-[auto_auto] justify-start gap-x-8 gap-y-3 text-sm">
        {Object.entries(projected).map(([month, emails]) => (
          <div key={month} className="contents">
            <dt>{monthName(month)}</dt>
            <dd>
              {emails.toLocaleString()} / {limit.toLocaleString()}
            </dd>
            {emails > limit ? (
              <dd className="col-span-2 -mt-2 text-destructive">
                חריגה מהמכסה
              </dd>
            ) : null}
          </div>
        ))}
      </dl>
    </aside>
  );
}
