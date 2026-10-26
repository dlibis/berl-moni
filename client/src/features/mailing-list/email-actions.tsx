import { Pencil, Trash2 } from "lucide-react";
import { useState } from "react";
import { Button } from "../../components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogTitle,
  DialogTrigger,
} from "../../components/ui/dialog";
import {
  AlertDialog,
  AlertDialogTrigger,
} from "../../components/ui/alert-dialog";
import { ConfirmDialog } from "../../components/confirm-dialog";
import { EmailForm } from "./email-form";

export function EmailActions({
  email,
  name,
  onDelete,
}: {
  email: string;
  name: string;
  onDelete: () => void;
}) {
  const [edit, setEdit] = useState(false);
  return (
    <div className="float-left flex gap-1">
      <Dialog open={edit} onOpenChange={setEdit}>
        <DialogTrigger asChild>
          <Button
            variant="ghost"
            size="icon"
            aria-label={`עריכת ${email}`}
            title="עריכה"
          >
            <Pencil size={16} />
          </Button>
        </DialogTrigger>
        <DialogContent>
          <DialogTitle className="text-xl font-semibold">
            עריכת נמען
          </DialogTitle>
          <EmailForm
            initialEmail={email}
            initialName={name}
            onDone={() => setEdit(false)}
          />
        </DialogContent>
      </Dialog>
      <AlertDialog>
        <AlertDialogTrigger asChild>
          <Button
            variant="ghost"
            size="icon"
            aria-label={`מחיקת ${email}`}
            title="מחיקה"
          >
            <Trash2 size={16} className="text-destructive" />
          </Button>
        </AlertDialogTrigger>
        <ConfirmDialog
          title="למחוק את הנמען?"
          description={`הכתובת ${email} תוסר מרשימת התפוצה.`}
          action="מחיקת נמען"
          destructive
          onConfirm={onDelete}
        />
      </AlertDialog>
    </div>
  );
}
