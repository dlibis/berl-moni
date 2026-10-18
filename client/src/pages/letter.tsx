import { useParams } from "react-router-dom";
import { PageHeader } from "../components/page-header";
import { LetterActions } from "../features/letters/letter-actions";
import { LetterReport } from "../features/letter-report/letter-report";
import { useLetter } from "../hooks/use-letter";

export function Letter() {
  const { slug = "" } = useParams();
  const letter = useLetter(slug).data;
  return (
    <>
      <PageHeader title={letter?.request_numbers.join(", ") || "מכתב"}>
        {letter ? <LetterActions letter={letter} /> : null}
      </PageHeader>
      <LetterReport />
    </>
  );
}
