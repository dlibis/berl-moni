import { useState } from "react";
import { PageHeader } from "../components/page-header";
import { Input } from "../components/ui/input";
import { LettersTable } from "../features/letters/letters-table";
import { ExportButton } from "../features/letters/export-button";
import { RefreshButton } from "../features/letters/refresh-button";
import { StatusFilter } from "../features/letters/status-filter";
import type { LetterStatusFilter } from "../features/letters/types";
import { FailedSendRunCard } from "../features/status/failed-send-run-card";
import { LastScanLine } from "../features/status/last-scan-card";

export function Home() {
  const [status, setStatus] = useState<LetterStatusFilter>();
  const [search, setSearch] = useState("");
  return (
    <>
      <PageHeader title="ראשי" detail={<LastScanLine />}>
        <div className="flex flex-wrap items-center gap-2 mb-2">
          <Input
            type="search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="חיפוש לפי משרד או מספר בקשה"
            aria-label="חיפוש לפי משרד או מספר בקשה"
            className="w-full sm:w-72"
          />
          <StatusFilter value={status} onChange={setStatus} />
          <ExportButton />
          <RefreshButton />
        </div>
      </PageHeader>
      <FailedSendRunCard />
      <LettersTable
        key={JSON.stringify([status, search.trim()])}
        status={status}
        search={search.trim()}
      />
    </>
  );
}
