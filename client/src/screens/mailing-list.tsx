import { FormEvent, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Pencil, Plus, Search, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { get, write } from "../lib/api";
import { Button } from "../components/ui/button";
import { Field } from "../components/field";
import { Dialog, DialogContent, DialogTitle, DialogTrigger } from "../components/ui/dialog";
import { AlertDialog, AlertDialogTrigger, ConfirmDialog } from "../components/ui/alert-dialog";
import { ErrorState, Loading, PageHeader } from "../components/states";
import { Pagination } from "../components/pagination";

type Mailing = { emails: string[]; count: number; cap: number };
const validEmail = (value: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
function EmailForm({ initial, onDone }: { initial?: string; onDone: () => void }) {
  const queryClient = useQueryClient();
  const [email, setEmail] = useState(initial ?? "");
  const [error, setError] = useState("");
  const save = useMutation({
    mutationFn: async () => {
      // No update endpoint: add the new address first so a failed add never loses the old one.
      const next = email.trim().toLowerCase();
      if (initial === next) return;
      await write("/api/v1/mailing_list", "POST", { email: next });
      if (initial) await write(`/api/v1/mailing_list/${encodeURIComponent(initial)}`, "DELETE");
    },
    onSuccess: () => {
      toast.success("הנמען נשמר");
      queryClient.invalidateQueries({ queryKey: ["mailing"] });
      onDone();
    },
    onError: () => setError(initial ? "לא ניתן לעדכן את הנמען" : "לא ניתן להוסיף את הנמען. ייתכן שהוא קיים."),
  });
  function submit(event: FormEvent) {
    event.preventDefault();
    if (!validEmail(email)) {
      setError("יש להזין כתובת דוא״ל תקינה");
      return;
    }
    save.mutate();
  }
  return (
    <form onSubmit={submit} className="mt-5 space-y-4">
      <Field
        label="כתובת דוא״ל"
        type="email"
        dir="ltr"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        error={email && !validEmail(email) ? "יש להזין כתובת דוא״ל תקינה" : error}
      />
      {initial ? <p className="text-xs text-muted-foreground">העדכון מחליף את הכתובת הקיימת.</p> : null}
      <Button type="submit" disabled={save.isPending}>
        {save.isPending ? "שומר…" : "שמירה"}
      </Button>
    </form>
  );
}
export function MailingList() {
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);
  const [open, setOpen] = useState(false);
  const queryClient = useQueryClient();
  const mailing = useQuery({ queryKey: ["mailing"], queryFn: () => get<Mailing>("/api/v1/mailing_list") });
  const remove = useMutation({
    mutationFn: (email: string) => write(`/api/v1/mailing_list/${encodeURIComponent(email)}`, "DELETE"),
    onSuccess: () => {
      toast.success("הנמען נמחק");
      queryClient.invalidateQueries({ queryKey: ["mailing"] });
    },
    onError: () => toast.error("לא ניתן למחוק את הנמען"),
  });
  const filtered = useMemo(
    () => (mailing.data?.emails ?? []).filter((email) => email.includes(search.trim().toLowerCase())),
    [mailing.data, search],
  );
  const rows = filtered.slice(page * 25, page * 25 + 25);
  if (mailing.isPending) return <Loading />;
  if (mailing.isError || !mailing.data) return <ErrorState />;
  const atCap = mailing.data.count >= mailing.data.cap;
  return (
    <>
      <PageHeader title="רשימת תפוצה">
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button disabled={atCap}>
              <Plus size={16} />
              הוספת נמען
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogTitle className="text-xl font-semibold">הוספת נמען</DialogTitle>
            <EmailForm onDone={() => setOpen(false)} />
          </DialogContent>
        </Dialog>
      </PageHeader>
      <p className="mb-4 text-sm">
        {mailing.data.count} / {mailing.data.cap} נמענים
      </p>
      {atCap ? (
        <p className="mb-4 text-sm text-muted-foreground">
          הגעת למכסה הנגזרת ממגבלת השליחה היומית של Resend.
        </p>
      ) : null}
      <div className="max-w-xl">
        <label className="relative block">
          <span className="sr-only">חיפוש נמען</span>
          <Search className="absolute right-3 top-3 text-muted-foreground" size={18} />
          <input
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(0);
            }}
            placeholder="חיפוש כתובת דוא״ל"
            className="h-12 w-full rounded-md border bg-background ps-10 pe-3 text-sm outline-none focus:ring-2 focus:ring-ring lg:h-10"
          />
        </label>
      </div>
      {filtered.length === 0 ? (
        <div className="mt-6 rounded-lg border bg-card p-6 text-muted-foreground">אין נמענים עדיין</div>
      ) : (
        <>
          <div className="mt-5 hidden overflow-hidden rounded-lg border md:block">
            <table className="w-full text-sm">
              <thead className="bg-muted">
                <tr>
                  <th className="p-3 text-start font-semibold">כתובת דוא״ל</th>
                  <th className="p-3">
                    <span className="sr-only">פעולות</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {rows.map((email) => (
                  <tr className="border-t" key={email}>
                    <td className="p-3" dir="ltr">
                      {email}
                    </td>
                    <td className="p-2">
                      <EmailActions
                        email={email}
                        remove={() => remove.mutate(email)}
                        pending={remove.isPending}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-5 space-y-3 md:hidden">
            {rows.map((email) => (
              <div key={email} className="rounded-lg border bg-card p-4">
                <EmailActions email={email} remove={() => remove.mutate(email)} pending={remove.isPending} />
                <p dir="ltr" className="truncate text-sm">
                  {email}
                </p>
              </div>
            ))}
          </div>
          <Pagination page={page} count={filtered.length} setPage={setPage} />
        </>
      )}
    </>
  );
}
function EmailActions({ email, remove, pending }: { email: string; remove: () => void; pending: boolean }) {
  const [edit, setEdit] = useState(false);
  return (
    <div className="float-left flex gap-1">
      <Dialog open={edit} onOpenChange={setEdit}>
        <DialogTrigger asChild>
          <Button variant="ghost" size="icon" aria-label={`עריכת ${email}`} title="עריכה">
            <Pencil size={16} />
          </Button>
        </DialogTrigger>
        <DialogContent>
          <DialogTitle className="text-xl font-semibold">עריכת נמען</DialogTitle>
          <EmailForm initial={email} onDone={() => setEdit(false)} />
        </DialogContent>
      </Dialog>
      <AlertDialog>
        <AlertDialogTrigger asChild>
          <Button variant="ghost" size="icon" aria-label={`מחיקת ${email}`} title="מחיקה">
            <Trash2 size={16} className="text-destructive" />
          </Button>
        </AlertDialogTrigger>
        <ConfirmDialog
          title="למחוק את הנמען?"
          description={`הכתובת ${email} תוסר מרשימת התפוצה.`}
          action="מחיקת נמען"
          destructive
          pending={pending}
          onConfirm={remove}
        />
      </AlertDialog>
    </div>
  );
}
