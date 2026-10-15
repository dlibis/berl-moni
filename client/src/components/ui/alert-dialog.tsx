import * as Alert from "@radix-ui/react-alert-dialog";
import { Button } from "./button";
export const AlertDialog = Alert.Root;
export const AlertDialogTrigger = Alert.Trigger;
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
    <Alert.Portal>
      <Alert.Overlay className="fixed inset-0 z-50 bg-foreground/25" />
      <Alert.Content className="fixed start-1/2 top-1/2 z-50 w-[calc(100%-2rem)] max-w-md -translate-x-1/2 -translate-y-1/2 rounded-lg border bg-card p-6 shadow-lg">
        <Alert.Title className="text-lg font-semibold">{title}</Alert.Title>
        <Alert.Description className="mt-2 text-sm text-muted-foreground">
          {description}
        </Alert.Description>
        <div className="mt-6 flex justify-start gap-2">
          <Alert.Action asChild>
            <Button
              variant={destructive ? "destructive" : "default"}
              disabled={pending}
              onClick={onConfirm}
            >
              {pending ? "שומר…" : action}
            </Button>
          </Alert.Action>
          <Alert.Cancel asChild>
            <Button variant="outline">ביטול</Button>
          </Alert.Cancel>
        </div>
      </Alert.Content>
    </Alert.Portal>
  );
}
