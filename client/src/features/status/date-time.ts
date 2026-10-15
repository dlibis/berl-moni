export const dateTime = (value?: string) =>
  value
    ? new Intl.DateTimeFormat("he-IL", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value))
    : "—";
