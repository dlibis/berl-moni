import { Fragment } from "react";
import { AtSign, CalendarDays, House, List, Mail } from "lucide-react";
import { NavLink } from "react-router-dom";
import { cn } from "../utils/utils";
import { SignOutButton } from "../features/auth/sign-out-button";

const navigation = [
  ["/", "ראשי", House],
  ["/programs", "תוכניות", List],
  ["/mailing-list", "רשימת תפוצה", Mail],
  ["/schedule", "מועדי שליחה", CalendarDays],
  ["/mailbox", "כתובות שליחה", AtSign],
] as const;
export function Nav({ close }: { close?: () => void }) {
  return (
    <nav className="flex h-full flex-col" aria-label="ניווט ראשי">
      <div className="mb-8 flex items-center gap-3">
        <img
          src="/logo.png"
          alt="לוגו ברל מוני"
          className="h-10 w-10 rounded-md object-contain"
        />
        <span className="font-semibold">ברל מוני</span>
      </div>
      <div className="space-y-1">
        {navigation.map(([to, label, Icon]) => (
          <Fragment key={to}>
            <NavLink
              end={to === "/"}
              onClick={close}
              to={to}
              className={({ isActive }) =>
                cn(
                  "flex min-h-12 items-center gap-3 rounded-md px-3 text-sm transition-colors lg:min-h-10",
                  isActive
                    ? "bg-accent font-medium text-accent-foreground"
                    : "text-muted-foreground hover:bg-accent/60 hover:text-foreground",
                )
              }
            >
              <Icon size={16} />
              {label}
            </NavLink>
            {to === "/" ? (
              <p className="px-3 pt-6 pb-2 text-xs font-medium text-muted-foreground">
                הגדרות
              </p>
            ) : null}
          </Fragment>
        ))}
      </div>
      <div className="mt-auto border-t pt-4">
        <SignOutButton />
      </div>
    </nav>
  );
}
