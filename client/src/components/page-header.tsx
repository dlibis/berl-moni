export function PageHeader({
  title,
  detail,
  children,
}: {
  title: string;
  detail?: React.ReactNode;
  children?: React.ReactNode;
}) {
  if (detail) return (
    <div className="mb-8">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="min-w-0 max-w-full truncate" title={title}>{title}</h1>
        {children}
      </div>
      <div className="mt-2">{detail}</div>
    </div>
  );
  return (
    <div
      className="mb-8 flex flex-wrap items-center justify-between gap-4"
    >
      <div className="min-w-0">
        <h1 className="min-w-0 max-w-full truncate" title={title}>
          {title}
        </h1>
      </div>
      {children}
    </div>
  );
}
