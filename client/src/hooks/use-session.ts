import { useQuery } from "@tanstack/react-query";
import { get } from "../services/api";

type Session = { user: { email: string } } | null;

export function useSession() {
  return useQuery({
    queryKey: ["session"],
    queryFn: () => get<Session>("/api/auth/get-session"),
    staleTime: Infinity,
  });
}
