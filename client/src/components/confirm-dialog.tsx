import {
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { buttonVariants } from "@/components/ui/button";

export function ConfirmDialog({
  title,
  description,
  action,
  pending,
  destructive = false,
  onConfirm,
}: {
  title: string;
  description: string;
  action: string;
  pending?: boolean;
  destructive?: boolean;
  onConfirm: () => void;
}) {
  return (
    <AlertDialogContent>
      <AlertDialogHeader>
        <AlertDialogTitle>{title}</AlertDialogTitle>
        <AlertDialogDescription>{description}</AlertDialogDescription>
      </AlertDialogHeader>
      <AlertDialogFooter>
        <AlertDialogCancel>ביטול</AlertDialogCancel>
        <AlertDialogAction
          className={
            destructive ? buttonVariants({ variant: "destructive" }) : undefined
          }
          disabled={pending}
          onClick={onConfirm}
        >
          {pending ? "שומר…" : action}
        </AlertDialogAction>
      </AlertDialogFooter>
    </AlertDialogContent>
  );
}
