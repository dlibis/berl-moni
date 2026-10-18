import { useParams } from "react-router-dom";
import { ErrorState } from "../../components/error-state";
import { Loading } from "../../components/loading";
import { useLetter } from "../../hooks/use-letter";
import { ReportAppendix } from "./report-appendix";
import { ReportHeader } from "./report-header";
import { ReportMoneyFlow } from "./report-money-flow";
import { ReportSummary } from "./report-summary";
import { ReportWhyTable } from "./report-why-table";

export function LetterReport() {
  const { slug = "" } = useParams();
  const letter = useLetter(slug);
  if (letter.isPending) return <Loading />;
  if (letter.isError) return <ErrorState />;
  const { report } = letter.data;
  if (report === null)
    return <p className="text-muted-foreground">המכתב טרם נותח</p>;
  return (
    <div className="space-y-8">
      <ReportHeader header={report.header} />
      <ReportSummary summary={report.summary} />
      <ReportMoneyFlow flow={report.money_flow} />
      <ReportWhyTable why={report.why} />
      <ReportAppendix appendix={report.appendix} />
    </div>
  );
}
