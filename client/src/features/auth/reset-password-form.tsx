import { FormEvent, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { ApiError, write } from "../../services/api";
import { Button } from "../../components/ui/button";
import { Field } from "../../components/field";
import { ErrorState } from "../../components/error-state";

export function ResetPasswordForm() {
  const token = useSearchParams()[0].get("token");
  const navigate = useNavigate();
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const reset = useMutation({
    mutationFn: () =>
      write("/api/auth/reset-password", "POST", {
        newPassword: password,
        token,
      }),
    onSuccess: () => {
      toast.success("הסיסמה נשמרה. אפשר להיכנס");
      navigate("/sign-in", { replace: true });
    },
  });
  if (!token || (reset.error instanceof ApiError && reset.error.status < 500))
    return (
      <div className="mt-5 space-y-4">
        <ErrorState text="הקישור אינו תקף או שפג תוקפו (15 דקות)" />
        <Link
          to="/sign-in"
          className="block text-center text-sm underline underline-offset-4"
        >
          חזרה לכניסה ובקשת קישור חדש
        </Link>
      </div>
    );
  function submit(event: FormEvent) {
    event.preventDefault();
    if (password === confirm) reset.mutate();
  }
  return (
    <form onSubmit={submit} className="mt-5 space-y-4">
      <Field
        label="סיסמה חדשה"
        type="password"
        dir="ltr"
        autoComplete="new-password"
        required
        minLength={8}
        value={password}
        onChange={(e) => setPassword(e.target.value)}
      />
      <Field
        label="אימות סיסמה"
        type="password"
        dir="ltr"
        autoComplete="new-password"
        required
        value={confirm}
        onChange={(e) => setConfirm(e.target.value)}
        error={
          confirm && confirm !== password
            ? "הסיסמאות אינן תואמות"
            : reset.isError
              ? "שירות הכניסה אינו זמין כעת"
              : undefined
        }
      />
      <Button type="submit" className="w-full" disabled={reset.isPending}>
        {reset.isPending ? "שומר…" : "שמירת סיסמה"}
      </Button>
    </form>
  );
}
