import { createContext, useContext, useEffect, useState } from "react";
import type { Range } from "../features/schedule/types";
import { useSchedule } from "../hooks/use-schedule";

// The header's add button and the editor edit the same unsaved ranges, so the draft lives in a context
// shared by those two blocks instead of in the page. Data and setter are split into two providers so a
// block that only writes (the add button) doesn't re-render on every edit (Advanced React, ch. 8, p. 154).
type SetRanges = React.Dispatch<React.SetStateAction<Range[]>>;
const ScheduleDraftContext = createContext<Range[]>([]);
const ScheduleDraftApiContext = createContext<SetRanges>(() => {});
export function ScheduleDraftProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const schedule = useSchedule();
  const [ranges, setRanges] = useState<Range[]>([]);
  useEffect(() => {
    if (schedule.data) setRanges(schedule.data.schedule);
  }, [schedule.data]);
  // Both values are referentially stable: `ranges` changes only on edit, `setRanges` never does.
  return (
    <ScheduleDraftContext.Provider value={ranges}>
      <ScheduleDraftApiContext.Provider value={setRanges}>
        {children}
      </ScheduleDraftApiContext.Provider>
    </ScheduleDraftContext.Provider>
  );
}
export const useScheduleDraft = () => useContext(ScheduleDraftContext);
export const useScheduleDraftApi = () => useContext(ScheduleDraftApiContext);
