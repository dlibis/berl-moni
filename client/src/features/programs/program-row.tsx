import type { Program } from "./types";
import { ProgramActions } from "./program-actions";
import { TableCell, TableRow } from "../../components/ui/table";

export function ProgramRow({ program }: { program: Program }) {
  return (
    <TableRow>
      <TableCell className="font-mono">{program.code}</TableCell>
      <TableCell className="max-w-0 truncate" title={program.name}>
        {program.name}
      </TableCell>
      <TableCell>
        <ProgramActions program={program} />
      </TableCell>
    </TableRow>
  );
}
