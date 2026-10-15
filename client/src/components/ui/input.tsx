import { forwardRef } from "react";
import { cn } from "../../lib/utils";
export const Input = forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => (
    <input
      ref={ref}
      className={cn(
        "flex h-12 w-full rounded-md border bg-background px-3 py-2 text-sm outline-none placeholder:text-muted-foreground focus-visible:ring-2 focus-visible:ring-ring lg:h-10",
        className,
      )}
      {...props}
    />
  ),
);
Input.displayName = "Input";
