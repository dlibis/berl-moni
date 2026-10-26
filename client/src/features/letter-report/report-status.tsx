import { useParams } from "react-router-dom";
import { ErrorState } from "../../components/error-state";
import { Loading } from "../../components/loading";
import { dateTime } from "../../utils/date-time";
import { lastErrorLabel } from "../letters/last-error";
import { useLetter } from "../../hooks/use-letter";

/** Empty/loading/failure. A saved report is the page; a later failure is a note. */
export function ReportStatus() {
  const { slug = "" } = useParams();
  const letter = useLetter(slug);
  if (letter.isPending) return <Loading />;
  if (letter.isError) return <ErrorState />;
  const reason = lastErrorLabel(letter.data.last_error);
  const analyzed = letter.data.analyzed_at
    ? dateTime(letter.data.analyzed_at)
    : null;
  if (letter.data.report)
    return (
      <>
        {letter.data.report.header.scanned && letter.data.requires_review && (
          <p className="text-muted-foreground">
            מכתב סרוק: יש לבדוק את הנתונים מול המקור לפני שימוש בדוח.
          </p>
        )}
        {reason ? (
          <p className="text-muted-foreground">
            הניתוח האחרון נכשל. מוצג הניתוח
            {analyzed ? ` מ-${analyzed}` : " השמור"}. {reason}
          </p>
        ) : analyzed ? (
          <p className="text-muted-foreground text-sm mb-2">
            ניתוח אחרון: {analyzed}
          </p>
        ) : null}
      </>
    );
  if (reason) return <p className="text-destructive">{reason}</p>;
  return <p className="text-muted-foreground">הפנייה טרם נותחה</p>;
}
