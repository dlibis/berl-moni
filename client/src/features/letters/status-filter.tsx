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
  ["failed", "תקלה"],
  ["requires_review", "דורש עיון"],
  ["needs_analysis", "דורשים ניתוח"],
  ["relevant", "רלוונטי"],
  ["irrelevant", "לא רלוונטי"],
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
        <SelectItem value="all">כל הפניות</SelectItem>
        {OPTIONS.map(([key, text]) => (
          <SelectItem key={key} value={key}>
            {text}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
