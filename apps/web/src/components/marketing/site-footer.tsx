import Link from "next/link";

import { Wordmark } from "@/components/brand";
import { API_URL } from "@/lib/api";
import { GITHUB_URL } from "@/lib/constants";

export function SiteFooter() {
  return (
    <footer className="border-t">
      <div className="mx-auto grid max-w-6xl gap-10 px-4 py-14 sm:px-6 md:grid-cols-[1.4fr_1fr_1fr_1fr]">
        <div>
          <Wordmark />
          <p className="mt-4 max-w-xs text-sm text-muted-foreground">
            The open-source AI receptionist. Apache-2.0 licensed, self-hostable, and free to use.
          </p>
        </div>
        <FooterCol
          title="Product"
          links={[
            { href: "/signup", label: "Create an agent" },
            { href: "/#product", label: "Features" },
            { href: "/contact", label: "Custom solutions" },
          ]}
        />
        <FooterCol
          title="Developers"
          links={[
            { href: GITHUB_URL, label: "GitHub" },
            { href: `${API_URL}/docs`, label: "API reference" },
            { href: `${GITHUB_URL}/tree/main/integrations/n8n`, label: "n8n templates" },
          ]}
        />
        <FooterCol
          title="Account"
          links={[
            { href: "/login", label: "Sign in" },
            { href: "/signup", label: "Sign up" },
            { href: "/dashboard", label: "Dashboard" },
          ]}
        />
      </div>
      <div className="border-t">
        <p className="mx-auto max-w-6xl px-4 py-5 text-xs text-muted-foreground sm:px-6">
          OpenFrontDesk is an open-source project. Built with LiveKit, Groq, Kokoro, pgvector and FastAPI.
        </p>
      </div>
    </footer>
  );
}

function FooterCol({ title, links }: { title: string; links: { href: string; label: string }[] }) {
  return (
    <div>
      <p className="mb-3 text-xs font-semibold tracking-[0.14em] uppercase">{title}</p>
      <ul className="grid gap-2 text-sm text-muted-foreground">
        {links.map((l) => (
          <li key={l.label}>
            {l.href.startsWith("http") ? (
              <a href={l.href} target="_blank" rel="noreferrer" className="hover:text-foreground">
                {l.label}
              </a>
            ) : (
              <Link href={l.href} className="hover:text-foreground">
                {l.label}
              </Link>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
