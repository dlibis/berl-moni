import { useState } from "react";
import { PageHeader } from "../components/page-header";
import { LettersTable } from "../features/letters/letters-table";
import { RefreshButton } from "../features/letters/refresh-button";
import { StatusFilter } from "../features/letters/status-filter";
import type { LetterStatusFilter } from "../features/letters/types";
import { FailedSendRunCard } from "../features/status/failed-send-run-card";
import { LastScanLine } from "../features/status/last-scan-card";

export function Home() {
  const [status, setStatus] = useState<LetterStatusFilter>();
  return (
    <>
      <PageHeader title="ראשי" detail={<LastScanLine />}>
        <div className="flex flex-wrap items-center gap-2">
          <StatusFilter value={status} onChange={setStatus} />
          <RefreshButton />
        </div>
      </PageHeader>
      <FailedSendRunCard />
      <LettersTable key={status ?? "all"} status={status} />
    </>
  );
}
