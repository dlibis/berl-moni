import { useQuery } from "@tanstack/react-query";
import { get } from "../../lib/api";

export type Mailing = { emails: string[]; count: number; cap: number };

export function useMailingList() {
  return useQuery({ queryKey: ["mailing"], queryFn: () => get<Mailing>("/api/v1/mailing_list") });
}
