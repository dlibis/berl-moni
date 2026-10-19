import { startTransition, useMemo, useOptimistic, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { toast } from "sonner";
import { ErrorState } from "../../components/error-state";
import { Loading } from "../../components/loading";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../../components/ui/table";
import { Pagination } from "../../components/pagination";
import { write } from "../../services/api";
import { EmailActions } from "./email-actions";
import { useMailingList, type Mailing } from "../../hooks/use-mailing-list";

export function RecipientList() {
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);
  const mailing = useMailingList();
  const queryClient = useQueryClient();
  const [emails, removeEmail] = useOptimistic(
    mailing.data?.emails ?? [],
    (current, email: string) => current.filter((item) => item !== email),
  );
  const filtered = useMemo(
    () =>
      emails.filter((email) => email.includes(search.trim().toLowerCase())),
    [emails, search],
  );
  const rows = filtered.slice(page * 25, page * 25 + 25);

  function handleDelete(email: string) {
    startTransition(async () => {
      removeEmail(email);
      try {
        await write("/api/v1/mailing_list", "DELETE", { email });
        queryClient.setQueryData<Mailing>(["mailing"], (old) =>
          old
            ? {
                ...old,
                emails: old.emails.filter((item) => item !== email),
                count: Math.max(0, old.count - 1),
              }
            : old,
        );
      } catch {
        toast.error("לא ניתן למחוק את הנמען");
      }
    });
  }

  if (mailing.isPending) return <Loading />;
  if (mailing.isError || !mailing.data) return <ErrorState />;
  return (
    <>
      <div className="max-w-xl">
        <div className="relative">
          <Label htmlFor="search" className="sr-only">
            חיפוש נמען
          </Label>
          <Search
            className="absolute start-3 top-1/2 -translate-y-1/2 text-muted-foreground"
            size={16}
          />
          <Input
            id="search"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(0);
            }}
            placeholder="חיפוש כתובת דוא״ל"
            className="ps-10"
          />
        </div>
      </div>
      {filtered.length === 0 ? (
        <div className="mt-6 rounded-lg border bg-card p-6 text-muted-foreground">
          {search.trim() ? "לא נמצאו נמענים תואמים" : "אין נמענים עדיין"}
        </div>
      ) : (
        <>
          <div className="mt-5 hidden overflow-hidden rounded-lg border md:block">
            <Table>
              <TableHeader className="bg-muted">
                <TableRow>
                  <TableHead className="text-start">כתובת דוא״ל</TableHead>
                  <TableHead>
                    <span className="sr-only">פעולות</span>
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((email) => (
                  <TableRow key={email}>
                    <TableCell dir="ltr">{email}</TableCell>
                    <TableCell>
                      <EmailActions
                        email={email}
                        onDelete={() => handleDelete(email)}
                      />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
          <div className="mt-5 space-y-3 md:hidden">
            {rows.map((email) => (
              <div key={email} className="rounded-lg border bg-card p-4">
                <EmailActions
                  email={email}
                  onDelete={() => handleDelete(email)}
                />
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
