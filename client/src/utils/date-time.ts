export const dateTime = (value?: string) =>
  value
    ? new Intl.DateTimeFormat("he-IL", {
        dateStyle: "medium",
        timeStyle: "short",
      }).format(new Date(value))
    : "—";
// Date-only API values ("2026-10-01") parse as UTC midnight; format in UTC so the day never shifts.
export const day = (value: string) =>
  new Intl.DateTimeFormat("he-IL", {
    dateStyle: "medium",
    timeZone: "UTC",
  }).format(new Date(value));
export const month = (value: string) =>
  new Intl.DateTimeFormat("he-IL", {
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(value));
