import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogTitle,
  DialogTrigger,
} from "../../components/ui/dialog";
import { ForgotPasswordForm } from "./forgot-password-form";

export function ForgotPasswordButton() {
  const [open, setOpen] = useState(false);
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <button
          type="button"
          className="mt-4 block w-full text-center text-sm underline-offset-4 hover:underline"
        >
          שכחתי סיסמה
        </button>
      </DialogTrigger>
      <DialogContent>
        <DialogTitle className="text-xl font-semibold">איפוס סיסמה</DialogTitle>
        <ForgotPasswordForm onDone={() => setOpen(false)} />
      </DialogContent>
    </Dialog>
  );
}
