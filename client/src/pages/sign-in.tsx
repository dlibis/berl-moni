import { SignInForm } from "../features/auth/sign-in-form";
import { Link } from "react-router-dom";

export function SignIn() {
  return (
    <>
      <h1 className="text-center text-xl font-semibold">כניסה</h1>
      <SignInForm />
      <Link
        to="/forgot-password"
        className="mt-4 block text-center text-sm underline-offset-4 hover:underline"
      >
        שכחתי סיסמה
      </Link>
    </>
  );
}
