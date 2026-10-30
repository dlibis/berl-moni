import { Checkbox } from "../../components/ui/checkbox";
import { Label } from "../../components/ui/label";
import { DatePicker } from "../../components/date-picker";
import type { Day, Range } from "./types";
import { FAR, hasUntilDate, today } from "./types";
import {
  ScheduleSwitch,
  ScheduleTimeSelect,
  WeekdayPicker,
  weekdays,
} from "./schedule-controls";

function SendFields({
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
    <div className="mt-6 grid gap-6 lg:grid-cols-2">
      <WeekdayPicker
        label="ימי שליחה"
        days={weekdays
          .filter(([key]) => range.days[key]?.enabled)
          .map(([key]) => key)}
        onToggle={(key) =>
          patchDay(key, { enabled: !range.days[key]?.enabled, time })
        }
      />
      <fieldset className="min-w-0 lg:border-s lg:ps-6">
        <legend className="mb-3 text-sm font-medium">תזמון</legend>
        <Label className="mb-2 block" htmlFor={`${idPrefix}-time`}>
          שעה קבועה
        </Label>
        <ScheduleTimeSelect
          id={`${idPrefix}-time`}
          label={timeAriaLabel}
          value={time}
          onChange={setTime}
        />
        <div className="mt-4 flex flex-wrap items-center gap-2">
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
      </fieldset>
    </div>
  );
}

export function SendScheduleSection({
  range,
  setRange,
  enabled,
  onEnabledChange,
  error,
}: {
  range: Range;
  setRange: (update: (old: Range) => Range) => void;
  enabled: boolean;
  onEnabledChange: (enabled: boolean) => void;
  error: string;
}) {
  return (
    <section className="rounded-lg border bg-card p-6">
      <h2 className="mb-3 text-sm font-medium">תזמון שליחת מייל בתפוצה</h2>
      <ScheduleSwitch
        id="send-enabled"
        checked={enabled}
        onChange={onEnabledChange}
      />
      {enabled ? (
        <SendFields
          range={range}
          setRange={setRange}
          idPrefix="send"
          timeAriaLabel="שעת שליחה"
        />
      ) : null}
      {error ? (
        <p role="alert" className="mt-3 text-sm text-destructive">
          {error}
        </p>
      ) : null}
    </section>
  );
}
