import { Input } from "./ui/input";
export function Field({
  label,
  helper,
  error,
  ...props
}: React.InputHTMLAttributes<HTMLInputElement> & { label: string; helper?: string; error?: string }) {
  return (
    <label className="block text-sm font-medium">
      <span>{label}</span>
      <Input className="mt-1" {...props} />
      {error ? (
        <span className="mt-1 block text-xs text-destructive">{error}</span>
      ) : helper ? (
        <span className="mt-1 block text-xs font-normal text-muted-foreground">{helper}</span>
      ) : null}
    </label>
  );
}
