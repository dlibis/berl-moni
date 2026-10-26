import { PageHeader } from "../components/page-header";
import { MonthlyProjection } from "../features/schedule/monthly-projection";
import { ScheduleEditor } from "../features/schedule/schedule-editor";

export function Schedule() {
  return (
    <>
      <PageHeader title="לוח זמנים" />
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_20rem]">
        <ScheduleEditor />
        <MonthlyProjection />
      </div>
    </>
  );
}
