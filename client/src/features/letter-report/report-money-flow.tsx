import { useElementWidth } from "../../hooks/use-element-width";
import { useLetterReport } from "../../hooks/use-letter-report";
import type { ReportItem } from "../letters/types";
import { COLORS, FONT, money, textWidth, wrap } from "./report-format";

// The layout of bot/adapters/summary_pdf/flow_chart.py: sources (right) -> hubs (middle) ->
// destinations (left), band thickness is the amount. Laid out in real px at the card's width (y up,
// flipped into SVG at draw time) so the text keeps docs/design.md's sizes: 14px labels, 11px codes.
const MIN_WIDTH = 560; // narrower scrolls inside the card rather than squeezing the labels
const LABEL = { size: 14, line: 18 };
const CODE = { size: 11, line: 14 };
const NODE_W = 8;
const GAP = 8;
const TOP = 24; // room for the first hub's label
const BOTTOM = 24; // and the last one's
const BAND_OPACITY = 0.28;

type Line = { text: string; code?: string; size: number; height: number; color: string };
type Placed = { item: ReportItem; top: number; bottom: number; mid: number };
type Label = { x: number; y: number; anchor: "start" | "end"; line: Line };

function labelLines(item: ReportItem, master: Set<string>, labelW: number): Line[] {
  const color = master.has(item.code) ? COLORS.master : COLORS.ink;
  const lines: Line[] = wrap(item.name, labelW, LABEL.size).map((text) => ({
    text, size: LABEL.size, height: LABEL.line, color,
  }));
  lines.push({ text: money(item.amount), size: LABEL.size, height: LABEL.line, color: COLORS.ink });
  if (item.code)
    lines.push({ text: "תוכנית ", code: item.code, size: CODE.size, height: CODE.line, color: COLORS.muted });
  return lines;
}

const linesHeight = (lines: Line[]) => lines.reduce((sum, line) => sum + line.height, 0);

/** Stack nodes down from `top`, each in a slot tall enough for its label. */
function place(items: ReportItem[], k: number, top: number, master: Set<string>, labelW: number) {
  const out: Placed[] = [];
  let y = top;
  for (const item of items) {
    const h = item.amount * k;
    const slot = Math.max(h, linesHeight(labelLines(item, master, labelW)) + 2);
    const nodeTop = y - (slot - h) / 2;
    out.push({ item, top: nodeTop, bottom: nodeTop - h, mid: y - slot / 2 });
    y -= slot + GAP;
  }
  return { nodes: out, height: top - y - GAP };
}

