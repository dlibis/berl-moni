import { useMailingList } from "./use-mailing-list";

export function RecipientCount() {
  const mailing = useMailingList();
  if (!mailing.data) return null;
  return (
    <>
      <p className="mb-4 text-sm">
        {mailing.data.count} / {mailing.data.cap} נמענים
      </p>
      {mailing.data.count >= mailing.data.cap ? (
        <p className="mb-4 text-sm text-muted-foreground">
          הגעת למכסה הנגזרת ממגבלת השליחה היומית של Resend.
        </p>
      ) : null}
    </>
  );
}
