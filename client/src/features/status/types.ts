export type Scan = {
  ran_at: string;
  status: string;
  reason?: string;
  letters_in_feed?: number;
  new_letters?: number;
  relevant?: number;
  failed?: number;
  emails_sent?: number;
};
export type FailedRun = {
  id: number;
  day: string;
  failed_at: string;
  error: string;
  sent_messages: number;
  unsent_messages: number;
  keys_expired: boolean;
};
export type Status = {
  latest_scan: Scan | null;
  next_scheduled_send_day: string | null;
  failed_send_run: FailedRun | null;
};
