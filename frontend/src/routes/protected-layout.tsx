import { Navigate, Outlet } from "react-router-dom";

import { useAppStore } from "@/app/store";
import { AppShell } from "@/components/layout/app-shell";

export function ProtectedLayout() {
  const { isAuthReady, isAuthenticated } = useAppStore((state) => ({
    isAuthReady: state.isAuthReady,
    isAuthenticated: state.isAuthenticated,
  }));

  if (!isAuthReady) {
    return null;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return (
    <AppShell>
      <Outlet />
    </AppShell>
  );
}
