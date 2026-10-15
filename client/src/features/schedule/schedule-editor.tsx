import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Trash2 } from "lucide-react";
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
import { AddRangeButton } from "./add-range-button";
import type { Day, Range } from "./types";
import { useSchedule } from "../../hooks/use-schedule";
import {
  useScheduleDraft,
  useScheduleDraftApi,
} from "../../contexts/schedule-draft";

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
export function ScheduleEditor() {
  const queryClient = useQueryClient();
  const schedule = useSchedule();
  const ranges = useScheduleDraft();
  const setRanges = useScheduleDraftApi();
  const [error, setError] = useState("");
  const save = useMutation({
    mutationFn: () =>
      write<{ schedule: Range[] }>("/api/v1/schedule", "POST", {
        schedule: ranges,
      }),
    onSuccess: () => {
      toast.success("מועדי השליחה נשמרו");
      setError("");
      queryClient.invalidateQueries({ queryKey: ["schedule"] });
    },
    onError: () =>
      setError(
        "לא ניתן לשמור. יש לוודא שטווחי התאריכים אינם חופפים ושהתאריכים תקינים.",
      ),
  });
  function patchRange(index: number, change: Partial<Range>) {
    setRanges((old) =>
      old.map((range, current) =>
        current === index ? { ...range, ...change } : range,
      ),
    );
  }
  function patchDay(index: number, key: string, change: Partial<Day>) {
    setRanges((old) =>
      old.map((range, current) => {
        if (current !== index) return range;
        const existing = range.days[key] ?? { enabled: false, time: "08:00" };
        return {
          ...range,
          days: { ...range.days, [key]: { ...existing, ...change } },
        };
      }),
    );
  }
  function setTime(index: number, time: string) {
    setRanges((old) =>
      old.map((range, current) =>
        current === index
          ? {
              ...range,
              days: Object.fromEntries(
                weekdays.map(([key]) => [
                  key,
                  { enabled: range.days[key]?.enabled ?? false, time },
                ]),
              ),
            }
          : range,
      ),
    );
  }
  if (schedule.isPending) return <Loading />;
  if (schedule.isError || !schedule.data) return <ErrorState />;
  return (
    <div className="max-w-2xl space-y-4">
      {ranges.length === 0 ? (
        <div className="rounded-lg border bg-card p-5 text-muted-foreground">
          לא הוגדרו טווחי שליחה. הוסיפו טווח כדי להתחיל.
        </div>
      ) : (
        ranges.map((range, index) => {
          const time =
            Object.values(range.days).find((day) => day.enabled)?.time ??
            "08:00";
          return (
            <section
              key={`${range.from}-${index}`}
              className="rounded-lg border bg-card p-6"
            >
              <div className="flex items-center justify-between gap-3">
                <h2 className="text-lg font-semibold">טווח {index + 1}</h2>
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label="מחיקת טווח"
                  title="מחיקת טווח"
                  onClick={() =>
                    setRanges((old) => old.filter((_, i) => i !== index))
                  }
                >
                  <Trash2 size={16} className="text-destructive" />
                </Button>
              </div>
              <div className="mt-3 grid gap-3 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor={`from-${index}`}>מתאריך</Label>
                  <DatePicker
                    id={`from-${index}`}
                    value={range.from}
                    onChange={(from) => patchRange(index, { from })}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor={`to-${index}`}>עד תאריך</Label>
                  <DatePicker
                    id={`to-${index}`}
                    value={range.to}
                    onChange={(to) => patchRange(index, { to })}
                  />
                </div>
              </div>
              <fieldset className="mt-6">
                <legend className="text-sm font-medium">ימי שליחה</legend>
                <div className="mt-2 flex flex-wrap gap-x-6">
                  {weekdays.map(([key, label]) => (
                    <div
                      key={key}
                      className="flex h-12 items-center gap-2 px-1 lg:h-10"
                    >
                      <Checkbox
                        id={`${index}-${key}`}
                        checked={range.days[key]?.enabled ?? false}
                        onCheckedChange={(checked) =>
                          patchDay(index, key, {
                            enabled: checked === true,
                            time,
                          })
                        }
                      />
                      <Label htmlFor={`${index}-${key}`}>{label}</Label>
                    </div>
                  ))}
                </div>
              </fieldset>
              <div className="mt-6 grid gap-3 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor={`time-${index}`}>שעת שליחה</Label>
                  <Select
                    value={time}
                    onValueChange={(value) => setTime(index, value)}
                  >
                    <SelectTrigger id={`time-${index}`}>
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
                </div>
              </div>
            </section>
          );
        })
      )}
      <AddRangeButton />
      {error ? <p className="text-sm text-destructive">{error}</p> : null}
      <div className="pt-4">
        <Button disabled={save.isPending} onClick={() => save.mutate()}>
          {save.isPending ? "שומר…" : "שמירה"}
        </Button>
      </div>
    </div>
  );
}
