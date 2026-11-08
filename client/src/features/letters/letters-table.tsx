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
import { LETTERS_PAGE_SIZE, useLetters } from "../../hooks/use-letters";
import { cn } from "../../utils/utils";
import { LetterCard } from "./letter-card";
import { LetterRow } from "./letter-row";
import type { LetterStatusFilter } from "./types";

export function LettersTable({
  status,
  search,
  page,
  setPage,
}: {
  status?: LetterStatusFilter;
  search?: string;
  page: number;
  setPage: (page: number) => void;
}) {
  const letters = useLetters({ page, status, search });
  if (letters.isError && (!letters.data || letters.isPlaceholderData)) return <ErrorState />;
  if (!letters.data) return <Loading />;
  const { items, total } = letters.data;
  return (
    <div className="relative" aria-busy={letters.isPlaceholderData}>
      <div className={cn("transition-opacity", letters.isPlaceholderData && "pointer-events-none opacity-50")}>
        {items.length === 0 ? (
          <div className="rounded-lg border bg-card p-6 text-muted-foreground">
            {status || search ? "אין פניות תואמות" : "אין פניות עדיין"}
          </div>
        ) : (
          <>
            <div className="hidden overflow-hidden rounded-lg border md:block">
              <Table className="table-fixed">
                <TableHeader className="bg-muted">
                  <TableRow>
                    <TableHead className="w-8">
                      <span className="sr-only">דורש עיון</span>
                    </TableHead>
                    <TableHead className="w-[7.5rem] text-start">תאריך</TableHead>
                    <TableHead className="w-[18%] text-start">
                      מספרי בקשה
                    </TableHead>
                    <TableHead className="text-start">משרד</TableHead>
                    <TableHead className="w-28 text-start">רלוונטי</TableHead>
                    <TableHead className="w-24 text-start">עברה</TableHead>
                    <TableHead className="w-16 px-1 text-center">דוח</TableHead>
                    <TableHead className="w-12 px-1">
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
            <Pagination
              page={page}
              count={total}
              pageSize={LETTERS_PAGE_SIZE}
              setPage={setPage}
              disabled={letters.isPlaceholderData}
            />
          </>
        )}
      </div>
    </div>
  );
}
