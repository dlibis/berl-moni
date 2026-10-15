import { Button } from "./ui/button";
export function Pagination({
  page,
  count,
  setPage,
}: {
  page: number;
  count: number;
  setPage: (page: number) => void;
}) {
  const pages = Math.max(1, Math.ceil(count / 25));
  if (pages === 1) return null;
  return (
    <div className="mt-4 flex items-center gap-2 text-sm">
      <Button
        variant="outline"
        disabled={page === 0}
        onClick={() => setPage(page - 1)}
      >
        הקודם
      </Button>
      <span>
        עמוד {page + 1} מתוך {pages}
      </span>
      <Button
        variant="outline"
        disabled={page + 1 === pages}
        onClick={() => setPage(page + 1)}
      >
        הבא
      </Button>
    </div>
  );
}
