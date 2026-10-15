import * as DialogPrimitive from "@radix-ui/react-dialog"
import { X } from "lucide-react"
import { cn } from "../../lib/utils"
export const Dialog = DialogPrimitive.Root
export const DialogTrigger = DialogPrimitive.Trigger
export const DialogTitle = DialogPrimitive.Title
export const DialogDescription = DialogPrimitive.Description
export function DialogContent({ className, children, ...props }: React.ComponentPropsWithoutRef<typeof DialogPrimitive.Content>) { return <DialogPrimitive.Portal><DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-foreground/25" /><DialogPrimitive.Content className={cn("fixed start-1/2 top-1/2 z-50 w-[calc(100%-2rem)] max-w-lg -translate-x-1/2 -translate-y-1/2 rounded-lg border bg-card p-6 shadow-lg", className)} {...props}>{children}<DialogPrimitive.Close aria-label="סגירה" className="absolute left-3 top-3 rounded p-2 hover:bg-muted"><X size={16} /></DialogPrimitive.Close></DialogPrimitive.Content></DialogPrimitive.Portal> }
