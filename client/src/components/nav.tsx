import { CalendarDays, House, Inbox, List, Mail } from "lucide-react";
import { NavLink } from "react-router-dom";
import { cn } from "../utils/utils";
import { SignOutButton } from "../features/auth/sign-out-button";

const navigation = [
  ["/", "ראשי", House],
  ["/programs", "תוכניות", List],
  ["/mailing-list", "רשימת תפוצה", Mail],
  ["/schedule", "לוח שליחה", CalendarDays],
  ["/mailbox", "תיבת דואר", Inbox],
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
          <NavLink
            end={to === "/"}
            onClick={close}
            key={to}
            to={to}
            className={({ isActive }) =>
              cn(
                "flex min-h-12 items-center gap-3 rounded-md px-3 text-sm transition-colors lg:min-h-10",
                isActive
                  ? "bg-primary text-primary-foreground"
                  : "hover:bg-accent",
              )
            }
          >
            <Icon size={20} />
            {label}
          </NavLink>
        ))}
      </div>
      <div className="mt-auto border-t pt-4">
        <SignOutButton />
      </div>
    </nav>
  );
}
