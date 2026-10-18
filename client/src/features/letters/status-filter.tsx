import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../../components/ui/select";
import type { LetterStatusFilter } from "./types";

const OPTIONS: [LetterStatusFilter, string][] = [
  ["not_analyzed", "לא נותחו"],
  ["queued", "בתור"],
  ["relevant", "רלוונטיים"],
  ["irrelevant", "לא רלוונטיים"],
  ["failed", "נכשלו"],
  ["sent", "נשלחו"],
  ["needs_analysis", "דורשים ניתוח"],
  ["outdated", "גרסה ישנה"],
];

export function StatusFilter({
  value,
  onChange,
}: {
  value?: LetterStatusFilter;
  onChange: (value?: LetterStatusFilter) => void;
}) {
  return (
    <Select
      value={value ?? "all"}
      onValueChange={(v) =>
        onChange(v === "all" ? undefined : (v as LetterStatusFilter))
      }
    >
      <SelectTrigger className="w-48" aria-label="סינון לפי סטטוס">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="all">כל המכתבים</SelectItem>
        {OPTIONS.map(([key, text]) => (
          <SelectItem key={key} value={key}>
            {text}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
