export default function PageHeader({ eyebrow, title, description, actions }) {
  return (
    <div className="px-10 py-10 border-b border-[#E4E4E1] bg-white">
      <div className="flex items-end justify-between gap-6">
        <div>
          {eyebrow && <div className="imh-eyebrow" data-testid="page-eyebrow">{eyebrow}</div>}
          <h1 className="font-editorial text-4xl sm:text-5xl leading-[1.05] mt-3 tracking-tight text-[#0A0A0A]"
              data-testid="page-title">{title}</h1>
          {description && (
            <p className="mt-3 text-[15px] text-[#52525B] max-w-2xl">{description}</p>
          )}
        </div>
        {actions && <div className="flex items-center gap-3">{actions}</div>}
      </div>
    </div>
  );
}
