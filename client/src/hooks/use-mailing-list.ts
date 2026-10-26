import { useQuery } from "@tanstack/react-query";
import { get } from "../services/api";

export type Subscriber = { email: string; name: string };
export type Mailing = { subscribers: Subscriber[]; count: number; cap: number };

export function useMailingList() {
  return useQuery({
    queryKey: ["mailing"],
    queryFn: () => get<Mailing>("/api/v1/mailing_list"),
  });
}
