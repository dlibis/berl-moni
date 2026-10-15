import { Outlet } from "react-router-dom";

export function AuthLayout() {
  return (
    <main className="flex min-h-screen items-center justify-center p-4">
      <section className="w-full max-w-sm rounded-lg border bg-card p-6">
        <img
          src="/logo.png"
          alt="לוגו ברל מוני"
          className="mx-auto mb-4 h-12 w-12 rounded-md object-contain"
        />
        <Outlet />
      </section>
    </main>
  );
}
