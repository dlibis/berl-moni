import { FormEvent, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { write } from "../../services/api";
import { Button } from "../../components/ui/button";
import { Field } from "../../components/field";

export function ForgotPasswordForm() {
  const [email, setEmail] = useState("");
  const request = useMutation({
    mutationFn: () =>
      write("/api/auth/request-password-reset", "POST", {
        email: email.trim(),
        redirectTo: `${location.origin}/reset-password`,
      }),
  });
  function submit(event: FormEvent) {
    event.preventDefault();
    request.mutate();
  }
  const backLink = (
    <Link
      to="/sign-in"
      className="block text-center text-sm underline-offset-4 hover:underline"
    >
      חזרה לכניסה
    </Link>
  );
  if (request.isSuccess)
    return (
      <div className="mt-5 space-y-4 text-center">
        <p>
          אם <span dir="ltr">{email.trim()}</span> רשומה במערכת, נשלח אליה קישור
          לאיפוס הסיסמה. הקישור תקף ל־15 דקות.
        </p>
        <p className="text-sm text-muted-foreground">
          לא הגיע? כדאי לבדוק בתיקיית הספאם.
        </p>
        {backLink}
      </div>
    );
  return (
    <form onSubmit={submit} className="mt-5 space-y-4">
      <p className="text-center text-sm text-muted-foreground">
        נשלח לך קישור לבחירת סיסמה חדשה
      </p>
      <Field
        label="כתובת דוא״ל"
        type="email"
        dir="ltr"
        autoComplete="username"
        autoFocus
        required
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        error={request.isError ? "לא ניתן לשלוח קישור כעת" : undefined}
      />
      <Button type="submit" className="w-full" disabled={request.isPending}>
        {request.isPending ? "שולח…" : "שליחת קישור"}
      </Button>
      {backLink}
    </form>
  );
}
