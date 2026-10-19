// The report's chart colors and money format, as the summary PDF has them (theme.py), but drawn in
// the app's own theme tokens so the report follows light and dark mode.
export const COLORS = {
  ink: "hsl(var(--foreground))",
  muted: "hsl(var(--muted-foreground))",
  master: "hsl(var(--report-master))", // a program on the master list
  source: "hsl(var(--destructive))", // money leaving a program
  destination: "hsl(var(--primary))", // money reaching a program
  surface: "hsl(var(--card))",
};
export const FONT = "Outfit, Rubik, system-ui, sans-serif"; // the app's font (tailwind.config.ts)

export const UNIT = "אלפי ש״ח";
export const COALITION_TAG = "קואליציוני";

export const amount = (value: number) =>
  Math.abs(value).toLocaleString("en-US", { maximumFractionDigits: 0 });

export const money = (thousands: number) => `${amount(thousands)} ${UNIT}`;

let canvas: HTMLCanvasElement | undefined;

export function textWidth(text: string, size: number): number {
  canvas ??= document.createElement("canvas");
  const context = canvas.getContext("2d");
  if (!context) return text.length * size * 0.5;
  context.font = `${size}px ${FONT}`;
  return context.measureText(text).width;
}

/** Greedy word wrap of one line, by measured width (hebrew_text.wrap). */
export function wrap(line: string, width: number, size: number): string[] {
  const rows: string[] = [];
  let current = "";
  for (const word of line.split(" ")) {
    const trial = `${current} ${word}`.trim();
    if (!current || textWidth(trial, size) <= width) current = trial;
    else {
      rows.push(current);
      current = word;
    }
  }
  return [...rows, current];
}
