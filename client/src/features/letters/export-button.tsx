import { Download } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { Button } from "../../components/ui/button";

export function ExportButton() {
  const [loading, setLoading] = useState(false);
  async function exportXlsx() {
    setLoading(true);
    try {
      const response = await fetch("/api/v1/letters/export", { credentials: "include" });
      if (response.status === 401) {
        toast.error("יש להתחבר מחדש");
        return;
      }
      if (!response.ok) {
        toast.error("לא ניתן לייצא את הקובץ");
        return;
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "letters.xlsx";
      link.click();
      URL.revokeObjectURL(url);
    } catch {
      toast.error("לא ניתן לייצא את הקובץ");
    } finally {
      setLoading(false);
    }
  }
  return (
    <Button variant="outline" disabled={loading} onClick={() => exportXlsx()}>
      <Download size={16} />
      {loading ? "מייצא…" : "ייצוא Excel"}
    </Button>
  );
}
