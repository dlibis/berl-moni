import { useLetterReport } from "../../hooks/use-letter-report";

export function ReportSummary() {
  const report = useLetterReport();
  if (!report) return null;
  const { header, summary } = report;
  const label = "w-32 bg-muted/60 px-3 py-2.5 text-start align-middle font-medium text-muted-foreground sm:w-44";
  const value = "px-3 py-2.5 align-middle";
  return (
    <section className="rounded-lg border bg-card p-5">
      <h2>סיכום פנייה תקציבית</h2>
      {header.letterhead.length ? (
        <p className="mt-2 text-[11px] text-muted-foreground">{header.letterhead.join(" · ")}</p>
      ) : null}
      {header.scanned ? (
        <p role="alert" className="mt-1 text-sm text-destructive">
          מכתב סרוק — יש לאמת מול המקור
        </p>
      ) : null}
      <div className="mt-5 overflow-hidden rounded-md border">
        <table className="w-full border-collapse text-sm">
          <tbody>
            {summary.map((row) => (
              <tr key={row.label} className="border-b last:border-0">
                <th className={label}>{row.label}</th>
                <td className={value}>{row.value}</td>
              </tr>
            ))}
            {header.source ? (
              <tr>
                <th className={label}>המכתב המקורי</th>
                <td className={`${value} break-all text-[11px]`} dir="ltr">
                  <a className="text-[hsl(var(--report-master))] underline" href={header.source} target="_blank" rel="noreferrer">
                    {header.source}
                  </a>
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </section>
  );
}
