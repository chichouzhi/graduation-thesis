import { cn } from "@/lib/utils";
import type { AsyncStatus } from "@/types/app";

export function StatusBadge({ status, className }: { status: AsyncStatus; className?: string }) {
  return <span className={cn("badge", status, className)}>{status}</span>;
}
