"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { loginUser } from "@/lib/api/auth";
import { setAccessToken } from "@/lib/store/auth";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (password.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }
    setSubmitting(true);
    try {
      const { access_token } = await loginUser({ email, password });
      setAccessToken(access_token);
      router.push("/home");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="max-w-sm">
      <p className="text-xs font-semibold uppercase tracking-widest text-ink-subtle">
        Welcome back
      </p>
      <h1 className="mt-1 mb-8 text-2xl font-semibold tracking-tight text-ink">
        Log in to Micro Habit Coach
      </h1>

      <form onSubmit={handleSubmit} className="flex flex-col gap-5">
        <Input
          label="Email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          placeholder="alex@example.com"
        />
        <Input
          label="Password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          placeholder="Your password"
        />
        {error && (
          <p className="text-sm text-red-600">{error}</p>
        )}
        <div className="pt-2">
          <Button type="submit" loading={submitting}>
            Log in
          </Button>
        </div>
        <p className="text-sm text-ink-muted">
          Don&apos;t have an account?{" "}
          <Link href="/onboarding" className="text-accent hover:underline underline-offset-2">
            Get started
          </Link>
        </p>
      </form>
    </div>
  );
}
