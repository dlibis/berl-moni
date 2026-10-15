import { SignInForm } from "../features/auth/sign-in-form";
import { ForgotPasswordButton } from "../features/auth/forgot-password-button";

export function SignIn() {
  return (
    <>
      <h1 className="text-center text-xl font-semibold">כניסה</h1>
      <SignInForm />
      <ForgotPasswordButton />
    </>
  );
}
