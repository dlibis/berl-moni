import { useState } from "react";
import { MoreVertical } from "lucide-react";
import { Button } from "../../components/ui/button";
import { AlertDialog } from "../../components/ui/alert-dialog";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "../../components/ui/popover";
import { ConfirmDialog } from "../../components/confirm-dialog";
import { useAnalyzeLetter } from "../../hooks/use-analyze-letter";

export function ReanalyzeMenu({ slug }: { slug: string }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const analyze = useAnalyzeLetter();
  return (
    <>
      <Popover open={menuOpen} onOpenChange={setMenuOpen}>
        <PopoverTrigger asChild>
          <Button variant="ghost" size="sm" aria-label="פעולות נוספות">
            <MoreVertical className="size-4" />
          </Button>
        </PopoverTrigger>
        <PopoverContent align="end" className="w-auto p-1">
          <Button
            variant="ghost"
            size="sm"
            className="w-full justify-start"
            onClick={() => {
              setMenuOpen(false);
              setConfirmOpen(true);
            }}
          >
            ניתוח מחדש
          </Button>
        </PopoverContent>
      </Popover>
      <AlertDialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <ConfirmDialog
          title="לנתח מחדש?"
          description="ניתוח מחדש יעלה קריאה נוספת למודל"
          action="ניתוח מחדש"
          pending={analyze.isPending}
          onConfirm={() => analyze.mutate({ slug, reanalyze: true })}
        />
      </AlertDialog>
    </>
  );
}
