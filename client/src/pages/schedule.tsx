import { PageHeader } from "../components/page-header";
import { AddRangeButton } from "../features/schedule/add-range-button";
import { MonthlyProjection } from "../features/schedule/monthly-projection";
import { ScheduleDraftProvider } from "../contexts/schedule-draft";
import { ScheduleEditor } from "../features/schedule/schedule-editor";

export function Schedule() {
  return (
    <ScheduleDraftProvider>
      <PageHeader title="לוח שליחה">
        <AddRangeButton />
      </PageHeader>
      <div className="grid gap-4 xl:grid-cols-[minmax(0,560px)_1fr]">
        <ScheduleEditor />
        <MonthlyProjection />
      </div>
    </ScheduleDraftProvider>
  );
}
