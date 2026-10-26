import { PageHeader } from "../components/page-header";
import { AddRecipientButton } from "../features/mailing-list/add-recipient-button";
import { RecipientList } from "../features/mailing-list/recipient-list";

export function MailingList() {
  return (
    <>
      <PageHeader title="רשימת תפוצה">
        <AddRecipientButton />
      </PageHeader>
      <RecipientList />
    </>
  );
}
