import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Micro Habit Coach",
  description: "One habit. The right time.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen bg-canvas text-ink antialiased" suppressHydrationWarning>
        {children}
      </body>
    </html>
  );
}
