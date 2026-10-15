import { useQuery } from "@tanstack/react-query";
import { get } from "../../lib/api";

export type MailboxData = { from_address: string; reply_to_address: string };

export function useMailbox() {
  return useQuery({ queryKey: ["mailbox"], queryFn: () => get<MailboxData>("/api/v1/notifier") });
}
