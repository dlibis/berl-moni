import { useLetterReport } from "../../hooks/use-letter-report";
import { ReportGridTable } from "./report-grid-table";

export function ReportAppendix() {
  const appendix = useLetterReport()?.appendix;
  if (!appendix) return null;
  return (
    <section className="space-y-6 rounded-lg border bg-card p-5">
      <h2>נספח: הנתונים המלאים</h2>
      <ReportGridTable rows={appendix.table.rows} spans={appendix.table.spans} />
      {appendix.budget_history.map((history) => (
        <div key={history.label} className="space-y-2">
          <h3 className="text-center">{history.label}</h3>
          <ReportGridTable rows={[history.table.columns, ...history.table.rows]} />
        </div>
      ))}
      {appendix.decision_links.length ? (
        <div>
          <h3 className="mb-2">קישורים להחלטות ממשלה</h3>
          <ul className="space-y-1 text-sm" dir="ltr">
            {appendix.decision_links.map((link) => (
              <li key={link} className="break-all">
                <a className="text-[hsl(var(--report-master))] underline" href={link} target="_blank" rel="noreferrer">
                  {link}
                </a>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {appendix.staffing_changes ? (
        <p>
          <span className="text-muted-foreground">שינויים בכוח אדם: </span>
          {appendix.staffing_changes}
        </p>
      ) : null}
    </section>
  );
}
