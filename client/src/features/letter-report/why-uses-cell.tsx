import type { ReportWhyRow } from "../letters/types";
import { COALITION_TAG } from "./report-format";

/** One bullet per use of the money; a coalition-funded use ends in an orange tag. */
export function WhyUsesCell({ row }: { row: ReportWhyRow }) {
  return (
    <td className="px-3 py-2 align-top">
      {row.uses.map((use, i) => (
        <p key={i}>
          • {use.text}
          {use.coalition ? (
            <>
              {" · "}
              <span className="text-[hsl(var(--report-coalition))]">{COALITION_TAG}</span>
            </>
          ) : null}
        </p>
      ))}
    </td>
  );
}
