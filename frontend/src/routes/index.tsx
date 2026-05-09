import { createBrowserRouter, Navigate } from "react-router-dom";

import { ChatPage } from "@/pages/chat/chat-page";
import { DashboardPage } from "@/pages/dashboard/dashboard-page";
import { DocumentsPage } from "@/pages/documents/documents-page";
import { LoginPage } from "@/pages/login/login-page";
import { TaskboardPage } from "@/pages/taskboard/taskboard-page";
import { TopicsPage } from "@/pages/topics/topics-page";
import { ProtectedLayout } from "@/routes/protected-layout";
import { RouteErrorPage } from "@/routes/route-error-page";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <Navigate to="/login" replace />,
    errorElement: <RouteErrorPage />,
  },
  {
    path: "/login",
    element: <LoginPage />,
    errorElement: <RouteErrorPage />,
  },
  {
    path: "/app",
    element: <ProtectedLayout />,
    errorElement: <RouteErrorPage />,
    children: [
      { index: true, element: <Navigate to="/app/dashboard" replace /> },
      { path: "dashboard", element: <DashboardPage /> },
      { path: "chat", element: <ChatPage /> },
      { path: "documents", element: <DocumentsPage /> },
      { path: "topics", element: <TopicsPage /> },
      { path: "taskboard", element: <TaskboardPage /> },
    ],
  },
]);
