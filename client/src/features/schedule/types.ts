export type Day = { enabled: boolean; time: string };
export type Range = { from: string; to: string; days: Record<string, Day> };
export type ScheduleData = {
  schedule: Range[];
  always_send: boolean;
  projected_monthly_emails: Record<string, number>;
  monthly_limit: number;
};
