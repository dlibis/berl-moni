import { PageHeader } from "../components/page-header";
import { MonthlyProjection } from "../features/schedule/monthly-projection";
import { ScheduleDraftProvider } from "../contexts/schedule-draft";
import { ScheduleEditor } from "../features/schedule/schedule-editor";

export function Schedule() {
  return (
    <ScheduleDraftProvider>
      <PageHeader title="מועדי שליחה" />
      <div className="grid gap-4 xl:grid-cols-[minmax(0,42rem)_20rem]">
        <ScheduleEditor />
        <MonthlyProjection />
      </div>
    </ScheduleDraftProvider>
  );
}
