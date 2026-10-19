/** The small, grey-headed, centred grid both appendix tables use. `spans` are
 * (column, top row, bottom row) in `rows`' own indexes; the first column is drawn rightmost. */
export function ReportGridTable({
  rows,
  spans = [],
}: {
  rows: (string | number | null)[][];
  spans?: [number, number, number][];
}) {
  const rowSpan = new Map(spans.map(([col, top, bottom]) => [`${top}:${col}`, bottom - top + 1]));
  const covered = new Set(
    spans.flatMap(([col, top, bottom]) =>
      Array.from({ length: bottom - top }, (_, i) => `${top + 1 + i}:${col}`),
    ),
  );
  // plaintext: each cell takes its own direction, so '-18,000' keeps its minus sign in front
  const cell = "border px-1.5 py-1 tabular-nums text-center align-middle [unicode-bidi:plaintext]";
  const [header, ...body] = rows;
  return (
    <div className="overflow-x-auto">
      <table className="mx-auto border-collapse text-sm">
        <thead>
          <tr className="bg-muted text-muted-foreground">
            {header.map((text, i) => (
              <th key={i} className={`${cell} whitespace-pre-line font-medium`}>
                {text}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {body.map((row, r) => (
            <tr key={r}>
              {row.map((text, c) =>
                covered.has(`${r + 1}:${c}`) ? null : (
                  <td key={c} className={c === 0 ? `${cell} font-mono` : cell} rowSpan={rowSpan.get(`${r + 1}:${c}`)}>
                    {text ?? ""}
                  </td>
                ),
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
