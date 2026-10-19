import type { LetterItem } from "./types";

const base = "rounded-full px-2 py-0.5 text-xs";

function label({
  analysis_status,
  legacy,
  needs_analysis,
  outdated,
  relevant,
}: LetterItem) {
  if (analysis_status === "discovered") return "לא נותח";
  if (analysis_status === "queued") return "בתור";
  if (analysis_status === "analyzing") return "בניתוח";
  if (analysis_status === "failed") return "נכשל";
  if (legacy) return "יש לנתח מחדש";
  if (needs_analysis) return "דרוש ניתוח";
  if (outdated) return "גרסה ישנה";
  return relevant ? "רלוונטי" : "לא רלוונטי";
}

export function LetterStatusBadge({ letter }: { letter: LetterItem }) {
  const failed = letter.analysis_status === "failed";
  return (
    <div className="flex flex-wrap items-center gap-1">
      <span
        className={`${base} ${failed ? "bg-destructive/10 text-destructive" : "bg-muted"}`}
        title={failed ? (letter.last_error ?? undefined) : undefined}
      >
        {label(letter)}
      </span>
      {!failed && letter.last_error ? (
        <span
          className={`${base} bg-destructive/10 text-destructive`}
          title={letter.last_error}
        >
          הניתוח האחרון נכשל
        </span>
      ) : null}
    </div>
  );
}
