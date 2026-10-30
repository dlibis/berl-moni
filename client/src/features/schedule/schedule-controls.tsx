import { Button } from "../../components/ui/button";
import { Label } from "../../components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../../components/ui/select";

export const weekdays: [string, string][] = [
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

export function ScheduleSwitch({
  id,
  checked,
  onChange,
}: {
  id: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}) {
  return (
    <div className="flex items-center gap-2">
      <button
        id={id}
        type="button"
        role="switch"
        dir="ltr"
        aria-checked={checked}
        aria-labelledby={`${id}-label`}
        onClick={() => onChange(!checked)}
        className={`inline-flex h-6 w-11 shrink-0 items-center rounded-full p-0.5 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ${checked ? "bg-primary" : "bg-muted-foreground/40"}`}
      >
        <span
          className={`pointer-events-none block h-5 w-5 rounded-full bg-background shadow-sm transition-transform motion-reduce:transition-none ${checked ? "translate-x-5" : "translate-x-0"}`}
        />
      </button>
      <Label id={`${id}-label`} htmlFor={id}>
        פעיל
      </Label>
    </div>
  );
}

export function WeekdayPicker({
  label,
  days,
  onToggle,
  disabled = false,
}: {
  label: string;
  days: string[];
  onToggle: (day: string) => void;
  disabled?: boolean;
}) {
  return (
    <fieldset className="min-w-0">
      <legend className="mb-3 text-sm font-medium">{label}</legend>
      <div className="grid grid-cols-7 gap-1.5">
        {weekdays.map(([key, name]) => (
          <Button
            key={key}
            type="button"
            variant={days.includes(key) ? "default" : "outline"}
            className="h-11 min-w-0 px-0"
            aria-label={`יום ${name}`}
            aria-pressed={days.includes(key)}
            disabled={disabled}
            onClick={() => onToggle(key)}
          >
            {name}
          </Button>
        ))}
      </div>
    </fieldset>
  );
}

export function ScheduleTimeSelect({
  id,
  label,
  value,
  onChange,
}: {
  id?: string;
  label: string;
  value: string;
  onChange: (time: string) => void;
}) {
  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger id={id} className="w-full" aria-label={label}>
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
  );
}
