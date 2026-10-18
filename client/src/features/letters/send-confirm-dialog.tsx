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
      description="המכתב כבר נשלח. לשלוח שוב לכל רשימת התפוצה?"
      action="שליחה"
      pending={pending}
      onConfirm={onConfirm}
    />
  );
}
