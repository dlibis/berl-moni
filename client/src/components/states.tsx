import { AlertCircle, LoaderCircle } from "lucide-react"
export function Loading() { return <div className="flex min-h-48 items-center justify-center text-muted-foreground"><LoaderCircle className="animate-spin" size={24} /> <span className="me-2">טוען…</span></div> }
export function ErrorState({ text = "לא ניתן לטעון את הנתונים כעת" }: { text?: string }) { return <div role="alert" className="flex items-center gap-2 rounded-md border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive"><AlertCircle size={18} />{text}</div> }
export function PageHeader({ title, children }: { title: string; children?: React.ReactNode }) { return <div className="mb-8 flex flex-wrap items-center justify-between gap-4"><h1>{title}</h1>{children}</div> }
