"use client";

import React from "react";

type Variant = "primary" | "ghost" | "danger";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  loading?: boolean;
}

const variants: Record<Variant, string> = {
  primary:
    "bg-accent text-white hover:bg-accent-hover",
  ghost:
    "bg-transparent text-ink border border-rim hover:bg-stone-50",
  danger:
    "bg-transparent text-red-700 border border-red-200 hover:bg-red-50",
};

export function Button({
  variant = "primary",
  loading = false,
  disabled,
  className = "",
  children,
  ...rest
}: ButtonProps) {
  return (
    <button
      {...rest}
      disabled={disabled || loading}
      className={[
        "inline-flex items-center justify-center rounded-lg px-4 py-2",
        "text-sm font-medium transition-colors duration-150",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2",
        "disabled:opacity-40 disabled:cursor-not-allowed",
        variants[variant],
        className,
      ].join(" ")}
    >
      {loading ? (
        <span className="inline-flex items-center gap-1.5">
          <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent" />
          <span>Loading</span>
        </span>
      ) : (
        children
      )}
    </button>
  );
}
