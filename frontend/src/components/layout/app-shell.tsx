import type { PropsWithChildren } from "react";

import { AppHeader } from "@/components/layout/app-header";
import { AppSidebar } from "@/components/layout/app-sidebar";

export function AppShell({ children }: PropsWithChildren) {
  return (
    <div className="app-shell">
      <AppSidebar />
      <div className="app-main">
        <AppHeader />
        <main className="content-wrap">{children}</main>
      </div>
    </div>
  );
}
