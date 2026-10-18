import { PageHeader } from "../components/page-header";
import { LettersTable } from "../features/letters/letters-table";
import { RefreshButton } from "../features/letters/refresh-button";
import { FailedSendRunCard } from "../features/status/failed-send-run-card";
import { LastScanCard } from "../features/status/last-scan-card";

export function Home() {
  return (
    <>
      <PageHeader title="ראשי" />
      <div className="grid gap-4 xl:grid-cols-2">
        <LastScanCard />
        <FailedSendRunCard />
      </div>
      <div className="mt-8 mb-4 flex items-center justify-between gap-2">
        <h2 className="text-xl font-semibold">מכתבים</h2>
        <RefreshButton />
      </div>
      <LettersTable />
    </>
  );
}
