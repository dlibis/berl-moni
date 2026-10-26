import { RefreshCw } from "lucide-react";
import { Button } from "../../components/ui/button";
import { useRefreshLetters } from "../../hooks/use-refresh-letters";

export function RefreshButton() {
  const refresh = useRefreshLetters();
  return (
    <Button
      variant="outline"
      disabled={refresh.isPending}
      onClick={() => refresh.mutate()}
    >
      <RefreshCw size={16} className="me-2" />
      {refresh.isPending ? "מרענן…" : "רענון פניות"}
    </Button>
  );
}
