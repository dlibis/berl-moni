import { ConfirmDialog } from "../../components/confirm-dialog";

export function SendConfirmDialog({
  pending,
  onConfirm,
}: {
  pending: boolean;
  onConfirm: () => void;
}) {
  return (
    <ConfirmDialog
      title="לשלוח שוב?"
      description="הפנייה כבר נשלחה. לשלוח שוב לכל רשימת התפוצה?"
      action="שליחה"
      pending={pending}
      onConfirm={onConfirm}
    />
  );
}
