import { day } from "../../utils/date-time";
import { LetterActions } from "./letter-actions";
import {
  LetterPassedBadge,
  LetterReportCell,
  LetterRelevantBadge,
  RequiresReviewIcon,
} from "./letter-status-badge";
import type { LetterItem } from "./types";

export function LetterCard({ letter }: { letter: LetterItem }) {
  const date = letter.letter_date ? day(letter.letter_date) : "—";
  return (
    <div className="space-y-2 rounded-lg border bg-card p-4">
      <div className="flex items-center justify-between gap-2">
        <span className="flex items-center gap-1">
          <RequiresReviewIcon show={letter.requires_review} />
          {date}
        </span>
        <div className="flex flex-wrap items-center justify-end gap-1">
          <LetterRelevantBadge letter={letter} />
          <LetterReportCell letter={letter} />
          <LetterPassedBadge letter={letter} />
        </div>
      </div>
      <p className="font-mono text-sm">
        {letter.request_numbers.join(", ") || "—"}
      </p>
      <p className="text-sm">{letter.ministry ?? "—"}</p>
      <LetterActions letter={letter} compact />
    </div>
  );
}
