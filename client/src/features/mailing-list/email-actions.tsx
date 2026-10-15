import { Pencil, Trash2 } from "lucide-react";
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { write } from "../../lib/api";
import { Button } from "../../components/ui/button";
import { Dialog, DialogContent, DialogTitle, DialogTrigger } from "../../components/ui/dialog";
import { AlertDialog, AlertDialogTrigger, ConfirmDialog } from "../../components/ui/alert-dialog";
import { EmailForm } from "./email-form";

export function EmailActions({ email }: { email: string }) {
  const [edit, setEdit] = useState(false);
  const queryClient = useQueryClient();
  const remove = useMutation({
    mutationFn: () => write(`/api/v1/mailing_list/${encodeURIComponent(email)}`, "DELETE"),
    onSuccess: () => {
      toast.success("הנמען נמחק");
      queryClient.invalidateQueries({ queryKey: ["mailing"] });
    },
    onError: () => toast.error("לא ניתן למחוק את הנמען"),
  });
  return (
    <div className="float-left flex gap-1">
      <Dialog open={edit} onOpenChange={setEdit}>
        <DialogTrigger asChild>
          <Button variant="ghost" size="icon" aria-label={`עריכת ${email}`} title="עריכה">
            <Pencil size={16} />
          </Button>
        </DialogTrigger>
        <DialogContent>
          <DialogTitle className="text-xl font-semibold">עריכת נמען</DialogTitle>
          <EmailForm initial={email} onDone={() => setEdit(false)} />
        </DialogContent>
      </Dialog>
      <AlertDialog>
        <AlertDialogTrigger asChild>
          <Button variant="ghost" size="icon" aria-label={`מחיקת ${email}`} title="מחיקה">
            <Trash2 size={16} className="text-destructive" />
          </Button>
        </AlertDialogTrigger>
        <ConfirmDialog
          title="למחוק את הנמען?"
          description={`הכתובת ${email} תוסר מרשימת התפוצה.`}
          action="מחיקת נמען"
          destructive
          pending={remove.isPending}
          onConfirm={() => remove.mutate()}
        />
      </AlertDialog>
    </div>
  );
}
