import { useMemo, useState } from "react";
import { Search } from "lucide-react";
import { ErrorState } from "../../components/error-state";
import { Loading } from "../../components/loading";
import { Pagination } from "../../components/pagination";
import { EmailActions } from "./email-actions";
import { useMailingList } from "../../hooks/use-mailing-list";

export function RecipientList() {
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);
  const mailing = useMailingList();
  const filtered = useMemo(
    () => (mailing.data?.emails ?? []).filter((email) => email.includes(search.trim().toLowerCase())),
    [mailing.data, search],
  );
  const rows = filtered.slice(page * 25, page * 25 + 25);
  if (mailing.isPending) return <Loading />;
  if (mailing.isError || !mailing.data) return <ErrorState />;
  return (
    <>
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
                      <EmailActions email={email} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-5 space-y-3 md:hidden">
            {rows.map((email) => (
              <div key={email} className="rounded-lg border bg-card p-4">
                <EmailActions email={email} />
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
