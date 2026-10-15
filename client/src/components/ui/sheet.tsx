import * as DialogPrimitive from "@radix-ui/react-dialog";
import { X } from "lucide-react";
export const Sheet = DialogPrimitive.Root;
export const SheetTrigger = DialogPrimitive.Trigger;
export function SheetContent({ children }: { children: React.ReactNode }) {
  return (
    <DialogPrimitive.Portal>
      <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-foreground/25 lg:hidden" />
      <DialogPrimitive.Content className="fixed inset-y-0 right-0 z-50 w-72 border-s bg-card p-5 shadow-xl lg:hidden">
        {children}
        <DialogPrimitive.Close
          aria-label="סגירה"
          className="absolute left-3 top-3 rounded p-2 hover:bg-muted"
        >
          <X size={16} />
        </DialogPrimitive.Close>
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  );
}
