"use client";

import { CodeIcon, EyeIcon, EyeOffIcon, MessageCircleIcon, PhoneIcon, WorkflowIcon } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { CodeBlock, PageHeader, Panel } from "@/components/kit";
import { Button, buttonVariants } from "@/components/ui/button";
import { API_URL } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useSaveSettings, useTenant } from "@/lib/hooks";
import { cn } from "@/lib/utils";

const SWATCHES = ["#0f766e", "#1d4ed8", "#7c3aed", "#be123c", "#c2410c", "#15803d", "#0f172a"];
const HEX = /^#[0-9a-f]{6}$/i;

function removeWidget() {
  document.querySelectorAll(".ofd-btn, .ofd-panel, script[data-ofd-preview]").forEach((el) => el.remove());
  document.querySelectorAll("style").forEach((s) => {
    if (s.textContent?.includes(".ofd-btn")) s.remove();
  });
}

export default function DeployPage() {
  const { workspace } = useAuth();
  const { data: tenant } = useTenant();
  const save = useSaveSettings();
  const stored = typeof tenant?.settings?.widget_color === "string" ? tenant.settings.widget_color : null;
  const [picked, setPicked] = useState<string | null>(null);
  const color = picked ?? stored ?? SWATCHES[0];
  const [preview, setPreview] = useState(false);
  const slug = workspace?.tenant_slug ?? "your-business";

  const snippet = `<script src="${API_URL}/widget.js"\n        data-agent="${slug}"\n        data-color="${color}"></script>`;

  // Inject the real widget into this page for a live preview; re-inject when the color changes.
  useEffect(() => {
    if (!preview || !workspace) return;
    removeWidget();
    const s = document.createElement("script");
    s.src = `${API_URL}/widget.js`;
    s.dataset.agent = workspace.tenant_slug;
    s.dataset.color = color;
    s.dataset.ofdPreview = "1";
    document.body.appendChild(s);
    return removeWidget;
  }, [preview, color, workspace]);

  async function persistColor(c: string) {
    setPicked(c);
    if (!HEX.test(c)) return;
    try {
      await save({ widget_color: c });
    } catch {
      /* the snippet still reflects the choice; saving is a convenience */
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="Build"
        title="Deploy"
        description="Put your receptionist wherever your customers are. Everything uses the same knowledge and settings."
      />

      <div className="grid gap-6 lg:grid-cols-[1.25fr_1fr]">
        <Panel
          title={
            <span className="flex items-center gap-2">
              <CodeIcon className="size-4 text-primary" /> Website chat widget
            </span>
          }
          description="Paste this just before the closing </body> tag on every page where the chat should appear."
        >
          <CodeBlock code={snippet} />
          <div className="mt-5 flex flex-wrap items-center gap-3">
            <span className="text-sm text-muted-foreground">Brand color</span>
            <div className="flex flex-wrap gap-1.5">
              {SWATCHES.map((c) => (
                <button
                  key={c}
                  type="button"
                  aria-label={`Use ${c}`}
                  onClick={() => persistColor(c)}
                  className={cn(
                    "size-7 rounded-full border-2 transition-transform hover:scale-110",
                    c === color ? "border-foreground" : "border-transparent",
                  )}
                  style={{ background: c }}
                />
              ))}
              <label className="relative size-7 cursor-pointer overflow-hidden rounded-full border" title="Custom color">
                <input
                  type="color"
                  value={HEX.test(color) ? color : "#0f766e"}
                  onChange={(e) => persistColor(e.target.value)}
                  className="absolute -inset-2 size-12 cursor-pointer"
                  aria-label="Custom color"
                />
              </label>
            </div>
          </div>
          <div className="mt-6 flex flex-wrap gap-2 border-t pt-5">
            <Button variant={preview ? "secondary" : "default"} onClick={() => setPreview((p) => !p)}>
              {preview ? <EyeOffIcon /> : <EyeIcon />}
              {preview ? "Hide preview" : "Preview on this page"}
            </Button>
            <Button
              variant="outline"
              onClick={async () => {
                try {
                  await navigator.clipboard.writeText(snippet);
                  await save({ widget_copied_at: new Date().toISOString() });
                  toast.success("Snippet copied. Paste it into your website.");
                } catch {
                  toast.error("Could not copy automatically. Select the code and copy it.");
                }
              }}
            >
              Copy snippet
            </Button>
          </div>
          {preview && (
            <p className="mt-3 text-sm text-muted-foreground">
              The chat bubble is now in the bottom-right corner of this page. It is the live widget, talking to your
              receptionist.
            </p>
          )}
        </Panel>

        <div className="grid content-start gap-6">
          <Channel
            icon={PhoneIcon}
            title="Phone number"
            status="At go-live"
            body="Connect a Telnyx or Twilio number and calls ring straight through to your receptionist. Until then, test voice in the browser."
            action={
              <Link href="/dashboard/test" className={cn(buttonVariants({ variant: "outline", size: "sm" }))}>
                Test voice now
              </Link>
            }
          />
          <Channel
            icon={MessageCircleIcon}
            title="WhatsApp"
            status="Template ready"
            body="Answer WhatsApp messages with the same receptionist using the ready-made n8n workflow, or let us set it up for you."
            action={
              <Link href="/contact?need=whatsapp" className={cn(buttonVariants({ variant: "outline", size: "sm" }))}>
                Get it set up
              </Link>
            }
          />
          <Channel
            icon={WorkflowIcon}
            title="Your tools"
            status="Available"
            body="Send leads, bookings and call transcripts to Sheets, Slack, a CRM or email with webhooks and the REST API."
            action={
              <Link href="/dashboard/integrations" className={cn(buttonVariants({ variant: "outline", size: "sm" }))}>
                Open integrations
              </Link>
            }
          />
        </div>
      </div>
    </>
  );
}

function Channel({
  icon: Icon,
  title,
  status,
  body,
  action,
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  status: string;
  body: string;
  action: React.ReactNode;
}) {
  return (
    <div className="rounded-2xl border bg-card p-5">
      <div className="flex items-center gap-3">
        <div className="grid size-9 place-items-center rounded-lg bg-accent text-accent-foreground">
          <Icon className="size-4" />
        </div>
        <p className="font-semibold">{title}</p>
        <span className="ml-auto rounded-full bg-secondary px-2.5 py-0.5 text-xs text-muted-foreground">{status}</span>
      </div>
      <p className="mt-3 text-sm text-muted-foreground">{body}</p>
      <div className="mt-4">{action}</div>
    </div>
  );
}
