import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Micro Habit Coach",
  description: "Tiny habits at the right time.",
};

export default function AppLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <>
      <header className="border-b border-rim bg-white">
        <div className="mx-auto flex max-w-3xl items-center px-6 py-4">
          <Link
            href="/"
            className="text-sm font-semibold tracking-tight text-ink hover:text-accent transition-colors"
          >
            Micro Habit Coach
          </Link>
          <nav className="ml-auto flex items-center gap-6">
            <Link href="/home" className="text-sm text-ink-muted hover:text-ink transition-colors">
              Today
            </Link>
            <Link href="/habits" className="text-sm text-ink-muted hover:text-ink transition-colors">
              Habits
            </Link>
            <Link href="/history" className="text-sm text-ink-muted hover:text-ink transition-colors">
              History
            </Link>
            <Link href="/schedule" className="text-sm text-ink-muted hover:text-ink transition-colors">
              Schedule
            </Link>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-3xl px-6 py-10">{children}</main>
    </>
  );
}
