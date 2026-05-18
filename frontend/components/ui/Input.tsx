import React from "react";

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label: string;
  error?: string;
}

export function Input({ label, error, id, className = "", ...rest }: InputProps) {
  const inputId = id ?? label.toLowerCase().replace(/\s+/g, "-");
  return (
    <div className="flex flex-col gap-1.5">
      <label
        htmlFor={inputId}
        className="text-xs font-semibold uppercase tracking-wide text-ink-muted"
      >
        {label}
      </label>
      <input
        id={inputId}
        {...rest}
        className={[
          "rounded-lg border border-rim bg-white px-3 py-2 text-sm text-ink",
          "placeholder:text-ink-subtle",
          "focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent",
          "disabled:opacity-40",
          className,
        ].join(" ")}
      />
      {error && <span className="text-xs text-red-600">{error}</span>}
    </div>
  );
}
