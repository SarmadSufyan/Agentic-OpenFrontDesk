"use client";

import { useEffect } from "react";

import { PageHeader } from "@/components/kit";
import { ChatPanel } from "@/components/test/chat-panel";
import { VoicePanel } from "@/components/test/voice-panel";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/lib/auth";
import { useAgent, useSaveSettings, useTenant } from "@/lib/hooks";

export default function TestPage() {
  const { workspace } = useAuth();
  const { data: agent } = useAgent();
  const { data: tenant } = useTenant();
  const save = useSaveSettings();

  // Opening the test console counts as the "test it" setup step.
  useEffect(() => {
    if (tenant && !tenant.settings?.tested_at) save({ tested_at: new Date().toISOString() }).catch(() => undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tenant?.id]);

  return (
    <>
      <PageHeader
        eyebrow="Build"
        title="Test console"
        description="Talk or chat with your receptionist exactly as a customer would. Bookings and messages it creates here are real, so you can see them flow into your dashboard and integrations."
      />
      <div className="grid gap-6 lg:grid-cols-2">
        {workspace ? (
          <ChatPanel slug={workspace.tenant_slug} greeting={agent?.greeting} />
        ) : (
          <Skeleton className="h-[560px] rounded-2xl" />
        )}
        <VoicePanel />
      </div>
    </>
  );
}
