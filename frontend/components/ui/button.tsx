import { ButtonHTMLAttributes, ReactNode } from "react";

import { cn } from "@/lib/utils";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost";
  children: ReactNode;
}

export function Button({ className, variant = "primary", children, ...props }: ButtonProps) {
  return (
    <button
      className={cn(
        "inline-flex min-h-14 items-center justify-center rounded-lg border-4 border-[var(--line)] px-7 py-3 text-sm font-bold uppercase tracking-[0.08em] transition duration-150 sm:min-h-16 sm:px-9 sm:text-base",
        variant === "primary" &&
          "bg-[var(--accent)] text-[#d5e8bc] shadow-[6px_6px_0_var(--line)] hover:-translate-y-0.5 hover:bg-[#1d2f1b] disabled:bg-[#2f3f2e] disabled:text-[#9fb58d]",
        variant === "secondary" &&
          "bg-[var(--card)] text-[var(--ink)] shadow-[6px_6px_0_var(--line)] hover:-translate-y-0.5 hover:bg-[var(--card-2)]",
        variant === "ghost" &&
          "bg-transparent text-[var(--ink)] shadow-[4px_4px_0_var(--line)] hover:bg-black/10",
        "disabled:cursor-not-allowed disabled:translate-y-0 disabled:opacity-80",
        className
      )}
      {...props}
    >
      {children}
    </button>
  );
}
