import type { Program } from "./types";
import { ProgramActions } from "./program-actions";

export function ProgramRow({ program }: { program: Program }) {
  return (
    <tr className="border-t">
      <td className="p-3 font-mono">{program.code}</td>
      <td className="max-w-0 truncate p-3" title={program.name}>
        {program.name}
      </td>
      <td className="p-2">
        <ProgramActions program={program} />
      </td>
    </tr>
  );
}
