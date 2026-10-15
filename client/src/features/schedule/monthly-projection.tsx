import { useSchedule } from "../../hooks/use-schedule";

export function MonthlyProjection() {
  const schedule = useSchedule();
  if (!schedule.data) return null;
  const { projected_monthly_emails: projected, monthly_limit: limit } =
    schedule.data;
  return (
    <aside className="h-fit rounded-lg border bg-card p-5">
      <h2 className="text-xl font-semibold">תחזית חודשית</h2>
      <p className="mt-2 text-sm text-muted-foreground">
        התחזית מתעדכנת לאחר שמירת לוח השליחה.
      </p>
      <dl className="mt-5 space-y-3 text-sm">
        {Object.entries(projected).map(([month, emails]) => (
          <div key={month} className="flex justify-between gap-4">
            <dt>{month}</dt>
            <dd>
              {emails} מתוך {limit} הודעות
            </dd>
            {emails > limit ? (
              <dd className="col-span-2 text-destructive">
                התחזית חורגת מהמגבלה החודשית
              </dd>
            ) : null}
          </div>
        ))}
      </dl>
    </aside>
  );
}
