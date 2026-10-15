import { useId } from "react";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
export function Field({
  label,
  helper,
  error,
  id,
  ...props
}: React.InputHTMLAttributes<HTMLInputElement> & {
  label: string;
  helper?: string;
  error?: string;
}) {
  const generatedId = useId();
  const inputId = id ?? generatedId;
  return (
    <div className="block text-sm font-medium">
      <Label htmlFor={inputId}>{label}</Label>
      <Input id={inputId} className="mt-2" {...props} />
      {error ? (
        <span className="mt-1 block text-xs text-destructive">{error}</span>
      ) : helper ? (
        <span className="mt-1 block text-xs font-normal text-muted-foreground">
          {helper}
        </span>
      ) : null}
    </div>
  );
}
