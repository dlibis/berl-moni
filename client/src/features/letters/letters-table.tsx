import { useState } from "react";
import { ErrorState } from "../../components/error-state";
import { Loading } from "../../components/loading";
import { Pagination } from "../../components/pagination";
import {
  Table,
  TableBody,
  TableHead,
  TableHeader,
  TableRow,
} from "../../components/ui/table";
import { useLetters } from "../../hooks/use-letters";
import { LetterCard } from "./letter-card";
import { LetterRow } from "./letter-row";
import { StatusFilter } from "./status-filter";
import type { LetterStatusFilter } from "./types";

export function LettersTable() {
  const [page, setPage] = useState(0);
  const [status, setStatus] = useState<LetterStatusFilter>();
  const letters = useLetters({ page, status });
  if (letters.isPending) return <Loading />;
  if (letters.isError) return <ErrorState />;
  const { items, total } = letters.data;
  return (
    <>
      <StatusFilter
        value={status}
        onChange={(value) => {
          setStatus(value);
          setPage(0);
        }}
      />
      {items.length === 0 ? (
        <div className="mt-6 rounded-lg border bg-card p-6 text-muted-foreground">
          {status ? "אין מכתבים תואמים" : "אין מכתבים עדיין"}
        </div>
      ) : (
        <>
          <div className="mt-5 hidden overflow-hidden rounded-lg border md:block">
            <Table>
              <TableHeader className="bg-muted">
                <TableRow>
                  <TableHead className="text-start">תאריך</TableHead>
                  <TableHead className="text-start">מספרי בקשה</TableHead>
                  <TableHead className="text-start">משרד</TableHead>
                  <TableHead className="text-start">סטטוס</TableHead>
                  <TableHead className="text-start">נשלח לאחרונה</TableHead>
                  <TableHead>
                    <span className="sr-only">פעולות</span>
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((letter) => (
                  <LetterRow key={letter.slug} letter={letter} />
                ))}
              </TableBody>
            </Table>
          </div>
          <div className="mt-5 space-y-3 md:hidden">
            {items.map((letter) => (
              <LetterCard key={letter.slug} letter={letter} />
            ))}
          </div>
          <Pagination page={page} count={total} setPage={setPage} />
        </>
      )}
    </>
  );
}
