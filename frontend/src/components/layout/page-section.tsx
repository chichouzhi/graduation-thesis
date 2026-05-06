import type { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

export function PageSection({ className, ...props }: HTMLAttributes<HTMLElement>) {
  return <section className={cn("page-section", className)} {...props} />;
}
