import { FormEvent, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ApiError, write } from "../../services/api";
import { Button } from "../../components/ui/button";
import { Field } from "../../components/field";

export function SignInForm() {
  const queryClient = useQueryClient();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const signIn = useMutation({
    mutationFn: () =>
      write("/api/auth/sign-in/email", "POST", {
        email: email.trim(),
        password,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["session"] }),
  });
  function submit(event: FormEvent) {
    event.preventDefault();
    signIn.mutate();
  }
  const error =
    signIn.error instanceof ApiError && signIn.error.status < 500
      ? "דוא״ל או סיסמה שגויים"
      : signIn.error
        ? "שירות הכניסה אינו זמין כעת"
        : undefined;
  return (
    <form onSubmit={submit} className="mt-5 space-y-4">
      <Field
        label="כתובת דוא״ל"
        type="email"
        dir="ltr"
        autoComplete="username"
        required
        value={email}
        onChange={(e) => setEmail(e.target.value)}
      />
      <Field
        label="סיסמה"
        type="password"
        dir="ltr"
        autoComplete="current-password"
        required
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        error={error}
      />
      <Button type="submit" className="w-full" disabled={signIn.isPending}>
        {signIn.isPending ? "נכנסים…" : "כניסה"}
      </Button>
    </form>
  );
}
