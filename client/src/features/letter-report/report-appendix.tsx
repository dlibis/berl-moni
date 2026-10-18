import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../../components/ui/table";
import type { LetterReport, ReportTable } from "../letters/types";

function DataTable({ table }: { table: ReportTable }) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          {table.columns.map((column, i) => (
            <TableHead key={i}>{column}</TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {table.rows.map((row, i) => (
          <TableRow key={i}>
            {row.map((cell, j) => (
              <TableCell key={j}>{cell ?? ""}</TableCell>
            ))}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

export function ReportAppendix({
  appendix,
}: {
  appendix: LetterReport["appendix"];
}) {
  return (
    <section className="space-y-6">
      <h2 className="text-xl font-semibold">נספח</h2>
      <div>
        <h3 className="mb-2 font-semibold">טבלת התקציב</h3>
        <DataTable table={appendix.table} />
      </div>
      {appendix.budget_history.map((history) => (
        <div key={history.label}>
          <h3 className="mb-2 font-semibold">{history.label}</h3>
          <DataTable table={history.table} />
        </div>
      ))}
      {appendix.decision_links.length ? (
        <div>
          <h3 className="mb-2 font-semibold">קישורים להחלטות ממשלה</h3>
          <ul className="space-y-1 text-sm">
            {appendix.decision_links.map((link) => (
              <li key={link}>
                <a
                  className="underline"
                  href={link}
                  target="_blank"
                  rel="noreferrer"
                >
                  {link}
                </a>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {appendix.staffing_changes ? (
        <div>
          <h3 className="mb-2 font-semibold">שינויים בכוח אדם</h3>
          <p className="text-sm">{appendix.staffing_changes}</p>
        </div>
      ) : null}
    </section>
  );
}
