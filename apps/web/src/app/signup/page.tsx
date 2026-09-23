"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { AuthShell } from "@/components/auth-shell";
import { ErrorNote, Field } from "@/components/kit";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/lib/auth";

export default function SignupPage() {
  const { signup, status } = useAuth();
  const router = useRouter();
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const [justSignedUp, setJustSignedUp] = useState(false);

  // Fresh accounts go to onboarding; someone already signed in goes to their dashboard.
  useEffect(() => {
    if (status === "authed") router.replace(justSignedUp ? "/onboarding" : "/dashboard");
  }, [status, justSignedUp, router]);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    const password = String(form.get("password"));
    if (password.length < 8) {
      setError(new Error("Use at least 8 characters for your password."));
      return;
    }
    setBusy(true);
    setError(null);
    setJustSignedUp(true);
    try {
      await signup({
        name: String(form.get("name")).trim() || undefined,
        business_name: String(form.get("business")).trim() || undefined,
        email: String(form.get("email")).trim(),
        password,
      });
    } catch (err) {
      setJustSignedUp(false);
      setError(err);
      setBusy(false);
    }
  }

  return (
    <AuthShell
      title={
        <>
          Your receptionist,
          <br />
          <span className="italic">ready in minutes</span>
        </>
      }
      subtitle="Free forever. No credit card needed."
    >
      <form onSubmit={onSubmit} className="grid gap-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Your name" htmlFor="name">
            <Input id="name" name="name" autoComplete="name" className="h-10" />
          </Field>
          <Field label="Business name" htmlFor="business">
            <Input id="business" name="business" autoComplete="organization" required className="h-10" />
          </Field>
        </div>
        <Field label="Work email" htmlFor="email">
          <Input id="email" name="email" type="email" autoComplete="email" required className="h-10" />
        </Field>
        <Field label="Password" htmlFor="password" hint="At least 8 characters.">
          <Input id="password" name="password" type="password" autoComplete="new-password" required className="h-10" />
        </Field>
        <ErrorNote error={error} />
        <Button type="submit" size="lg" className="h-10" disabled={busy}>
          {busy ? "Creating your workspace..." : "Create account"}
        </Button>
        <p className="text-sm text-muted-foreground">
          Already have an account?{" "}
          <Link href="/login" className="font-medium text-primary underline-offset-4 hover:underline">
            Sign in
          </Link>
        </p>
      </form>
    </AuthShell>
  );
}
