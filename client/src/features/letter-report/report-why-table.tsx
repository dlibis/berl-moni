import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../../components/ui/table";
import type { LetterReport } from "../letters/types";

export function ReportWhyTable({ why }: { why: LetterReport["why"] }) {
  return (
    <section>
      <h2 className="mb-3 text-xl font-semibold">למה</h2>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>תוכנית</TableHead>
            <TableHead>סכום (אלפי ₪)</TableHead>
            <TableHead>כיוון</TableHead>
            <TableHead>במעקב</TableHead>
            <TableHead>שימושים</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {why.map((row) => (
            <TableRow key={row.code}>
              <TableCell>
                <span className="font-mono">{row.code}</span> {row.name}
              </TableCell>
              <TableCell className="tabular-nums">
                {row.amount.toLocaleString("he-IL")}
              </TableCell>
              <TableCell>
                {row.direction === "in" ? "תוספת" : "הפחתה"}
              </TableCell>
              <TableCell>{row.master ? "★" : ""}</TableCell>
              <TableCell>{row.uses || "—"}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </section>
  );
}
