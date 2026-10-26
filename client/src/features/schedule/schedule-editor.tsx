import { useEffect, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { write } from "../../services/api";
import { Button } from "../../components/ui/button";
import { DatePicker } from "../../components/date-picker";
import { Checkbox } from "../../components/ui/checkbox";
import { Label } from "../../components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../../components/ui/select";
import { ErrorState } from "../../components/error-state";
import { Loading } from "../../components/loading";
import type { Day, Range, ScheduleData } from "./types";
import { FAR, hasUntilDate, initialRange, today } from "./types";
import { useSchedule } from "../../hooks/use-schedule";

const FETCH_CADENCE: { value: string; label: string }[] = [
  { value: "off", label: "כבוי" },
  { value: "1", label: "כל שעה" },
  { value: "6", label: "כל 6 שעות" },
  { value: "24", label: "פעם ביום" },
];

const weekdays: [string, string][] = [
  ["sun", "א׳"],
  ["mon", "ב׳"],
  ["tue", "ג׳"],
  ["wed", "ד׳"],
  ["thu", "ה׳"],
  ["fri", "ו׳"],
  ["sat", "ש׳"],
];
const hours = Array.from(
  { length: 24 },
  (_, hour) => `${String(hour).padStart(2, "0")}:00`,
);

function toPayload(range: Range): Range {
  const { from, days, to } = range;
  if (hasUntilDate(range)) return { from, to, days };
  return { from, to: FAR, days };
}

function RangeFields({
  range,
  setRange,
  idPrefix,
  timeAriaLabel,
}: {
  range: Range;
  setRange: (update: (old: Range) => Range) => void;
  idPrefix: string;
  timeAriaLabel: string;
}) {
  function patch(change: Partial<Range>) {
    setRange((old) => ({ ...old, ...change }));
  }
  function patchDay(key: string, change: Partial<Day>) {
    setRange((old) => {
      const existing = old.days[key] ?? { enabled: false, time: "08:00" };
      return {
        ...old,
        days: { ...old.days, [key]: { ...existing, ...change } },
      };
    });
  }
  function setTime(time: string) {
    setRange((old) => ({
      ...old,
      days: Object.fromEntries(
        weekdays.map(([key]) => [
          key,
          { enabled: old.days[key]?.enabled ?? false, time },
        ]),
      ),
    }));
  }
  function setUntil(on: boolean) {
    setRange((old) => {
      const { count: _c, ...rest } = old;
      if (!on) return { ...rest, to: FAR };
      return { ...rest, to: old.to < FAR ? old.to : today() };
    });
  }
  const time =
    Object.values(range.days).find((day) => day.enabled)?.time ?? "08:00";
  const until = hasUntilDate(range);
  const untilId = `${idPrefix}-until`;
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
      <div className="flex items-center gap-x-1.5">
        {weekdays.map(([key, label]) => {
          const id = `${idPrefix}-${key}`;
          return (
            <div key={key} className="flex items-center gap-1.5">
              <Checkbox
                id={id}
                checked={range.days[key]?.enabled ?? false}
                onCheckedChange={(checked) =>
                  patchDay(key, { enabled: checked === true, time })
                }
              />
              <Label htmlFor={id}>{label}</Label>
            </div>
          );
        })}
      </div>
      <Select value={time} onValueChange={setTime}>
        <SelectTrigger className="w-24 shrink-0" aria-label={timeAriaLabel}>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {hours.map((hour) => (
            <SelectItem key={hour} value={hour}>
              {hour}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <div className="flex shrink-0 items-center gap-2">
        <Checkbox
          id={untilId}
          checked={until}
          onCheckedChange={(checked) => setUntil(checked === true)}
        />
        <Label htmlFor={untilId}>עם תאריך סיום?</Label>
        {until ? (
          <div className="w-36">
            <DatePicker
              id={`${idPrefix}-until-date`}
              value={range.to}
              onChange={(to) => patch({ to })}
            />
          </div>
        ) : null}
      </div>
    </div>
  );
}

export function ScheduleEditor() {
  const queryClient = useQueryClient();
  const schedule = useSchedule();
  const [range, setRange] = useState<Range | null>(null);
  const [fetchHours, setFetchHours] = useState<ScheduleData["fetch_every_hours"]>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    if (schedule.data) {
      setRange(initialRange(schedule.data));
      setFetchHours(schedule.data.fetch_every_hours ?? null);
    }
  }, [schedule.data]);
  const save = useMutation({
    mutationFn: async () => {
      if (!range) return;
      await write("/api/v1/schedule", "POST", {
        schedule: [toPayload(range)],
        fetch_every_hours: fetchHours,
        always_send: false,
      });
    },
    onSuccess: () => {
      toast.success("לוח הזמנים נשמר");
      setError("");
      queryClient.invalidateQueries({ queryKey: ["schedule"] });
    },
    onError: () =>
      setError("לא ניתן לשמור. יש לבחור ימי שליחה וסיום תקינים."),
  });
  if (schedule.isPending || !range) return <Loading />;
  if (schedule.isError || !schedule.data) return <ErrorState />;
  return (
    <div className="space-y-4">
      <section className="rounded-lg border bg-card p-6">
        <h2 className="mb-3 text-sm font-medium">רענון מהכנסת</h2>
        <Select
          value={fetchHours == null ? "off" : String(fetchHours)}
          onValueChange={(value) =>
            setFetchHours(value === "off" ? null : (Number(value) as 1 | 6 | 24))
          }
        >
          <SelectTrigger className="w-40" aria-label="תדירות רענון">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {FETCH_CADENCE.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </section>
      <section className="rounded-lg border bg-card p-6">
        <h2 className="mb-3 text-sm font-medium">שליחה</h2>
        <RangeFields
          range={range}
          setRange={(update) => setRange((old) => (old ? update(old) : old))}
          idPrefix="send"
          timeAriaLabel="שעת שליחה"
        />
      </section>
      {error ? <p className="text-sm text-destructive">{error}</p> : null}
      <div className="pt-4">
        <Button disabled={save.isPending} onClick={() => save.mutate()}>
          {save.isPending ? "שומר…" : "שמירה"}
        </Button>
      </div>
    </div>
  );
}
