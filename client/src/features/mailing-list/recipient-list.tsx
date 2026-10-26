import { startTransition, useOptimistic, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ErrorState } from "../../components/error-state";
import { Loading } from "../../components/loading";
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
import { useMailingList, type Mailing, type Subscriber } from "../../hooks/use-mailing-list";

export function RecipientList() {
  const [page, setPage] = useState(0);
  const mailing = useMailingList();
  const queryClient = useQueryClient();
  const [subscribers, removeSubscriber] = useOptimistic(
    mailing.data?.subscribers ?? [],
    (current, email: string) => current.filter((item) => item.email !== email),
  );
  const rows = subscribers.slice(page * 25, page * 25 + 25);

  function handleDelete(email: string) {
    startTransition(async () => {
      removeSubscriber(email);
      try {
        await write("/api/v1/mailing_list", "DELETE", { email });
        queryClient.setQueryData<Mailing>(["mailing"], (old) =>
          old
            ? {
                ...old,
                subscribers: old.subscribers.filter((item) => item.email !== email),
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
      {subscribers.length === 0 ? (
        <div className="rounded-lg border bg-card p-6 text-muted-foreground">
          אין נמענים עדיין
        </div>
      ) : (
        <>
          <div className="hidden overflow-hidden rounded-lg border md:block">
            <Table>
              <TableHeader className="bg-muted">
                <TableRow>
                  <TableHead className="text-start">שם</TableHead>
                  <TableHead className="text-start">כתובת דוא״ל</TableHead>
                  <TableHead>
                    <span className="sr-only">פעולות</span>
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((row: Subscriber) => (
                  <TableRow key={row.email}>
                    <TableCell>{row.name}</TableCell>
                    <TableCell>
                      <span dir="ltr">{row.email}</span>
                    </TableCell>
                    <TableCell>
                      <EmailActions
                        email={row.email}
                        name={row.name}
                        onDelete={() => handleDelete(row.email)}
                      />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
          <div className="space-y-3 md:hidden">
            {rows.map((row: Subscriber) => (
              <div key={row.email} className="rounded-lg border bg-card p-4">
                <EmailActions
                  email={row.email}
                  name={row.name}
                  onDelete={() => handleDelete(row.email)}
                />
                <p className="font-medium">{row.name}</p>
                <p dir="ltr" className="truncate text-sm text-muted-foreground">
                  {row.email}
                </p>
              </div>
            ))}
          </div>
          <Pagination page={page} count={subscribers.length} setPage={setPage} />
        </>
      )}
    </>
  );
}
