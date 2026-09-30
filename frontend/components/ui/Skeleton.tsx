import { cn } from "@/lib/cn";

export function Skeleton({ className }: { className?: string }) {
  return <div aria-hidden="true" className={cn("rounded-sm bg-bg-active motion-safe:animate-pulse", className)} />;
}
