import { useParams } from "react-router-dom";
import { PageHeader } from "../components/page-header";
import { ReportAppendix } from "../features/letter-report/report-appendix";
import { ReportMoneyFlow } from "../features/letter-report/report-money-flow";
import { ReportStatus } from "../features/letter-report/report-status";
import { ReportSummary } from "../features/letter-report/report-summary";
import { ReportWhyTable } from "../features/letter-report/report-why-table";
import { LetterActions } from "../features/letters/letter-actions";
import { useLetter } from "../hooks/use-letter";

// The summary PDF's sections, as the app's own cards.
export function Letter() {
  const { slug = "" } = useParams();
  const letter = useLetter(slug).data;
  return (
    <>
      <PageHeader title={letter?.request_numbers.join(", ") || "מכתב"}>
        {letter ? <LetterActions letter={letter} /> : null}
      </PageHeader>
      <ReportStatus />
      <div className="space-y-6">
        <ReportSummary />
        <ReportMoneyFlow />
        <ReportWhyTable />
        <ReportAppendix />
      </div>
    </>
  );
}
