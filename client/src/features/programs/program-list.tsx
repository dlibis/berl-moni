import { useMemo, useState } from "react";
import { Search } from "lucide-react";
import { ErrorState } from "../../components/error-state";
import { Loading } from "../../components/loading";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import {
  Table,
  TableBody,
  TableHead,
  TableHeader,
  TableRow,
} from "../../components/ui/table";
import { Pagination } from "../../components/pagination";
import { ProgramActions } from "./program-actions";
import { ProgramRow } from "./program-row";
import { usePrograms } from "../../hooks/use-programs";

export function ProgramList() {
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);
  const programs = usePrograms();
  const filtered = useMemo(
    () =>
      (programs.data?.programs ?? []).filter((p) =>
        `${p.code} ${p.name}`.includes(search.trim()),
      ),
    [programs.data, search],
  );
  const rows = filtered.slice(page * 25, page * 25 + 25);
  if (programs.isPending) return <Loading />;
  if (programs.isError) return <ErrorState />;
  return (
    <>
      <div className="max-w-xl">
        <div className="relative">
          <Label htmlFor="search" className="sr-only">
            חיפוש תוכנית
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
            placeholder="חיפוש לפי קוד או שם"
            className="ps-10"
          />
        </div>
      </div>
      {filtered.length === 0 ? (
        <div className="mt-6 rounded-lg border bg-card p-6 text-muted-foreground">
          {search.trim() ? "לא נמצאו תוכניות תואמות" : "אין תוכניות עדיין"}
        </div>
      ) : (
        <>
          <div className="mt-5 hidden overflow-hidden rounded-lg border md:block">
            <Table>
              <TableHeader className="bg-muted">
                <TableRow>
                  <TableHead className="text-start">קוד</TableHead>
                  <TableHead className="text-start">שם</TableHead>
                  <TableHead>
                    <span className="sr-only">פעולות</span>
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((program) => (
                  <ProgramRow key={program.code} program={program} />
                ))}
              </TableBody>
            </Table>
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
