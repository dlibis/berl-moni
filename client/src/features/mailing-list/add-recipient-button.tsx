import { useState } from "react";
import { Plus } from "lucide-react";
import { Button } from "../../components/ui/button";
import { Dialog, DialogContent, DialogTitle, DialogTrigger } from "../../components/ui/dialog";
import { EmailForm } from "./email-form";
import { useMailingList } from "../../hooks/use-mailing-list";

export function AddRecipientButton() {
  const [open, setOpen] = useState(false);
  const mailing = useMailingList();
  if (!mailing.data) return null;
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button disabled={mailing.data.count >= mailing.data.cap}>
          <Plus size={16} />
          הוספת נמען
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogTitle className="text-xl font-semibold">הוספת נמען</DialogTitle>
        <EmailForm onDone={() => setOpen(false)} />
      </DialogContent>
    </Dialog>
  );
}
