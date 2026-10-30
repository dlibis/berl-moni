import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { write } from "../../services/api";
import { Button } from "../../components/ui/button";
import { ErrorState } from "../../components/error-state";
import { Loading } from "../../components/loading";
import { useSchedule } from "../../hooks/use-schedule";
import type { Range, FetchSchedule, ScheduleData } from "./types";
import { FAR, hasUntilDate, initialRange } from "./types";
import { weekdays } from "./schedule-controls";
import { FetchScheduleSection } from "./fetch-schedule-section";
import { SendScheduleSection } from "./send-schedule-section";

function toPayload(range: Range): Range {
  const { from, days, to } = range;
  if (hasUntilDate(range)) return { from, to, days };
  return { from, to: FAR, days };
}

export function ScheduleEditor() {
  const schedule = useSchedule();
  if (schedule.isError) return <ErrorState />;
  if (schedule.isPending) return <Loading />;
  return <ScheduleForm initial={schedule.data} />;
}

function ScheduleForm({ initial }: { initial: ScheduleData }) {
  const queryClient = useQueryClient();
  const [range, setRange] = useState(() => initialRange(initial));
  const [sendEnabled, setSendEnabled] = useState(() =>
    Object.values(initialRange(initial).days).some((day) => day.enabled),
  );
  const initialFetch =
    initial.fetch_schedule === undefined
      ? initial.fetch_every_hours
        ? {
            days: weekdays.map(([key]) => key),
            mode: "interval" as const,
            interval_hours: initial.fetch_every_hours,
          }
        : null
      : initial.fetch_schedule;
  const [fetchEnabled, setFetchEnabled] = useState(initialFetch != null);
  const [fetchConfig, setFetchConfig] = useState<FetchSchedule>(
    () =>
      initialFetch ?? {
        days: weekdays.map(([key]) => key),
        mode: "interval",
        interval_hours: 6,
      },
  );
  const [error, setError] = useState("");
  const save = useMutation({
    mutationFn: async () => {
      await write("/api/v1/schedule", "POST", {
        schedule: sendEnabled ? [toPayload(range)] : [],
        fetch_schedule: fetchEnabled ? fetchConfig : null,
        always_send: false,
      });
    },
    onSuccess: () => {
      toast.success("לוח הזמנים נשמר");
      setError("");
      queryClient.invalidateQueries({ queryKey: ["schedule"] });
    },
    onError: () =>
      setError("לא ניתן לשמור את לוח הזמנים. בדקו את החיבור ונסו שוב."),
  });
  const fetchError = !fetchEnabled
    ? ""
    : !fetchConfig.days.length
      ? "יש לבחור לפחות יום אחד לרענון."
      : fetchConfig.mode === "interval" &&
          (!Number.isInteger(fetchConfig.interval_hours) ||
            fetchConfig.interval_hours < 1 ||
            fetchConfig.interval_hours > 24)
        ? "יש להזין מספר שעות שלם בין 1 ל־24."
        : "";
  const sendError =
    sendEnabled && !Object.values(range.days).some((day) => day.enabled)
      ? "יש לבחור לפחות יום אחד לשליחה."
      : "";
  return (
    <div className="space-y-4">
      <FetchScheduleSection
        fetchConfig={fetchConfig}
        setFetchConfig={setFetchConfig}
        fetchEnabled={fetchEnabled}
        setFetchEnabled={setFetchEnabled}
        fetchError={fetchError}
        pending={save.isPending}
      />
      <SendScheduleSection
        range={range}
        setRange={setRange}
        enabled={sendEnabled}
        onEnabledChange={setSendEnabled}
        error={sendError}
      />
      {error ? <p className="text-sm text-destructive">{error}</p> : null}
      <div className="pt-4">
        <Button
          disabled={save.isPending || !!fetchError || !!sendError}
          onClick={() => save.mutate()}
        >
          {save.isPending ? "שומר…" : "שמירה"}
        </Button>
      </div>
    </div>
  );
}
