import { useEffect, useState } from "react";

/** A ref callback to put on an element, and that element's current width in px (0 until measured).
 * A callback ref, so an element that appears after the first render is still observed. */
export function useElementWidth<T extends HTMLElement>() {
  const [element, ref] = useState<T | null>(null);
  const [width, setWidth] = useState(0);
  useEffect(() => {
    if (!element) return;
    const observer = new ResizeObserver(([entry]) => setWidth(entry.contentRect.width));
    observer.observe(element);
    return () => observer.disconnect();
  }, [element]);
  return [ref, width] as const;
}
