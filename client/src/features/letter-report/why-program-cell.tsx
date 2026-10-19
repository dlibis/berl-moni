import type { ReportWhyRow } from "../letters/types";

/** The name (blue for a master program), the code small under it. */
export function WhyProgramCell({ row }: { row: ReportWhyRow }) {
  return (
    <td className="w-[30%] px-3 py-2 align-top">
      <div className={row.master ? "text-[hsl(var(--report-master))]" : undefined}>{row.name}</div>
      <div className="text-[11px] text-muted-foreground">
        תוכנית <span className="font-mono">{row.code}</span>
      </div>
    </td>
  );
}
