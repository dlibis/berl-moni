import { Menu, CalendarDays, House, Inbox, List, Mail, Settings2 } from "lucide-react"
import { NavLink, Outlet } from "react-router-dom"
import { Sheet, SheetContent, SheetTrigger } from "./ui/sheet"
import { Button } from "./ui/button"
import { cn } from "../lib/utils"

const navigation = [
  ["/", "ראשי", House], ["/programs", "תוכניות", List], ["/mailing-list", "רשימת תפוצה", Mail], ["/schedule", "לוח שליחה", CalendarDays], ["/mailbox", "תיבת דואר", Inbox],
] as const
function Nav({ close }: { close?: () => void }) { return <nav className="flex h-full flex-col" aria-label="ניווט ראשי"><div className="mb-8 flex items-center gap-3"><img src="/logo.png" alt="לוגו ברל מוני" className="h-10 w-10 rounded-md object-contain" /><span className="font-semibold">ברל מוני</span></div><div className="space-y-1">{navigation.map(([to, label, Icon]) => <NavLink end={to === "/"} onClick={close} key={to} to={to} className={({ isActive }) => cn("flex min-h-12 items-center gap-3 rounded-md px-3 text-sm transition-colors lg:min-h-10", isActive ? "bg-primary text-primary-foreground" : "hover:bg-accent")}><Icon size={20} />{label}</NavLink>)}</div><div className="mt-auto border-t pt-4 text-xs text-muted-foreground"><Settings2 className="inline-block align-text-bottom" size={16} /> הגדרות ניהול</div></nav> }
export function AppLayout() { return <div className="min-h-screen lg:grid lg:grid-cols-[1fr_17rem]"><aside className="hidden border-s bg-card p-5 lg:block"><Nav /></aside><header className="flex min-h-16 items-center justify-between border-b bg-card px-4 lg:hidden"><span className="font-semibold">ברל מוני</span><Sheet><SheetTrigger asChild><Button variant="ghost" size="icon" aria-label="פתיחת תפריט"><Menu size={20} /></Button></SheetTrigger><SheetContent><Nav /></SheetContent></Sheet></header><main className="min-w-0 px-4 py-8 lg:px-[30px]"><div className="mx-auto max-w-[1200px]"><Outlet /></div></main></div> }
