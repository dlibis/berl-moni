import { useEffect, useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { onUnauthenticated } from "../lib/api";
import { AppLayout } from "./layout";
import { NotSignedIn } from "./not-signed-in";
import { Home } from "../screens/home";
import { Programs } from "../screens/programs";
import { MailingList } from "../screens/mailing-list";
import { Schedule } from "../screens/schedule";
import { Mailbox } from "../screens/mailbox";

export function RoutesView() {
  const [signedOut, setSignedOut] = useState(false);
  useEffect(() => onUnauthenticated(() => setSignedOut(true)), []);
  if (signedOut) return <NotSignedIn />;
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route path="/" element={<Home />} />
        <Route path="/programs" element={<Programs />} />
        <Route path="/mailing-list" element={<MailingList />} />
        <Route path="/schedule" element={<Schedule />} />
        <Route path="/mailbox" element={<Mailbox />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
