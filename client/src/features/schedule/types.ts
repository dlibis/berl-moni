export type Day = { enabled: boolean; time: string };
export type Range = {
  from: string;
  to: string;
  days: Record<string, Day>;
  count?: number;
};
export type ScheduleData = {
  schedule: Range[];
  fetch_every_hours?: 1 | 6 | 24 | null;
  always_send: boolean;
  projected_monthly_emails: Record<string, number>;
  monthly_limit: number;
};
export const FAR = "2999-12-31";
export const today = () => new Date().toISOString().slice(0, 10);

export function hasUntilDate(range: Range): boolean {
  return !range.count && range.to < "2999-01-01";
}

export function initialRange(data: ScheduleData): Range {
  const first = data.schedule[0];
  if (first) return first;
  if (data.always_send)
    return {
      from: today(),
      to: FAR,
      days: { sun: { enabled: true, time: "09:00" } },
    };
  return { from: today(), to: FAR, days: {} };
}
