export function Progress({ value }: { value: number }) {
  return (
    <div className="h-5 w-full overflow-hidden rounded-md border-4 border-[var(--line)] bg-[#8ea577]">
      <div
        className="h-full bg-[var(--accent)] transition-all duration-500"
        style={{ width: `${Math.max(0, Math.min(100, value))}%` }}
      />
    </div>
  );
}
