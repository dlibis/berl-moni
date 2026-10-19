import { useParams } from "react-router-dom";
import { ErrorState } from "../../components/error-state";
import { Loading } from "../../components/loading";
import { useLetter } from "../../hooks/use-letter";

/** Loading, failure, or 'not analyzed yet'; nothing once the report is there. */
export function ReportStatus() {
  const { slug = "" } = useParams();
  const letter = useLetter(slug);
  if (letter.isPending) return <Loading />;
  if (letter.isError) return <ErrorState />;
  if (letter.data.report === null)
    return <p className="text-muted-foreground">המכתב טרם נותח</p>;
  return null;
}
