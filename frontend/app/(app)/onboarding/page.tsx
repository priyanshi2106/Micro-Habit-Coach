"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Button } from "@/components/ui/Button";
import { HabitForm } from "@/components/forms/HabitForm";
import { ScheduleBlockForm } from "@/components/forms/ScheduleBlockForm";
import { createUser } from "@/lib/api/users";
import { setUserId } from "@/lib/utils/userId";

type Step = "profile" | "setup";

const TIMEZONE_OPTIONS = [
  { value: "America/New_York", label: "Eastern Time — New York" },
  { value: "America/Chicago", label: "Central Time — Chicago" },
  { value: "America/Denver", label: "Mountain Time — Denver" },
  { value: "America/Los_Angeles", label: "Pacific Time — Los Angeles" },
  { value: "America/Anchorage", label: "Alaska Time — Anchorage" },
  { value: "Pacific/Honolulu", label: "Hawaii Time — Honolulu" },
  { value: "Europe/London", label: "GMT — London" },
  { value: "Europe/Paris", label: "CET — Paris / Berlin" },
  { value: "Europe/Helsinki", label: "EET — Helsinki / Kyiv" },
  { value: "Europe/Moscow", label: "MSK — Moscow" },
  { value: "Asia/Dubai", label: "GST — Dubai" },
  { value: "Asia/Kolkata", label: "IST — India" },
  { value: "Asia/Bangkok", label: "ICT — Bangkok / Jakarta" },
  { value: "Asia/Singapore", label: "SGT — Singapore" },
  { value: "Asia/Tokyo", label: "JST — Tokyo" },
  { value: "Asia/Seoul", label: "KST — Seoul" },
  { value: "Australia/Sydney", label: "AEDT — Sydney" },
  { value: "Pacific/Auckland", label: "NZST — Auckland" },
  { value: "UTC", label: "UTC" },
];

export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState<Step>("profile");

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const detectedTz =
    typeof window !== "undefined"
      ? Intl.DateTimeFormat().resolvedOptions().timeZone
      : "UTC";
  const [timezone, setTimezone] = useState(detectedTz);
  const [profileError, setProfileError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const [blocksAdded, setBlocksAdded] = useState(0);
  const [habitsAdded, setHabitsAdded] = useState(0);

  async function handleProfileSubmit(e: React.FormEvent) {
    e.preventDefault();
    setProfileError(null);
    setSubmitting(true);
    try {
      const user = await createUser({ name, email, timezone });
      setUserId(user.id);
      setStep("setup");
    } catch (err: unknown) {
      setProfileError(
        err instanceof Error ? err.message : "Failed to create account",
      );
    } finally {
      setSubmitting(false);
    }
  }

  const canFinish = blocksAdded > 0 && habitsAdded > 0;

  return (
    <div className="max-w-lg">
      {/* Step indicator */}
      <div className="mb-10 flex items-center gap-2">
        <div className="h-1 w-8 rounded-full bg-accent" />
        <div
          className={[
            "h-1 w-8 rounded-full transition-colors duration-300",
            step === "setup" ? "bg-accent" : "bg-rim",
          ].join(" ")}
        />
      </div>

      {step === "profile" ? (
        <div>
          <p className="text-xs font-semibold uppercase tracking-widest text-ink-subtle">
            Step 1 of 2
          </p>
          <h1 className="mt-1 mb-8 text-2xl font-semibold tracking-tight text-ink">
            Create your account
          </h1>

          <form onSubmit={handleProfileSubmit} className="flex flex-col gap-5">
            <Input
              label="Your name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              placeholder="Alex"
            />
            <Input
              label="Email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              placeholder="alex@example.com"
            />
            <Select
              label="Timezone"
              value={timezone}
              onChange={(e) => setTimezone(e.target.value)}
              options={TIMEZONE_OPTIONS}
            />
            {profileError && (
              <p className="text-sm text-red-600">{profileError}</p>
            )}
            <div className="pt-2">
              <Button type="submit" loading={submitting}>
                Continue
              </Button>
            </div>
          </form>
        </div>
      ) : (
        <div>
          <p className="text-xs font-semibold uppercase tracking-widest text-ink-subtle">
            Step 2 of 2
          </p>
          <h1 className="mt-1 mb-2 text-2xl font-semibold tracking-tight text-ink">
            Set up your schedule
          </h1>
          <p className="mb-8 text-sm text-ink-muted">
            Add your free time blocks and at least one habit so we can suggest
            the right moment for you.
          </p>

          <section className="mb-5 rounded-xl border border-rim bg-white p-6">
            <div className="mb-5 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-ink">Free time blocks</h2>
              {blocksAdded > 0 && (
                <span className="rounded-md bg-accent-light px-2 py-0.5 text-xs font-medium text-accent">
                  {blocksAdded} added
                </span>
              )}
            </div>
            <ScheduleBlockForm onSuccess={() => setBlocksAdded((n) => n + 1)} />
          </section>

          <section className="mb-8 rounded-xl border border-rim bg-white p-6">
            <div className="mb-5 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-ink">Starter habits</h2>
              {habitsAdded > 0 && (
                <span className="rounded-md bg-accent-light px-2 py-0.5 text-xs font-medium text-accent">
                  {habitsAdded} added
                </span>
              )}
            </div>
            <HabitForm onSuccess={() => setHabitsAdded((n) => n + 1)} />
          </section>

          <Button
            onClick={() => router.push("/home")}
            disabled={!canFinish}
            className="w-full"
          >
            {canFinish
              ? "Go to today's habit"
              : "Add a time block and a habit to continue"}
          </Button>
        </div>
      )}
    </div>
  );
}
