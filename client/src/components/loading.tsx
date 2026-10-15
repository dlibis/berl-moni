import { LoaderCircle } from "lucide-react";

export function Loading() {
  return (
    <div className="flex min-h-48 items-center justify-center text-muted-foreground">
      <LoaderCircle className="animate-spin" size={24} />{" "}
      <span className="me-2">טוען…</span>
    </div>
  );
}
