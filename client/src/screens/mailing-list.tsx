import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Search } from "lucide-react";
import { toast } from "sonner";
import { get, write } from "../lib/api";
import { Button } from "../components/ui/button";
import { Dialog, DialogContent, DialogTitle, DialogTrigger } from "../components/ui/dialog";
import { ErrorState } from "../components/error-state";
import { Loading } from "../components/loading";
import { PageHeader } from "../components/page-header";
import { Pagination } from "../components/pagination";
import { EmailActions } from "./mailing-list/email-actions";
import { EmailForm } from "./mailing-list/email-form";

type Mailing = { emails: string[]; count: number; cap: number };
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
