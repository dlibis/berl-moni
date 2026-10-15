import { Menu } from "lucide-react";
import { Outlet } from "react-router-dom";
import { Sheet, SheetContent, SheetTrigger } from "./ui/sheet";
import { Button } from "./ui/button";
import { Nav } from "./nav";

export function AppLayout() {
  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[1fr_17rem]">
      <aside className="hidden border-s bg-card p-5 lg:block">
        <Nav />
      </aside>
      <header className="flex min-h-16 items-center justify-between border-b bg-card px-4 lg:hidden">
        <span className="font-semibold">ברל מוני</span>
        <Sheet>
          <SheetTrigger asChild>
            <Button variant="ghost" size="icon" aria-label="פתיחת תפריט">
              <Menu size={20} />
            </Button>
          </SheetTrigger>
          <SheetContent>
            <Nav />
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

