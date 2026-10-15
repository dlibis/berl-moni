import { useEffect, useState } from "react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { Navigate, Route, Routes } from "react-router-dom"
import { Toaster } from "sonner"
import { onUnauthenticated } from "./lib/api"
import { AppLayout } from "./components/layout"
import { Home } from "./screens/home"
import { Programs } from "./screens/programs"
import { MailingList } from "./screens/mailing-list"
import { Schedule } from "./screens/schedule"
import { Mailbox } from "./screens/mailbox"

const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
function NotSignedIn() { return <main className="flex min-h-screen items-center justify-center p-4"><section className="max-w-sm rounded-lg border bg-card p-6 text-center shadow-sm"><h1 className="text-xl font-semibold">לא מחוברים</h1><p className="mt-3 text-sm text-muted-foreground">יש להתחבר כדי לצפות במערכת.</p></section></main> }
function RoutesView() { const [signedOut, setSignedOut] = useState(false); useEffect(() => onUnauthenticated(() => setSignedOut(true)), []); if (signedOut) return <NotSignedIn />; return <Routes><Route element={<AppLayout />}><Route path="/" element={<Home />} /><Route path="/programs" element={<Programs />} /><Route path="/mailing-list" element={<MailingList />} /><Route path="/schedule" element={<Schedule />} /><Route path="/mailbox" element={<Mailbox />} /></Route><Route path="*" element={<Navigate to="/" replace />} /></Routes> }
export function App() { return <QueryClientProvider client={queryClient}><RoutesView /><Toaster position="bottom-left" visibleToasts={2} duration={5000} closeButton richColors /></QueryClientProvider> }
