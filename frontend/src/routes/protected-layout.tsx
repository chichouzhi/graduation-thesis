import { Navigate, Outlet } from "react-router-dom";

import { useAppStore } from "@/app/store";
import { AppShell } from "@/components/layout/app-shell";

export function ProtectedLayout() {
  const isAuthenticated = useAppStore((state) => state.isAuthenticated);

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return (
    <AppShell>
      <Outlet />
    </AppShell>
  );
}
