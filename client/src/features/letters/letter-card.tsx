import { day } from "../../utils/date-time";
import { LetterActions } from "./letter-actions";
import { LetterStatusBadge } from "./letter-status-badge";
import type { LetterItem } from "./types";

export function LetterCard({ letter }: { letter: LetterItem }) {
  const date = letter.letter_date ? day(letter.letter_date) : "—";
  return (
    <div className="space-y-2 rounded-lg border bg-card p-4">
      <div className="flex items-center justify-between gap-2">
        <span>{date}</span>
        <LetterStatusBadge letter={letter} />
      </div>
      <p className="font-mono text-sm">
        {letter.request_numbers.join(", ") || "—"}
      </p>
      <p className="text-sm">{letter.ministry ?? "—"}</p>
      <LetterActions letter={letter} />
    </div>
  );
}
