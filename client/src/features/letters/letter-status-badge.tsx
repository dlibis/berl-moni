import type { LetterItem } from "./types";

const base = "rounded-full px-2 py-0.5 text-xs";

function label({
  analysis_status,
  legacy,
  needs_analysis,
  relevant,
}: LetterItem) {
  if (analysis_status === "failed") return "תקלה";
  if (["discovered", "queued", "analyzing"].includes(analysis_status))
    return "לא נותח";
  if (legacy) return "יש לנתח מחדש";
  if (needs_analysis) return "דורשים ניתוח";
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
      {letter.requires_review ? (
        <span className={`${base} bg-amber-500/15 text-amber-800`}>
          דורש עיון
        </span>
      ) : null}
      <span className={`${base} ${letter.passed ? "bg-green-500/15 text-green-800" : "bg-muted text-muted-foreground"}`}>
        {letter.passed ? "עברה" : "לא עברה"}
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
