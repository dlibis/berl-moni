import { useParams } from "react-router-dom";
import { useLetter } from "./use-letter";

/** The open letter's report (from the route's slug); undefined while loading or before analysis. */
export function useLetterReport() {
  const { slug = "" } = useParams();
  return useLetter(slug).data?.report ?? undefined;
}
