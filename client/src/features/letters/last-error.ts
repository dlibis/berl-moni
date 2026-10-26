/** Worker-written `letters.last_error` codes. Unknown values stay a generic sentence. */
const LABELS: Record<string, string> = {
  quota: "מכסת המודל נוצלה",
  model_overloaded: "המודל עמוס כרגע. אפשר לנסות לנתח שוב בעוד כמה דקות.",
  network: "שגיאת רשת",
  provider_5xx: "שגיאת שרת אצל הספק",
  extract_error: "ניתוח המכתב נכשל",
  no_text: "אין טקסט לקריאה במכתב",
  pdf_too_large: "הקובץ גדול מדי",
  lease_expired: "הניתוח נקטע",
};

export function lastErrorLabel(code: string | null): string | null {
  if (!code) return null;
  return LABELS[code] ?? "הניתוח נכשל";
}
