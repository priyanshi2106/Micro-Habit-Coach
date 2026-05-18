"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getUserId } from "@/lib/utils/userId";

// ── Static data ──────────────────────────────────────────────────────────────

const STEPS = [
  {
    n: "01",
    title: "Add your schedule",
    body: "Tell us which days and times you're actually free. We never suggest a habit outside your available window.",
  },
  {
    n: "02",
    title: "Choose your habits",
    body: "Pick from 14 curated templates across 7 categories, or write your own. Setup takes under two minutes.",
  },
  {
    n: "03",
    title: "Get one suggestion for today",
    body: "Each day we surface a single habit at the right moment. No list. No decisions. Just show up.",
  },
];

const BENEFITS = [
  {
    title: "Less decision fatigue",
    body: "You don't choose from a list every morning. We choose for you — one habit, one time, done.",
  },
  {
    title: "Built around your real week",
    body: "Suggestions are matched to your schedule. Mindfulness in the morning, movement in the evening — automatically.",
  },
  {
    title: "Progress you can see",
    body: "A streak counter, weekly summary, and full log history make momentum visible without turning misses into failures.",
  },
];

const FEATURES = [
  {
    label: "Habit templates",
    detail: "14 ready-made habits across 7 categories — customize any of them.",
  },
  {
    label: "Schedule-aware suggestions",
    detail: "We match habit categories to your actual free blocks by day and time.",
  },
  {
    label: "Done · Snooze · Skip",
    detail: "Three honest actions per day. Snooze keeps the streak alive if you need more time.",
  },
  {
    label: "Weekly summary + streaks",
    detail: "See your done/skipped/snoozed counts and your current consecutive-day streak.",
  },
  {
    label: "History view",
    detail: "Every log entry, grouped by date, with status badges and time windows.",
  },
];

// ── Subtle product mock — shown in hero ──────────────────────────────────────

