import { PageHeader } from "../components/page-header";
import { MailboxForm } from "../features/mailbox/mailbox-form";

export function Mailbox() {
  return (
    <>
      <PageHeader title="כתובות שליחה" />
      <MailboxForm />
    </>
  );
}
