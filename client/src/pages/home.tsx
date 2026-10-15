import { PageHeader } from "../components/page-header";
import { FailedLettersList } from "../features/status/failed-letters-list";
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
      <FailedLettersList />
    </>
  );
}
