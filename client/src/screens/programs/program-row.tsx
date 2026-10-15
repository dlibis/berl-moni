import type { Program } from "../../lib/programs";
import { ProgramActions } from "./program-actions";

export function ProgramRow({
  program,
  onRemove,
  pending,
}: {
  program: Program;
  onRemove: () => void;
  pending: boolean;
}) {
  return (
    <tr className="border-t">
      <td className="p-3 font-mono">{program.code}</td>
      <td className="max-w-0 truncate p-3" title={program.name}>
        {program.name}
      </td>
      <td className="p-2">
        <ProgramActions program={program} onRemove={onRemove} pending={pending} />
      </td>
    </tr>
  );
}
