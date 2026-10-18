import type { LetterReport } from "../letters/types";

export function ReportHeader({ header }: { header: LetterReport["header"] }) {
  return (
    <section className="space-y-2">
      {header.scanned ? (
        <p
          role="alert"
          className="rounded-md border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900"
        >
          מכתב סרוק — יש לאמת מול המקור
        </p>
      ) : null}
      {header.letterhead.map((line) => (
        <p key={line}>{line}</p>
      ))}
      <a
        className="text-sm underline"
        href={header.source}
        target="_blank"
        rel="noreferrer"
      >
        המכתב המקורי (PDF)
      </a>
    </section>
  );
}
