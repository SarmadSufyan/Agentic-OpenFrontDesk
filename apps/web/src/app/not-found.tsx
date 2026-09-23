import Link from "next/link";

import { Wordmark } from "@/components/brand";
import { buttonVariants } from "@/components/ui/button";

export default function NotFound() {
  return (
    <div className="grain flex min-h-screen flex-col px-5 py-8 sm:px-10">
      <Wordmark />
      <div className="m-auto max-w-md text-center">
        <p className="font-display text-8xl text-primary">404</p>
        <h1 className="mt-2 font-display text-4xl">
          This line is <span className="italic">not in service</span>.
        </h1>
        <p className="mt-3 text-muted-foreground">The page you asked for does not exist or has moved.</p>
        <div className="mt-8 flex justify-center gap-3">
          <Link href="/" className={buttonVariants({ size: "lg" })}>
            Back to home
          </Link>
          <Link href="/dashboard" className={buttonVariants({ variant: "outline", size: "lg" })}>
            Dashboard
          </Link>
        </div>
      </div>
    </div>
  );
}
