import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Navigate, Route, Routes } from "react-router-dom";
import { onUnauthenticated } from "../services/api";
import { useSession } from "../hooks/use-session";
import { AppLayout } from "../layouts/app-layout";
import { AuthLayout } from "../layouts/auth-layout";
import { Loading } from "./loading";
import { ErrorState } from "./error-state";
import { Home } from "../pages/home";
import { Programs } from "../pages/programs";
import { MailingList } from "../pages/mailing-list";
import { Schedule } from "../pages/schedule";
import { Mailbox } from "../pages/mailbox";
import { SignIn } from "../pages/sign-in";
import { ForgotPassword } from "../pages/forgot-password";
import { ResetPassword } from "../pages/reset-password";

export function RoutesView() {
  const queryClient = useQueryClient();
  const session = useSession();
  useEffect(
    () => onUnauthenticated(() => queryClient.setQueryData(["session"], null)),
    [queryClient],
  );
  if (session.isPending) return <Loading />;
  if (session.isError) return <ErrorState text="שירות הכניסה אינו זמין כעת" />;
  return (
    <Routes>
      <Route element={<AuthLayout />}>
        <Route path="/reset-password" element={<ResetPassword />} />
        {session.data ? null : (
          <>
            <Route path="/sign-in" element={<SignIn />} />
            <Route path="/forgot-password" element={<ForgotPassword />} />
          </>
        )}
      </Route>
      {session.data ? (
        <Route element={<AppLayout />}>
          <Route path="/" element={<Home />} />
          <Route path="/programs" element={<Programs />} />
          <Route path="/mailing-list" element={<MailingList />} />
          <Route path="/schedule" element={<Schedule />} />
          <Route path="/mailbox" element={<Mailbox />} />
        </Route>
      ) : null}
      <Route
        path="*"
        element={<Navigate to={session.data ? "/" : "/sign-in"} replace />}
      />
    </Routes>
  );
}
