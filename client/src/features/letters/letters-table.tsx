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
import type { LetterStatusFilter } from "./types";

export function LettersTable({ status }: { status?: LetterStatusFilter }) {
  const [page, setPage] = useState(0);
  const letters = useLetters({ page, status });
  if (letters.isPending) return <Loading />;
  if (letters.isError) return <ErrorState />;
  const { items, total } = letters.data;
  return (
    <>
      {items.length === 0 ? (
        <div className="rounded-lg border bg-card p-6 text-muted-foreground">
          {status ? "אין מכתבים תואמים" : "אין מכתבים עדיין"}
        </div>
      ) : (
        <>
          <div className="hidden overflow-hidden rounded-lg border md:block">
            <Table className="table-fixed">
              <TableHeader className="bg-muted">
                <TableRow>
                  <TableHead className="w-[7.5rem] text-start">תאריך</TableHead>
                  <TableHead className="w-[18%] text-start">מספרי בקשה</TableHead>
                  <TableHead className="text-start">משרד</TableHead>
                  <TableHead className="w-28 text-start">סטטוס</TableHead>
                  <TableHead className="w-28 text-start">נשלח לאחרונה</TableHead>
                  <TableHead className="w-44">
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
          <div className="space-y-3 md:hidden">
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
