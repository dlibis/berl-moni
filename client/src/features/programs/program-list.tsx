import { useMemo, useState } from "react";
import { Search } from "lucide-react";
import { ErrorState } from "../../components/error-state";
import { Loading } from "../../components/loading";
import { Pagination } from "../../components/pagination";
import { ProgramActions } from "./program-actions";
import { ProgramRow } from "./program-row";
import { usePrograms } from "./use-programs";

export function ProgramList() {
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);
  const programs = usePrograms();
  const filtered = useMemo(
    () => (programs.data?.programs ?? []).filter((p) => `${p.code} ${p.name}`.includes(search.trim())),
    [programs.data, search],
  );
  const rows = filtered.slice(page * 25, page * 25 + 25);
  if (programs.isPending) return <Loading />;
  if (programs.isError) return <ErrorState />;
  return (
    <>
      <div className="max-w-xl">
        <label className="relative block">
          <span className="sr-only">חיפוש תוכנית</span>
          <Search className="absolute right-3 top-3 text-muted-foreground" size={18} />
          <input
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(0);
            }}
            placeholder="חיפוש לפי קוד או שם"
            className="h-12 w-full rounded-md border bg-background ps-10 pe-3 text-sm outline-none focus:ring-2 focus:ring-ring lg:h-10"
          />
        </label>
      </div>
      {filtered.length === 0 ? (
        <div className="mt-6 rounded-lg border bg-card p-6 text-muted-foreground">אין תוכניות עדיין</div>
      ) : (
        <>
          <div className="mt-5 hidden overflow-hidden rounded-lg border md:block">
            <table className="w-full text-sm">
              <thead className="bg-muted text-start">
                <tr>
                  <th className="p-3 text-start font-semibold">קוד</th>
                  <th className="p-3 text-start font-semibold">שם</th>
                  <th className="p-3 text-start">
                    <span className="sr-only">פעולות</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {rows.map((program) => (
                  <ProgramRow key={program.code} program={program} />
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-5 space-y-3 md:hidden">
            {rows.map((program) => (
              <div key={program.code} className="rounded-lg border bg-card p-4">
                <ProgramActions program={program} />
                <p className="font-mono text-sm">{program.code}</p>
                <p className="mt-1 truncate" title={program.name}>
                  {program.name}
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
