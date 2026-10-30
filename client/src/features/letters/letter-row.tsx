import { useLayoutEffect, useRef, useState, type ReactNode } from "react";
import { TableCell, TableRow } from "../../components/ui/table";
import { day } from "../../utils/date-time";
import { LetterActions } from "./letter-actions";
import {
  LetterPassedBadge,
  LetterReportCell,
  LetterRelevantBadge,
  RequiresReviewIcon,
} from "./letter-status-badge";
import type { LetterItem } from "./types";

export function LetterRow({ letter }: { letter: LetterItem }) {
  const date = letter.letter_date ? day(letter.letter_date) : "—";
  const numbers = letter.request_numbers.join(", ");
  return (
    <TableRow>
      <TableCell>
        <RequiresReviewIcon show={letter.requires_review} />
      </TableCell>
      <TableCell className="whitespace-nowrap">{date}</TableCell>
      <OverflowCell dir="ltr" className="font-mono" hint={numbers}>
        {numbers || "—"}
      </OverflowCell>
      <OverflowCell hint={letter.ministry ?? undefined}>
        {letter.ministry ?? "—"}
      </OverflowCell>
      <TableCell>
        <LetterRelevantBadge letter={letter} />
      </TableCell>
      <TableCell>
        <LetterPassedBadge letter={letter} />
      </TableCell>
      <TableCell className="w-16 px-1 text-center">
        <LetterReportCell letter={letter} />
      </TableCell>
      <TableCell className="w-12 px-1">
        <LetterActions letter={letter} compact />
      </TableCell>
    </TableRow>
  );
}

/** Ellipsis + hover hint only when the cell actually overflows. */
function OverflowCell({
  hint,
  className,
  children,
  dir,
}: {
  hint?: string;
  className?: string;
  children: ReactNode;
  dir?: "ltr" | "rtl";
}) {
  const ref = useRef<HTMLTableCellElement>(null);
  const [overflow, setOverflow] = useState(false);
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    const sync = () => setOverflow(el.scrollWidth > el.clientWidth + 1);
    sync();
    const ro = new ResizeObserver(sync);
    ro.observe(el);
    return () => ro.disconnect();
  }, [children]);
  return (
    <TableCell
      ref={ref}
      dir={dir}
      className={`truncate ${className ?? ""}`}
      title={overflow ? hint : undefined}
    >
      {children}
    </TableCell>
  );
}
