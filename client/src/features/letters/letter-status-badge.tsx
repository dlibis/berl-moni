import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { CircleAlert, CircleX, Eye, LoaderCircle } from "lucide-react";
import { Button } from "../../components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "../../components/ui/tooltip";
import { lastErrorLabel } from "./last-error";
import type { LetterItem } from "./types";

const base = "rounded-full px-2 py-0.5 text-xs";
const onCls =
  "bg-green-500/15 font-bold text-green-800 dark:text-green-300";
const offCls = "bg-muted text-muted-foreground";

function FlagBadge({ on, yes, no }: { on: boolean; yes: string; no: string }) {
  return (
    <span className={`${base} ${on ? onCls : offCls}`}>{on ? yes : no}</span>
  );
}

function HintIcon({
  label,
  className = "text-red-500",
  children,
}: {
  label: string;
  className?: string;
  children: ReactNode;
}) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span
          className={`inline-flex ${className}`}
          tabIndex={0}
          aria-label={label}
        >
          {children}
        </span>
      </TooltipTrigger>
      <TooltipContent>{label}</TooltipContent>
    </Tooltip>
  );
}

export function LetterRelevantBadge({ letter }: { letter: LetterItem }) {
  if (letter.analysis_status !== "analyzed") return null;
  return <FlagBadge on={letter.relevant} yes="רלוונטי" no="לא רלוונטי" />;
}

export function LetterAnalysisIcon({ letter }: { letter: LetterItem }) {
  if (letter.analysis_status === "failed") {
    return (
      <HintIcon label={lastErrorLabel(letter.last_error) ?? "תקלה"}>
        <CircleX size={16} aria-hidden />
      </HintIcon>
    );
  }
  if (letter.analysis_status !== "analyzed") {
    const analyzing = letter.analysis_status === "analyzing";
    return (
      <HintIcon
        label={analyzing ? "הניתוח מתבצע" : "ממתין לניתוח"}
        className="text-muted-foreground"
      >
        <LoaderCircle
          size={16}
          className="animate-spin"
          aria-hidden
        />
      </HintIcon>
    );
  }
  if (!letter.last_error) return null;
  return (
    <HintIcon label={lastErrorLabel(letter.last_error) ?? "תקלה"}>
      <CircleX size={16} aria-hidden />
    </HintIcon>
  );
}

export function LetterReportCell({ letter }: { letter: LetterItem }) {
  return (
    <div className="flex items-center justify-center gap-1">
      <LetterAnalysisIcon letter={letter} />
      {letter.report_available || letter.analysis_status === "analyzed" ? (
        <Button asChild variant="ghost" size="sm" className="h-8 w-8 p-0">
          <Link to={`/letters/${letter.slug}`} aria-label="צפייה בדוח">
            <Eye aria-hidden />
          </Link>
        </Button>
      ) : null}
    </div>
  );
}

export function RequiresReviewIcon({ show }: { show: boolean }) {
  if (!show) return null;
  return (
    <HintIcon label="דורש עיון">
      <CircleAlert size={16} aria-hidden />
    </HintIcon>
  );
}

export function LetterPassedBadge({ passed }: { passed: boolean }) {
  return <FlagBadge on={passed} yes="עברה" no="לא עברה" />;
}
