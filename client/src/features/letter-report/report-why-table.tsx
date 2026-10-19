import { useLetterReport } from "../../hooks/use-letter-report";
import { UNIT, amount } from "./report-format";
import { WhyProgramCell } from "./why-program-cell";
import { WhyUsesCell } from "./why-uses-cell";

/** One row per destination the chart shows, in its order; then the ones it folds into 'עוד N',
 * in a sub-table — the only rows with an amount, since the chart shows the others'. */
export function ReportWhyTable() {
  const why = useLetterReport()?.why;
  if (!why?.shown.length) return null;
  const head = "px-3 py-2 text-start font-medium";
  const headRow = "border-b bg-muted/60 text-muted-foreground";
  const foldedTotal = why.folded.reduce((sum, row) => sum + row.amount, 0);
  return (
    <section className="rounded-lg border bg-card p-5 text-sm">
      <h2>למה עובר הכסף</h2>
      <p className="mt-2 text-[11px] text-muted-foreground">לפי סדר הגודל בתרשים</p>
      <div className="mt-5 overflow-hidden rounded-md border">
        <table className="w-full border-collapse">
          <thead>
            <tr className={headRow}>
              <th className={head}>תוכנית</th>
              <th className={head}>למה</th>
            </tr>
          </thead>
          <tbody>
            {why.shown.map((row) => (
              <tr key={row.code} className="border-b last:border-0">
                <WhyProgramCell row={row} />
                <WhyUsesCell row={row} />
              </tr>
            ))}
            {why.folded.length ? (
              <>
                <tr>
                  <td colSpan={2} className="px-3 py-2">
                    עוד {why.folded.length} תוכניות · +{amount(foldedTotal)} {UNIT}
                  </td>
                </tr>
                <tr>
                  <td colSpan={2} className="px-3 pb-3">
                    <div className="overflow-hidden rounded-md border">
                      <table className="w-full border-collapse">
                        <thead>
                          <tr className={headRow}>
                            <th className={head}>תוכנית</th>
                            <th className={head}>למה</th>
                            <th className={`${head} w-24 text-center`}>{UNIT}</th>
                          </tr>
                        </thead>
                        <tbody>
                          {why.folded.map((row) => (
                            <tr key={row.code} className="border-b last:border-0">
                              <WhyProgramCell row={row} />
                              <WhyUsesCell row={row} />
                              <td className="px-3 py-2 text-center align-top tabular-nums" dir="ltr">
                                +{amount(row.amount)}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </td>
                </tr>
              </>
            ) : null}
          </tbody>
        </table>
      </div>
      {why.sources.length ? (
        <p className="mt-3 text-[11px] text-muted-foreground">
          התוכניות שמהן נלקח הכסף (<span className="font-mono">{why.sources.join(", ")}</span>): המכתב אינו מפרט סיבה
        </p>
      ) : null}
    </section>
  );
}
