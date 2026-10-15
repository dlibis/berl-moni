import { createContext, useContext, useEffect, useState } from "react";
import type { Range } from "./types";
import { useSchedule } from "./use-schedule";

// The header's add button and the editor edit the same unsaved ranges, so the draft lives in a context
// shared by those two blocks instead of in the page.
const ScheduleDraftContext = createContext<{
  ranges: Range[];
  setRanges: React.Dispatch<React.SetStateAction<Range[]>>;
}>({ ranges: [], setRanges: () => {} });
export function ScheduleDraftProvider({ children }: { children: React.ReactNode }) {
  const schedule = useSchedule();
  const [ranges, setRanges] = useState<Range[]>([]);
  useEffect(() => {
    if (schedule.data) setRanges(schedule.data.schedule);
  }, [schedule.data]);
  return (
    <ScheduleDraftContext.Provider value={{ ranges, setRanges }}>{children}</ScheduleDraftContext.Provider>
  );
}
export const useScheduleDraft = () => useContext(ScheduleDraftContext);
