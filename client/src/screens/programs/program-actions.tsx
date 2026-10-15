import { Pencil, Trash2 } from "lucide-react";
import { useState } from "react";
import type { Program } from "../../lib/programs";
import { Button } from "../../components/ui/button";
import { Dialog, DialogContent, DialogTitle, DialogTrigger } from "../../components/ui/dialog";
import { AlertDialog, AlertDialogTrigger, ConfirmDialog } from "../../components/ui/alert-dialog";
import { ProgramForm } from "./program-form";

export function ProgramActions({
  program,
  onRemove,
  pending,
}: {
  program: Program;
  onRemove: () => void;
  pending: boolean;
}) {
  const [edit, setEdit] = useState(false);
  return (
    <div className="float-left flex gap-1">
      <Dialog open={edit} onOpenChange={setEdit}>
        <DialogTrigger asChild>
          <Button variant="ghost" size="icon" aria-label={`עריכת ${program.name}`} title="עריכה">
            <Pencil size={16} />
          </Button>
        </DialogTrigger>
        <DialogContent>
          <DialogTitle className="text-xl font-semibold">עריכת תוכנית</DialogTitle>
          <ProgramForm initial={program} onDone={() => setEdit(false)} />
        </DialogContent>
      </Dialog>
      <AlertDialog>
        <AlertDialogTrigger asChild>
          <Button variant="ghost" size="icon" aria-label={`מחיקת ${program.name}`} title="מחיקה">
            <Trash2 size={16} className="text-destructive" />
          </Button>
        </AlertDialogTrigger>
        <ConfirmDialog
          title="למחוק את התוכנית?"
          description={`התוכנית ${program.name} (${program.code}) תימחק.`}
          action="מחיקת תוכנית"
          destructive
          pending={pending}
          onConfirm={onRemove}
        />
      </AlertDialog>
    </div>
  );
}
