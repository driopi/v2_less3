import { ReactNode } from "react";

import { cn } from "@/lib/utils";

export function Card({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-2xl border-4 border-[var(--line)] bg-[var(--card)] p-5 text-[var(--ink)] shadow-[8px_8px_0_var(--line)] sm:p-6",
        className
      )}
    >
      {children}
    </div>
  );
}
