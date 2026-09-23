import { Wordmark } from "@/components/brand";

export function AuthShell({
  title,
  subtitle,
  children,
}: {
  title: React.ReactNode;
  subtitle: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="grid min-h-screen lg:grid-cols-[1fr_1.05fr]">
      <div className="flex flex-col px-5 py-8 sm:px-10">
        <Wordmark />
        <div className="mx-auto flex w-full max-w-sm flex-1 flex-col justify-center py-12">
          <h1 className="font-display text-[2.6rem] leading-[1.02]">{title}</h1>
          <p className="mt-2 text-muted-foreground">{subtitle}</p>
          <div className="mt-8">{children}</div>
        </div>
      </div>
      <aside className="grain relative hidden overflow-hidden bg-primary text-primary-foreground lg:flex lg:flex-col lg:justify-between lg:p-14">
        <div aria-hidden className="absolute -top-24 -right-24 size-96 rounded-full border border-primary-foreground/15" />
        <div aria-hidden className="absolute -top-8 -right-8 size-64 rounded-full border border-primary-foreground/15" />
        <p className="text-xs font-semibold tracking-[0.14em] uppercase opacity-75">OpenFrontDesk</p>
        <div>
          <p className="font-display text-5xl leading-[1.04]">
            &ldquo;Sorry, we missed your call&rdquo; is a sentence your customers <span className="italic">never</span>{" "}
            hear again.
          </p>
          <ul className="mt-10 grid gap-3 text-sm opacity-90">
            <li>Answers from your own documents, with sources.</li>
            <li>Books appointments into your hours.</li>
            <li>Sends every lead to your inbox and your tools.</li>
          </ul>
        </div>
        <p className="text-xs opacity-70">Free and open source · Apache-2.0</p>
      </aside>
    </div>
  );
}