export function ReportMoneyFlow() {
  const flow = useLetterReport()?.money_flow;
  const [ref, cardWidth] = useElementWidth<HTMLDivElement>();
  if (!flow?.hubs.length || !flow.destinations.length) return null;
  const width = Math.max(cardWidth, MIN_WIDTH);
  const labelW = width * 0.26;
  const master = new Set(flow.master);
  const sources = flow.hubs.flatMap((hub) => hub.items); // grouped by hub: bands never cross
  const destinations = [...flow.destinations];
  if (flow.folded.length)
    destinations.push({
      code: "",
      name: `עוד ${flow.folded.length} תוכניות`,
      amount: flow.folded.reduce((sum, item) => sum + item.amount, 0),
    });
  const total = destinations.reduce((sum, item) => sum + item.amount, 0);
  const k = Math.min(width * 0.36, 320) / total; // px per thousand ₪

  const height =
    Math.max(
      place(sources, k, 0, master, labelW).height,
      place(destinations, k, 0, master, labelW).height,
      total * k,
    ) + TOP + BOTTOM;
  const top = height - TOP;
  const srcNodes = place(sources, k, top, master, labelW).nodes;
  const dstNodes = place(destinations, k, top, master, labelW).nodes;
  const xSrc = width - labelW - 10 - NODE_W;
  const xDst = labelW + 10;
  const xHub = (xSrc + xDst) / 2 - NODE_W / 2;
  const Y = (y: number) => height - y;

  const band = (x0: number, y0t: number, y0b: number, x1: number, y1t: number, y1b: number) => {
    const mx = (x0 + x1) / 2;
    return `M${x0},${Y(y0t)} C${mx},${Y(y0t)} ${mx},${Y(y1t)} ${x1},${Y(y1t)} L${x1},${Y(y1b)} C${mx},${Y(y1b)} ${mx},${Y(y0b)} ${x0},${Y(y0b)} Z`;
  };
  const labels: Label[] = [];
  const label = (x: number, mid: number, item: ReportItem, anchor: Label["anchor"]) => {
    const lines = labelLines(item, master, labelW);
    let y = mid + linesHeight(lines) / 2;
    for (const line of lines) {
      labels.push({ x, y: y - line.height * 0.75, anchor, line }); // baseline about 3/4 down the line
      y -= line.height;
    }
  };

  // the hubs: one contiguous column, vertically centred; sources pour into their own hub
  const hubTop = top - (top - BOTTOM - total * k) / 2;
  const hubRects: { y: number; h: number }[] = [];
  const hubLabels: { y: number; text: string }[] = [];
  const sourceBands: string[] = [];
  let y = hubTop;
  let next = 0;
  flow.hubs.forEach((hub, i) => {
    const sum = hub.items.reduce((s, item) => s + item.amount, 0);
    const h = sum * k;
    hubRects.push({ y, h });
    let yIn = y;
    for (const item of hub.items) {
      const node = srcNodes[next++];
      sourceBands.push(band(xHub + NODE_W, yIn, yIn - item.amount * k, xSrc, node.top, node.bottom));
      yIn -= item.amount * k;
    }
    hubLabels.push({ y: i === 0 ? y + 6 : y - h - 18, text: `${hub.name} · ${money(sum)}` }); // first above, second below
    y -= h;
  });
  srcNodes.forEach((node) => label(xSrc + NODE_W + 6, node.mid, node.item, "start"));

  // the destinations fan out of the hub column, largest first
  const destBands: string[] = [];
  let yOut = hubTop;
  for (const node of dstNodes) {
    destBands.push(band(xDst + NODE_W, node.top, node.bottom, xHub, yOut, yOut - node.item.amount * k));
    yOut -= node.item.amount * k;
    label(xDst - 6, node.mid, node.item, "end");
  }

  // anchors are as the PDF draws them (start = text runs right of x); with direction rtl, SVG's
  // own start is the text's right end, so start and end swap
  const svgAnchor = { start: "end", end: "start" } as const;
  const hubX = xHub + NODE_W / 2;
  return (
    <section className="rounded-lg border bg-card p-5">
      <div className="flex justify-between gap-4">
        <h3>מאיפה מגיע הכסף</h3>
        <h3>לאן הולך הכסף</h3>
      </div>
      <div ref={ref} className="mt-4 overflow-x-auto">
        {cardWidth ? (
          <svg width={width} height={height} fontFamily={FONT} direction="rtl">
            {sourceBands.map((d, i) => (
              <path key={`s${i}`} d={d} style={{ fill: COLORS.source }} fillOpacity={BAND_OPACITY} />
            ))}
            {destBands.map((d, i) => (
              <path key={`d${i}`} d={d} style={{ fill: COLORS.destination }} fillOpacity={BAND_OPACITY} />
            ))}
            {hubRects.map((r, i) => (
              <rect key={`h${i}`} x={xHub} y={Y(r.y)} width={NODE_W} height={r.h} style={{ fill: COLORS.muted, stroke: COLORS.surface }} />
            ))}
            {srcNodes.map((n, i) => (
              <rect key={`sn${i}`} x={xSrc} y={Y(n.top)} width={NODE_W} height={n.top - n.bottom} style={{ fill: COLORS.source }} />
            ))}
            {dstNodes.map((n, i) => (
              <rect key={`dn${i}`} x={xDst} y={Y(n.top)} width={NODE_W} height={n.top - n.bottom} style={{ fill: COLORS.destination }} />
            ))}
            {hubLabels.map((hub, i) => {
              const w = textWidth(hub.text, LABEL.size);
              return (
                <g key={`hl${i}`}>
                  <rect x={hubX - w / 2 - 4} y={Y(hub.y) - 14} width={w + 8} height={LABEL.line} style={{ fill: COLORS.surface }} />
                  <text x={hubX} y={Y(hub.y)} fontSize={LABEL.size} textAnchor="middle" style={{ fill: COLORS.ink }}>
                    {hub.text}
                  </text>
                </g>
              );
            })}
            {labels.map((l, i) => (
              <text key={`l${i}`} x={l.x} y={Y(l.y)} fontSize={l.line.size} textAnchor={svgAnchor[l.anchor]} style={{ fill: l.line.color }}>
                {l.line.text}
                {l.line.code ? <tspan fontFamily="JetBrains Mono, monospace">{l.line.code}</tspan> : null}
              </text>
            ))}
          </svg>
        ) : null}
      </div>
      <p className="mt-2 text-[11px] text-muted-foreground">שם בכחול = תוכנית מהמאסטר</p>
    </section>
  );
}
