import { Plus } from "lucide-react";
import { Button } from "../../components/ui/button";
import type { Range } from "./types";
import { useSchedule } from "../../hooks/use-schedule";
import { useScheduleDraftApi } from "../../contexts/schedule-draft";

const blank = (): Range => ({
  from: new Date().toISOString().slice(0, 10),
  to: new Date().toISOString().slice(0, 10),
  days: {},
});
export function AddRangeButton() {
  const schedule = useSchedule();
  const setRanges = useScheduleDraftApi();
  // Hidden until loaded, as before: a range added earlier would be overwritten when the data arrives.
  if (!schedule.data) return null;
  return (
    <Button onClick={() => setRanges((old) => [...old, blank()])}>
      <Plus size={16} />
      הוספת טווח תאריכים
    </Button>
  );
}
