import { Pencil, Trash2 } from "lucide-react";
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { write } from "../../services/api";
import type { Program } from "./types";
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
import { ProgramForm } from "./program-form";

export function ProgramActions({ program }: { program: Program }) {
  const [edit, setEdit] = useState(false);
  const queryClient = useQueryClient();
  const remove = useMutation({
    mutationFn: () => write(`/api/v1/master/${program.code}`, "DELETE"),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["programs"] });
    },
    onError: () => toast.error("לא ניתן למחוק את התוכנית"),
  });
  return (
    <div className="float-left flex gap-1">
      <Dialog open={edit} onOpenChange={setEdit}>
        <DialogTrigger asChild>
          <Button
            variant="ghost"
            size="icon"
            aria-label={`עריכת ${program.name}`}
            title="עריכה"
          >
            <Pencil size={16} />
          </Button>
        </DialogTrigger>
        <DialogContent>
          <DialogTitle className="text-xl font-semibold">
            עריכת תוכנית
          </DialogTitle>
          <ProgramForm initial={program} onDone={() => setEdit(false)} />
        </DialogContent>
      </Dialog>
      <AlertDialog>
        <AlertDialogTrigger asChild>
          <Button
            variant="ghost"
            size="icon"
            aria-label={`מחיקת ${program.name}`}
            title="מחיקה"
          >
            <Trash2 size={16} className="text-destructive" />
          </Button>
        </AlertDialogTrigger>
        <ConfirmDialog
          title="למחוק את התוכנית?"
          description={`התוכנית ${program.name} (${program.code}) תימחק.`}
          action="מחיקת תוכנית"
          destructive
          pending={remove.isPending}
          onConfirm={() => remove.mutate()}
        />
      </AlertDialog>
    </div>
  );
}
