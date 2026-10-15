export function NotSignedIn() {
  return (
    <main className="flex min-h-screen items-center justify-center p-4">
      <section className="max-w-sm rounded-lg border bg-card p-6 text-center shadow-sm">
        <h1 className="text-xl font-semibold">לא מחוברים</h1>
        <p className="mt-3 text-sm text-muted-foreground">יש להתחבר כדי לצפות במערכת.</p>
      </section>
    </main>
  );
}
