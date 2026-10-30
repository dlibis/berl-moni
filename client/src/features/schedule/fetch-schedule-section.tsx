import type { Dispatch, SetStateAction } from "react";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import type { FetchSchedule } from "./types";
import {
  ScheduleSwitch,
  ScheduleTimeSelect,
  WeekdayPicker,
} from "./schedule-controls";

export function FetchScheduleSection({
  fetchConfig,
  setFetchConfig,
  fetchEnabled,
  setFetchEnabled,
  fetchError,
  pending,
}: {
  fetchConfig: FetchSchedule;
  setFetchConfig: Dispatch<SetStateAction<FetchSchedule>>;
  fetchEnabled: boolean;
  setFetchEnabled: (enabled: boolean) => void;
  fetchError: string;
  pending: boolean;
}) {
  return (
    <section className="rounded-lg border bg-card p-6">
      <h2 className="mb-3 text-sm font-medium">רענון מהכנסת</h2>
      <ScheduleSwitch
        id="fetch-enabled"
        checked={fetchEnabled}
        onChange={setFetchEnabled}
      />
      {fetchEnabled ? (
        <div className="mt-6 grid gap-6 lg:grid-cols-2">
          <WeekdayPicker
            label="ימי רענון"
            days={fetchConfig.days}
            disabled={pending}
            onToggle={(key) =>
              setFetchConfig((old) => ({
                ...old,
                days: old.days.includes(key)
                  ? old.days.filter((day) => day !== key)
                  : [...old.days, key],
              }))
            }
          />
          <fieldset className="min-w-0 lg:border-s lg:ps-6">
            <legend className="mb-3 text-sm font-medium">תזמון</legend>
            <div
              className="mb-4 grid grid-cols-2 gap-1 rounded-md border p-1"
              role="group"
              aria-label="סוג תזמון הרענון"
            >
              <Button
                variant={fetchConfig.mode === "specific" ? "default" : "ghost"}
                aria-pressed={fetchConfig.mode === "specific"}
                onClick={() =>
                  setFetchConfig({
                    days: fetchConfig.days,
                    mode: "specific",
                    time: "09:00",
                  })
                }
              >
                שעה קבועה
              </Button>
              <Button
                variant={fetchConfig.mode === "interval" ? "default" : "ghost"}
                aria-pressed={fetchConfig.mode === "interval"}
                onClick={() =>
                  setFetchConfig({
                    days: fetchConfig.days,
                    mode: "interval",
                    interval_hours: 6,
                  })
                }
              >
                מרווח קבוע
              </Button>
            </div>
            {fetchConfig.mode === "specific" ? (
              <ScheduleTimeSelect
                label="שעת רענון"
                value={fetchConfig.time}
                onChange={(time) =>
                  setFetchConfig({ ...fetchConfig, mode: "specific", time })
                }
              />
            ) : (
              <div className="flex items-center gap-3">
                <Label htmlFor="fetch-interval">כל</Label>
                <Input
                  id="fetch-interval"
                  type="number"
                  min={1}
                  max={24}
                  step={1}
                  className="w-24"
                  value={
                    Number.isNaN(fetchConfig.interval_hours)
                      ? ""
                      : fetchConfig.interval_hours
                  }
                  aria-invalid={!!fetchError}
                  aria-describedby={fetchError ? "fetch-error" : undefined}
                  onChange={(event) =>
                    setFetchConfig({
                      ...fetchConfig,
                      mode: "interval",
                      interval_hours: event.target.valueAsNumber,
                    })
                  }
                />
                <span className="text-sm">שעות מהרענון האחרון</span>
              </div>
            )}
          </fieldset>
        </div>
      ) : null}
      {fetchError ? (
        <p
          id="fetch-error"
          role="alert"
          className="mt-3 text-sm text-destructive"
        >
          {fetchError}
        </p>
      ) : null}
    </section>
  );
}