function SuggestionMock() {
  return (
    <div className="w-full max-w-xs rounded-2xl border border-rim bg-white shadow-sm">
      {/* card header */}
      <div className="flex items-center justify-between border-b border-rim px-5 py-3.5">
        <span className="text-xs font-semibold uppercase tracking-widest text-ink-subtle">
          Today
        </span>
        <span className="rounded-md bg-accent-light px-2 py-0.5 text-xs font-semibold text-accent">
          movement
        </span>
      </div>

      {/* card body */}
      <div className="px-5 py-5">
        <p className="text-xl font-semibold tracking-tight text-ink">
          Morning walk
        </p>
        <p className="mt-1 text-sm text-ink-muted">
          7:00 AM
          <span className="mx-1.5 text-ink-subtle">–</span>
          7:10 AM
        </p>
        <blockquote className="mt-4 border-l-2 border-rim pl-3 text-xs leading-relaxed text-ink-subtle">
          Matched to your Monday free block — 10 min fits your preference.
        </blockquote>
      </div>

      {/* card actions */}
      <div className="flex gap-2 border-t border-rim px-5 py-4">
        <button className="flex-1 rounded-lg bg-accent px-3 py-2 text-xs font-semibold text-white">
          Mark done
        </button>
        <button className="rounded-lg border border-rim px-3 py-2 text-xs font-medium text-ink-muted">
          Snooze
        </button>
        <button className="rounded-lg border border-rim px-3 py-2 text-xs font-medium text-ink-muted">
          Skip
        </button>
      </div>
    </div>
  );
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function LandingPage() {
  const [mounted, setMounted] = useState(false);
  const [signedIn, setSignedIn] = useState(false);

  useEffect(() => {
    setMounted(true);
    setSignedIn(!!getUserId());
  }, []);

  return (
    <div className="min-h-screen bg-canvas">

      {/* ── Navbar ──────────────────────────────────────────────────────── */}
      <header className="border-b border-rim bg-white">
        <div className="mx-auto flex max-w-4xl items-center px-6 py-4">
          <span className="text-sm font-semibold tracking-tight text-ink">
            Micro Habit Coach
          </span>
          <nav className="ml-auto flex items-center gap-6">
            {mounted && signedIn && (
              <>
                <Link href="/home" className="text-sm text-ink-muted transition-colors hover:text-ink">
                  Today
                </Link>
                <Link href="/habits" className="text-sm text-ink-muted transition-colors hover:text-ink">
                  Habits
                </Link>
              </>
            )}
            <Link
              href="/onboarding"
              className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-accent-hover"
            >
              {mounted && signedIn ? "Open app" : "Get started"}
            </Link>
          </nav>
        </div>
      </header>

      {/* ── Hero ────────────────────────────────────────────────────────── */}
      <section className="mx-auto max-w-4xl px-6 pb-24 pt-20">
        <div className="flex flex-col items-start gap-16 lg:flex-row lg:items-center">

          {/* left — copy */}
          <div className="flex-1">
            <p className="mb-5 text-xs font-semibold uppercase tracking-widest text-accent">
              Micro Habit Coach
            </p>
            <h1 className="text-5xl font-semibold leading-[1.1] tracking-tight text-ink sm:text-6xl">
              One habit.
              <br />
              The right time.
            </h1>
            <p className="mt-6 max-w-md text-lg leading-relaxed text-ink-muted">
              Build habits that fit real life, without needing a perfect routine
              first.
            </p>
            <p className="mt-3 max-w-md text-sm leading-relaxed text-ink-subtle">
              Add your schedule, choose a few habits, and get one realistic
              suggestion you can actually do today.
            </p>
            <div className="mt-10 flex flex-wrap items-center gap-3">
              <Link
                href="/onboarding"
                className="rounded-lg bg-accent px-6 py-3 text-sm font-medium text-white transition-colors hover:bg-accent-hover"
              >
                Get started — it takes 2 minutes
              </Link>
              {mounted && signedIn && (
                <Link
                  href="/home"
                  className="rounded-lg border border-rim bg-white px-6 py-3 text-sm font-medium text-ink transition-colors hover:bg-stone-50"
                >
                  Go to app
                </Link>
              )}
            </div>
          </div>

          {/* right — product mock */}
          <div className="flex w-full justify-center lg:w-auto lg:justify-end">
            <SuggestionMock />
          </div>

        </div>
      </section>

      <div className="border-t border-rim" />

      {/* ── How it works ────────────────────────────────────────────────── */}
      <section className="bg-white">
        <div className="mx-auto max-w-4xl px-6 py-20">
          <p className="mb-14 text-xs font-semibold uppercase tracking-widest text-ink-subtle">
            How it works
          </p>

          <div className="grid gap-0 sm:grid-cols-3">
            {STEPS.map((s, i) => (
              <div key={s.n} className="relative">
                {/* connector line between steps */}
                {i < STEPS.length - 1 && (
                  <div className="absolute left-full top-4 hidden h-px w-full -translate-x-1/2 border-t border-dashed border-rim sm:block" />
                )}
                <div className="pr-10">
                  <div className="mb-4 flex items-center gap-3">
                    <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-rim bg-canvas text-xs font-semibold text-ink-muted">
                      {s.n}
                    </span>
                    <div className="h-px flex-1 bg-rim sm:hidden" />
                  </div>
                  <p className="mb-2 text-sm font-semibold text-ink">{s.title}</p>
                  <p className="text-sm leading-relaxed text-ink-muted">{s.body}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <div className="border-t border-rim" />

      {/* ── Why it works ────────────────────────────────────────────────── */}
      <section className="mx-auto max-w-4xl px-6 py-20">
        <p className="mb-14 text-xs font-semibold uppercase tracking-widest text-ink-subtle">
          Why it works
        </p>
        <div className="grid gap-10 sm:grid-cols-3">
          {BENEFITS.map((b) => (
            <div key={b.title}>
              <div className="mb-4 h-0.5 w-10 bg-accent" />
              <p className="mb-2 text-base font-semibold tracking-tight text-ink">
                {b.title}
              </p>
              <p className="text-sm leading-relaxed text-ink-muted">{b.body}</p>
            </div>
          ))}
        </div>
      </section>

      <div className="border-t border-rim" />

      {/* ── Feature snapshot ────────────────────────────────────────────── */}
      <section className="bg-white">
        <div className="mx-auto max-w-4xl px-6 py-20">
          <div className="flex flex-col gap-10 sm:flex-row sm:items-start sm:gap-16">

            {/* left — label */}
            <div className="shrink-0 sm:w-40">
              <p className="text-xs font-semibold uppercase tracking-widest text-ink-subtle">
                What's included
              </p>
            </div>

            {/* right — feature list */}
            <ul className="flex flex-1 flex-col divide-y divide-rim">
              {FEATURES.map((f) => (
                <li key={f.label} className="flex items-baseline gap-4 py-4 first:pt-0 last:pb-0">
                  <span className="mt-0.5 shrink-0 text-accent">✦</span>
                  <div>
                    <p className="text-sm font-semibold text-ink">{f.label}</p>
                    <p className="mt-0.5 text-xs leading-relaxed text-ink-muted">
                      {f.detail}
                    </p>
                  </div>
                </li>
              ))}
            </ul>

          </div>
        </div>
      </section>

      <div className="border-t border-rim" />

      {/* ── Final CTA ───────────────────────────────────────────────────── */}
      <section className="mx-auto max-w-4xl px-6 py-28">
        <div className="mx-auto max-w-xl text-center">
          <p className="mb-4 text-xs font-semibold uppercase tracking-widest text-ink-subtle">
            Ready?
          </p>
          <h2 className="text-4xl font-semibold leading-tight tracking-tight text-ink">
            Start building better habits today.
          </h2>
          <p className="mx-auto mt-5 max-w-sm text-sm leading-relaxed text-ink-muted">
            No account needed. No downloads. Add your schedule, pick a habit,
            and let the app do the rest.
          </p>
          <div className="mt-10 flex flex-wrap justify-center gap-3">
            <Link
              href="/onboarding"
              className="rounded-lg bg-accent px-7 py-3 text-sm font-medium text-white transition-colors hover:bg-accent-hover"
            >
              Get started
            </Link>
            {mounted && signedIn && (
              <Link
                href="/home"
                className="rounded-lg border border-rim bg-white px-7 py-3 text-sm font-medium text-ink transition-colors hover:bg-stone-50"
              >
                Open app
              </Link>
            )}
          </div>
        </div>
      </section>

      {/* ── Footer ──────────────────────────────────────────────────────── */}
      <footer className="border-t border-rim bg-white">
        <div className="mx-auto flex max-w-4xl items-center justify-between px-6 py-6">
          <span className="text-xs font-semibold text-ink-subtle">
            Micro Habit Coach
          </span>
          <span className="text-xs text-ink-subtle">
            No tracking · No ads · No account required
          </span>
        </div>
      </footer>

    </div>
  );
}
