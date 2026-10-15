import { AlertCircle } from "lucide-react";

export function ErrorState({
  text = "לא ניתן לטעון את הנתונים כעת",
}: {
  text?: string;
}) {
  return (
    <div
      role="alert"
      className="flex items-center gap-2 rounded-md border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive"
    >
      <AlertCircle size={18} />
      {text}
    </div>
  );
}
