export function PageHeader({
  title,
  detail,
  children,
}: {
  title: string;
  detail?: React.ReactNode;
  children?: React.ReactNode;
}) {
  return (
    <div
      className={`mb-8 flex flex-wrap justify-between gap-4 ${
        detail ? "items-start" : "items-center"
      }`}
    >
      <div className="min-w-0">
        <h1 className="min-w-0 max-w-full truncate" title={title}>
          {title}
        </h1>
        {detail}
      </div>
      {children}
    </div>
  );
}
