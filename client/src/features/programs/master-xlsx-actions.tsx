import { Download, Upload } from "lucide-react";
import { useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Button } from "../../components/ui/button";

export function MasterXlsxActions() {
  const input = useRef<HTMLInputElement>(null);
  const queryClient = useQueryClient();
  const [loading, setLoading] = useState<"up" | "down" | null>(null);

  async function download() {
    setLoading("down");
    try {
      const response = await fetch("/api/v1/master/download", { credentials: "include" });
      if (!response.ok) {
        toast.error("לא ניתן להוריד את הקובץ");
        return;
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "master.xlsx";
      link.click();
      URL.revokeObjectURL(url);
    } catch {
      toast.error("לא ניתן להוריד את הקובץ");
    } finally {
      setLoading(null);
    }
  }

  async function upload(file: File) {
    setLoading("up");
    try {
      const body = new FormData();
      body.append("file", file);
      const response = await fetch("/api/v1/master/upload", {
        method: "POST",
        credentials: "include",
        body,
      });
      const data = (await response.json().catch(() => ({}))) as { error?: string };
      if (!response.ok) {
        toast.error(data.error ?? "קובץ לא תקין");
        return;
      }
      toast.success("רשימת התוכניות עודכנה");
      queryClient.invalidateQueries({ queryKey: ["programs"] });
    } catch {
      toast.error("לא ניתן להעלות את הקובץ");
    } finally {
      setLoading(null);
      if (input.current) input.current.value = "";
    }
  }

  return (
    <>
      <input
        ref={input}
        type="file"
        accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) upload(file);
        }}
      />
      <Button variant="outline" disabled={loading !== null} onClick={() => download()}>
        <Download size={16} />
        {loading === "down" ? "מוריד…" : "הורדה"}
      </Button>
      <Button variant="outline" disabled={loading !== null} onClick={() => input.current?.click()}>
        <Upload size={16} />
        {loading === "up" ? "מעלה…" : "העלאה"}
      </Button>
    </>
  );
}
