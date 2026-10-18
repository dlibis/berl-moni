import type { LetterReport, ReportItem } from "../letters/types";

const thousands = (amount: number) => `${amount.toLocaleString("he-IL")}`;

function Items({ items }: { items: ReportItem[] }) {
  return (
    <ul className="space-y-1 text-sm">
      {items.map((item) => (
        <li key={item.code} className="flex justify-between gap-4">
          <span>
            <span className="font-mono">{item.code}</span> {item.name}
          </span>
          <span className="tabular-nums">{thousands(item.amount)}</span>
        </li>
      ))}
    </ul>
  );
}

export function ReportMoneyFlow({
  flow,
}: {
  flow: LetterReport["money_flow"];
}) {
  return (
    <section>
      <h2 className="mb-1 text-xl font-semibold">מקורות ויעדים</h2>
      <p className="mb-3 text-sm text-muted-foreground">סכומים באלפי ₪</p>
      <div className="grid gap-6 md:grid-cols-2">
        <div className="space-y-4">
          <h3 className="font-semibold">מקורות</h3>
          {flow.hubs.map((hub) => (
            <div key={hub.name}>
              {hub.name ? <h4 className="mb-1 text-sm">{hub.name}</h4> : null}
              <Items items={hub.items} />
            </div>
          ))}
        </div>
        <div className="space-y-2">
          <h3 className="font-semibold">יעדים</h3>
          <Items items={flow.destinations} />
          {flow.folded.length ? (
            <details>
              <summary className="cursor-pointer text-sm">
                עוד {flow.folded.length}
              </summary>
              <div className="mt-2">
                <Items items={flow.folded} />
              </div>
            </details>
          ) : null}
        </div>
      </div>
    </section>
  );
}
