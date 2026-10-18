import type { LetterReport } from "../letters/types";

export function ReportSummary({
  summary,
}: {
  summary: LetterReport["summary"];
}) {
  const rows: [string, string | number][] = [
    ["תאריך", summary.date],
    ["מס' פנייה", summary.request_number],
    ["סך הפנייה (אלפי ₪)", summary.total_amount],
    ["כספים קואליציוניים", summary.coalition_funds],
    ["מספר תוכניות", summary.program_count],
    ["תוכניות במעקב", summary.master_count],
  ];
  return (
    <section>
      <h2 className="mb-3 text-xl font-semibold">סיכום</h2>
      <dl className="grid gap-x-8 gap-y-2 sm:grid-cols-2">
        {rows.map(([label, value]) => (
          <div key={label} className="flex gap-2">
            <dt className="text-muted-foreground">{label}:</dt>
            <dd>{value === "" ? "—" : value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
