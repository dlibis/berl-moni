import { Link } from "react-router-dom";
import { TableCell, TableRow } from "../../components/ui/table";
import { dateTime, day } from "../../utils/date-time";
import { LetterActions } from "./letter-actions";
import { LetterStatusBadge } from "./letter-status-badge";
import type { LetterItem } from "./types";

export function LetterRow({ letter }: { letter: LetterItem }) {
  const hasReport = letter.analysis_status === "analyzed" && !letter.legacy;
  const date = letter.letter_date ? day(letter.letter_date) : "—";
  return (
    <TableRow>
      <TableCell>
        {hasReport ? (
          <Link className="underline" to={`/letters/${letter.slug}`}>
            {date}
          </Link>
        ) : (
          date
        )}
      </TableCell>
      <TableCell className="font-mono">
        {letter.request_numbers.join(", ") || "—"}
      </TableCell>
      <TableCell>{letter.ministry ?? "—"}</TableCell>
      <TableCell>
        <LetterStatusBadge letter={letter} />
      </TableCell>
      <TableCell>{dateTime(letter.last_sent_at ?? undefined)}</TableCell>
      <TableCell>
        <LetterActions letter={letter} />
      </TableCell>
    </TableRow>
  );
}
