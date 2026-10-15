import { useState } from "react";
import { Menu } from "lucide-react";
import { Outlet } from "react-router-dom";
import {
  Sheet,
  SheetContent,
  SheetTitle,
  SheetTrigger,
} from "../components/ui/sheet";
import { Button } from "../components/ui/button";
import { Nav } from "../components/nav";

export function AppLayout() {
  const [menuOpen, setMenuOpen] = useState(false);
  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[17rem_1fr]">
      <aside className="hidden border-s bg-card p-5 lg:block">
        <Nav />
      </aside>
      <header className="flex min-h-16 items-center justify-between border-b bg-card px-4 lg:hidden">
        <span className="font-semibold">ברל מוני</span>
        <Sheet open={menuOpen} onOpenChange={setMenuOpen}>
          <SheetTrigger asChild>
            <Button variant="ghost" size="icon" aria-label="פתיחת תפריט">
              <Menu size={20} />
            </Button>
          </SheetTrigger>
          <SheetContent side="right" className="w-72 lg:hidden">
            <SheetTitle className="sr-only">תפריט</SheetTitle>
            <Nav close={() => setMenuOpen(false)} />
          </SheetContent>
        </Sheet>
      </header>
      <main className="min-w-0 px-4 py-8 lg:px-[30px]">
        <div className="mx-auto max-w-[1200px]">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
