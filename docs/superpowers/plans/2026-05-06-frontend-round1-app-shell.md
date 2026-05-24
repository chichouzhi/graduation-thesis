# Frontend Round 1 App Shell Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone `frontend/` React workspace with a student-facing academic workbench shell, static routes, and page skeletons for dashboard, chat, documents, topics, and taskboard.

**Architecture:** Create a Vite + React + TypeScript app under `frontend/`, wire global providers in a thin `app/` layer, mount `/app/*` routes inside a shared shell layout, and feed each page with static student demo data from feature-local mock modules. Keep routing, layout, and visual primitives stable so a later round can replace mock data with Axios and TanStack Query hooks without restructuring the UI.

**Tech Stack:** React, Vite, TypeScript, React Router, Tailwind CSS, shadcn/ui, TanStack Query, Zustand, Axios

---

### Task 1: Scaffold the standalone frontend workspace

**Files:**
- Create: `frontend/`
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/vite-env.d.ts`

- [ ] **Step 1: Scaffold the Vite React TypeScript app**

Run:

```bash
npm create vite@latest frontend -- --template react-ts
```

Expected: Vite creates a new `frontend/` directory with the default React TypeScript starter.

- [ ] **Step 2: Enter the frontend workspace and install baseline dependencies**

Run:

```bash
npm install
```

Workdir:

```text
frontend/
```

Expected: `node_modules/` and `package-lock.json` are created successfully.

- [ ] **Step 3: Verify the starter builds before customization**

Run:

```bash
npm run build
```

Expected: a successful Vite production build with output in `frontend/dist/`.

- [ ] **Step 4: Commit the clean scaffold**

Run:

```bash
git add frontend
git commit -m "feat: scaffold frontend vite workspace"
```

Expected: one commit that captures only the generated baseline app.

### Task 2: Install routing, styling, data, and UI dependencies

**Files:**
- Modify: `frontend/package.json`
- Create: `frontend/postcss.config.js`
- Create: `frontend/tailwind.config.ts`
- Create: `frontend/components.json`
- Modify: `frontend/src/index.css`

- [ ] **Step 1: Install runtime dependencies for the planned stack**

Run:

```bash
npm install react-router-dom @tanstack/react-query zustand axios lucide-react class-variance-authority clsx tailwind-merge
```

Workdir:

```text
frontend/
```

Expected: `package.json` dependencies include Router, Query, Zustand, Axios, icons, and utility helpers.

- [ ] **Step 2: Install Tailwind, shadcn prerequisites, and animation support**

Run:

```bash
npm install -D tailwindcss postcss autoprefixer tailwindcss-animate
```

Workdir:

```text
frontend/
```

Expected: Tailwind-related dev dependencies are added.

- [ ] **Step 3: Generate Tailwind base config**

Run:

```bash
npx tailwindcss init -p
```

Workdir:

```text
frontend/
```

Expected: `tailwind.config.js` and `postcss.config.js` are generated.

- [ ] **Step 4: Replace generated Tailwind config with the project-specific TypeScript config**

Update `frontend/tailwind.config.ts` to:

```ts
import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./index.html",
    "./src/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      boxShadow: {
        soft: "0 12px 40px -18px rgba(15, 23, 42, 0.18)",
      },
      backgroundImage: {
        "paper-grid":
          "linear-gradient(to right, rgba(15,23,42,0.04) 1px, transparent 1px), linear-gradient(to bottom, rgba(15,23,42,0.04) 1px, transparent 1px)",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};

export default config;
```

Replace `frontend/postcss.config.js` with:

```js
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
```

Expected: Tailwind content scanning and theme tokens are aligned with the planned app structure.

- [ ] **Step 5: Add shadcn configuration**

Create `frontend/components.json` with:

```json
{
  "$schema": "https://ui.shadcn.com/schema.json",
  "style": "default",
  "rsc": false,
  "tsx": true,
  "tailwind": {
    "config": "tailwind.config.ts",
    "css": "src/app/styles.css",
    "baseColor": "slate",
    "cssVariables": true
  },
  "aliases": {
    "components": "@/components",
    "utils": "@/lib/utils",
    "ui": "@/components/ui",
    "lib": "@/lib",
    "hooks": "@/hooks"
  }
}
```

Expected: shadcn CLI can resolve aliases and CSS entrypoints.

- [ ] **Step 6: Commit the dependency and config layer**

Run:

```bash
git add frontend/package.json frontend/package-lock.json frontend/postcss.config.js frontend/tailwind.config.ts frontend/components.json
git commit -m "feat: add frontend ui and state dependencies"
```

Expected: one commit containing dependency and config changes only.

### Task 3: Establish app-level providers, aliases, and global styling

**Files:**
- Modify: `frontend/tsconfig.json`
- Modify: `frontend/vite.config.ts`
- Create: `frontend/src/app/app.tsx`
- Create: `frontend/src/app/providers.tsx`
- Create: `frontend/src/app/store.ts`
- Create: `frontend/src/app/styles.css`
- Create: `frontend/src/lib/utils.ts`
- Create: `frontend/src/lib/axios.ts`
- Modify: `frontend/src/main.tsx`
- Delete: `frontend/src/index.css`
- Delete: `frontend/src/App.tsx`

- [ ] **Step 1: Add the `@/` alias to TypeScript and Vite**

Update `frontend/tsconfig.json` to include:

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "allowJs": false,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true,
    "strict": true,
    "forceConsistentCasingInFileNames": true,
    "module": "ESNext",
    "moduleResolution": "Node",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"]
    }
  },
  "include": ["src"],
  "references": []
}
```

Update `frontend/vite.config.ts` to:

```ts
import path from "node:path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
```

Expected: source files can import via `@/`.

- [ ] **Step 2: Create shared utilities and Axios entrypoint**

Create `frontend/src/lib/utils.ts` with:

```ts
import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

Create `frontend/src/lib/axios.ts` with:

```ts
import axios from "axios";

export const apiClient = axios.create({
  baseURL: "/api/v1",
  timeout: 15000,
});
```

Expected: the project has a shared className helper and future API client entry.

- [ ] **Step 3: Add global store and providers**

Create `frontend/src/app/store.ts` with:

```ts
import { create } from "zustand";

type UserSummary = {
  id: string;
  name: string;
  role: "student";
  studentNo: string;
};

type TermSummary = {
  id: string;
  name: string;
};

type AppState = {
  isAuthenticated: boolean;
  currentUser: UserSummary;
  currentTerm: TermSummary;
  login: () => void;
  logout: () => void;
};

export const useAppStore = create<AppState>((set) => ({
  isAuthenticated: false,
  currentUser: {
    id: "student-001",
    name: "刘佳浩",
    role: "student",
    studentNo: "20220001",
  },
  currentTerm: {
    id: "term-2026-spring",
    name: "2026 春季学期",
  },
  login: () => set({ isAuthenticated: true }),
  logout: () => set({ isAuthenticated: false }),
}));
```

Create `frontend/src/app/providers.tsx` with:

```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { PropsWithChildren, useState } from "react";

export function AppProviders({ children }: PropsWithChildren) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            retry: false,
            refetchOnWindowFocus: false,
          },
        },
      }),
  );

  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}
```

Create `frontend/src/app/app.tsx` with:

```tsx
import { RouterProvider } from "react-router-dom";

import { AppProviders } from "@/app/providers";
import { router } from "@/routes";

export function App() {
  return (
    <AppProviders>
      <RouterProvider router={router} />
    </AppProviders>
  );
}
```

Expected: provider wiring is centralized and intentionally minimal.

- [ ] **Step 4: Replace the starter CSS with the academic workbench theme**

Create `frontend/src/app/styles.css` with:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --background: 42 24% 97%;
    --foreground: 198 28% 16%;
    --card: 0 0% 100%;
    --card-foreground: 198 28% 16%;
    --primary: 184 39% 27%;
    --primary-foreground: 0 0% 100%;
    --secondary: 165 18% 92%;
    --secondary-foreground: 184 39% 23%;
    --muted: 35 20% 93%;
    --muted-foreground: 200 12% 38%;
    --accent: 44 38% 90%;
    --accent-foreground: 198 28% 18%;
    --border: 200 18% 84%;
    --input: 200 18% 84%;
    --ring: 184 39% 27%;
    --radius: 1rem;
  }

  * {
    @apply border-border;
  }

  body {
    @apply bg-background text-foreground antialiased;
    font-family: "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
    background-image:
      radial-gradient(circle at top, rgba(12, 74, 71, 0.08), transparent 32%),
      linear-gradient(to bottom, rgba(255, 255, 255, 0.8), rgba(247, 245, 240, 0.95));
    min-height: 100vh;
  }

  #root {
    min-height: 100vh;
  }
}
```

Update `frontend/src/main.tsx` to:

```tsx
import React from "react";
import ReactDOM from "react-dom/client";

import { App } from "@/app/app";
import "@/app/styles.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
```

Expected: the starter counter app is removed and the new theme becomes the global baseline.

- [ ] **Step 5: Commit the app foundation layer**

Run:

```bash
git add frontend/tsconfig.json frontend/vite.config.ts frontend/src
git commit -m "feat: add frontend app foundation"
```

Expected: one commit that replaces starter code with the app shell foundation.

### Task 4: Initialize shadcn/ui primitives and shared display components

**Files:**
- Create: `frontend/src/components/ui/button.tsx`
- Create: `frontend/src/components/ui/card.tsx`
- Create: `frontend/src/components/ui/badge.tsx`
- Create: `frontend/src/components/ui/input.tsx`
- Create: `frontend/src/components/ui/avatar.tsx`
- Create: `frontend/src/components/ui/scroll-area.tsx`
- Create: `frontend/src/components/shared/stat-card.tsx`
- Create: `frontend/src/components/shared/status-badge.tsx`
- Create: `frontend/src/components/shared/section-heading.tsx`
- Create: `frontend/src/components/shared/empty-state.tsx`

- [ ] **Step 1: Initialize shadcn and add the required primitives**

Run:

```bash
npx shadcn@latest init -y
npx shadcn@latest add button card badge input avatar scroll-area
```

Workdir:

```text
frontend/
```

Expected: shadcn generates the selected primitives inside `src/components/ui/`.

- [ ] **Step 2: Add the shared academic workbench primitives**

Create `frontend/src/components/shared/status-badge.tsx` with:

```tsx
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

type AsyncStatus = "pending" | "running" | "done" | "failed";

const statusStyles: Record<AsyncStatus, string> = {
  pending: "bg-amber-100 text-amber-900 hover:bg-amber-100",
  running: "bg-sky-100 text-sky-900 hover:bg-sky-100",
  done: "bg-emerald-100 text-emerald-900 hover:bg-emerald-100",
  failed: "bg-rose-100 text-rose-900 hover:bg-rose-100",
};

export function StatusBadge({ status, className }: { status: AsyncStatus; className?: string }) {
  return (
    <Badge className={cn("rounded-full px-3 py-1 text-xs font-medium", statusStyles[status], className)}>
      {status}
    </Badge>
  );
}
```

Create `frontend/src/components/shared/stat-card.tsx` with:

```tsx
import { ReactNode } from "react";

import { Card, CardContent } from "@/components/ui/card";

export function StatCard({
  label,
  value,
  hint,
  icon,
}: {
  label: string;
  value: string;
  hint: string;
  icon: ReactNode;
}) {
  return (
    <Card className="border-white/70 bg-white/85 shadow-soft backdrop-blur">
      <CardContent className="flex items-start justify-between p-5">
        <div className="space-y-2">
          <p className="text-sm text-muted-foreground">{label}</p>
          <p className="text-3xl font-semibold tracking-tight">{value}</p>
          <p className="text-sm text-muted-foreground">{hint}</p>
        </div>
        <div className="rounded-2xl bg-secondary p-3 text-primary">{icon}</div>
      </CardContent>
    </Card>
  );
}
```

Create `frontend/src/components/shared/section-heading.tsx` with:

```tsx
export function SectionHeading({
  title,
  description,
}: {
  title: string;
  description?: string;
}) {
  return (
    <div className="space-y-1">
      <h2 className="text-xl font-semibold tracking-tight">{title}</h2>
      {description ? <p className="text-sm text-muted-foreground">{description}</p> : null}
    </div>
  );
}
```

Create `frontend/src/components/shared/empty-state.tsx` with:

```tsx
import { ReactNode } from "react";

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="rounded-3xl border border-dashed border-border bg-white/70 p-8 text-center">
      <h3 className="text-lg font-semibold">{title}</h3>
      <p className="mt-2 text-sm text-muted-foreground">{description}</p>
      {action ? <div className="mt-4">{action}</div> : null}
    </div>
  );
}
```

Expected: shared layout primitives encapsulate repeated status and section styling.

- [ ] **Step 3: Commit the UI primitives**

Run:

```bash
git add frontend/src/components frontend/components.json
git commit -m "feat: add frontend shared ui primitives"
```

Expected: one commit containing reusable UI and display components.

### Task 5: Build the route tree and shared shell layout

**Files:**
- Create: `frontend/src/routes/index.tsx`
- Create: `frontend/src/routes/protected-layout.tsx`
- Create: `frontend/src/components/layout/app-shell.tsx`
- Create: `frontend/src/components/layout/app-sidebar.tsx`
- Create: `frontend/src/components/layout/app-header.tsx`
- Create: `frontend/src/components/layout/page-section.tsx`

- [ ] **Step 1: Create the shell layout components**

Create `frontend/src/components/layout/app-sidebar.tsx` with:

```tsx
import { BookOpenText, Files, LayoutDashboard, MessagesSquare, SquareKanban } from "lucide-react";
import { NavLink } from "react-router-dom";

import { cn } from "@/lib/utils";

const items = [
  { to: "/app/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/app/chat", label: "Chat", icon: MessagesSquare },
  { to: "/app/documents", label: "Documents", icon: Files },
  { to: "/app/topics", label: "Topics", icon: BookOpenText },
  { to: "/app/taskboard", label: "Taskboard", icon: SquareKanban },
];

export function AppSidebar() {
  return (
    <aside className="hidden w-72 flex-col border-r border-white/70 bg-[#f7f4ee]/90 px-5 py-6 lg:flex">
      <div className="mb-8 space-y-2">
        <p className="text-xs font-semibold uppercase tracking-[0.3em] text-primary/70">Academic Copilot</p>
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900">AI 学术助手工作台</h1>
          <p className="mt-2 text-sm leading-6 text-slate-600">围绕聊天、文档与毕业任务推进的学生端工作空间。</p>
        </div>
      </div>

      <nav className="space-y-2">
        {items.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 rounded-2xl px-4 py-3 text-sm font-medium text-slate-600 transition-colors",
                isActive ? "bg-white text-slate-950 shadow-soft" : "hover:bg-white/70 hover:text-slate-950",
              )
            }
          >
            <item.icon className="h-4 w-4" />
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="mt-auto rounded-3xl border border-white/70 bg-white/80 p-4">
        <p className="text-xs uppercase tracking-[0.24em] text-muted-foreground">Student Workspace</p>
        <p className="mt-2 text-sm font-medium">当前聚焦：毕业设计推进与答辩准备</p>
      </div>
    </aside>
  );
}
```

Create `frontend/src/components/layout/app-header.tsx` with:

```tsx
import { BellDot, GraduationCap } from "lucide-react";
import { useLocation } from "react-router-dom";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { useAppStore } from "@/app/store";

const pageCopy: Record<string, { title: string; description: string }> = {
  "/app/dashboard": {
    title: "Dashboard",
    description: "查看近期工作、任务状态和最近活动。",
  },
  "/app/chat": {
    title: "Chat",
    description: "围绕课题、论文与实现问题进行异步 AI 对话。",
  },
  "/app/documents": {
    title: "Documents",
    description: "管理 PDF 分析任务、处理中状态与结果摘要。",
  },
  "/app/topics": {
    title: "Topics",
    description: "浏览题目方向，组织选题思路与研究重点。",
  },
  "/app/taskboard": {
    title: "Taskboard",
    description: "跟踪毕业设计各阶段任务与关键节点。",
  },
};

export function AppHeader() {
  const location = useLocation();
  const { currentTerm, currentUser } = useAppStore();
  const current = pageCopy[location.pathname] ?? pageCopy["/app/dashboard"];

  return (
    <header className="flex flex-col gap-4 border-b border-white/70 bg-white/70 px-6 py-5 backdrop-blur md:flex-row md:items-center md:justify-between">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{current.title}</h1>
        <p className="mt-1 text-sm text-muted-foreground">{current.description}</p>
      </div>

      <div className="flex items-center gap-3">
        <Badge variant="secondary" className="rounded-full px-3 py-1">
          <GraduationCap className="mr-2 h-4 w-4" />
          {currentTerm.name}
        </Badge>
        <Badge variant="outline" className="rounded-full px-3 py-1">
          学生视角
        </Badge>
        <button className="rounded-full border border-border bg-white p-2 text-slate-600">
          <BellDot className="h-4 w-4" />
        </button>
        <Avatar className="h-10 w-10 border border-border">
          <AvatarFallback>{currentUser.name.slice(-2)}</AvatarFallback>
        </Avatar>
      </div>
    </header>
  );
}
```

Create `frontend/src/components/layout/page-section.tsx` with:

```tsx
import { PropsWithChildren } from "react";

import { cn } from "@/lib/utils";

export function PageSection({
  children,
  className,
}: PropsWithChildren<{ className?: string }>) {
  return (
    <section className={cn("rounded-[28px] border border-white/70 bg-white/80 p-6 shadow-soft backdrop-blur", className)}>
      {children}
    </section>
  );
}
```

Create `frontend/src/components/layout/app-shell.tsx` with:

```tsx
import { PropsWithChildren } from "react";

import { AppHeader } from "@/components/layout/app-header";
import { AppSidebar } from "@/components/layout/app-sidebar";

export function AppShell({ children }: PropsWithChildren) {
  return (
    <div className="min-h-screen lg:flex">
      <AppSidebar />
      <div className="flex min-h-screen flex-1 flex-col">
        <AppHeader />
        <main className="flex-1 p-4 md:p-6">{children}</main>
      </div>
    </div>
  );
}
```

Expected: the shell encodes a stable left-nav/top-bar/content layout for all `/app/*` pages.

- [ ] **Step 2: Add the protected layout and route table**

Create `frontend/src/routes/protected-layout.tsx` with:

```tsx
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
```

Create `frontend/src/routes/index.tsx` with:

```tsx
import { createBrowserRouter, Navigate } from "react-router-dom";

import { ProtectedLayout } from "@/routes/protected-layout";
import { ChatPage } from "@/pages/chat/chat-page";
import { DashboardPage } from "@/pages/dashboard/dashboard-page";
import { DocumentsPage } from "@/pages/documents/documents-page";
import { LoginPage } from "@/pages/login/login-page";
import { TaskboardPage } from "@/pages/taskboard/taskboard-page";
import { TopicsPage } from "@/pages/topics/topics-page";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <Navigate to="/login" replace />,
  },
  {
    path: "/login",
    element: <LoginPage />,
  },
  {
    path: "/app",
    element: <ProtectedLayout />,
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
```

Expected: the route tree matches the approved design and gatekeeps `/app/*` with the fake auth store.

- [ ] **Step 3: Commit the route and shell layer**

Run:

```bash
git add frontend/src/routes frontend/src/components/layout
git commit -m "feat: add frontend shell and route structure"
```

Expected: one commit for shell layout and routing only.

### Task 6: Create shared student demo data and the login/dashboard pages

**Files:**
- Create: `frontend/src/types/app.ts`
- Create: `frontend/src/data/student-workspace.ts`
- Create: `frontend/src/features/dashboard/dashboard.mock.ts`
- Create: `frontend/src/pages/login/login-page.tsx`
- Create: `frontend/src/pages/dashboard/dashboard-page.tsx`

- [ ] **Step 1: Create the shared demo types and student workspace context**

Create `frontend/src/types/app.ts` with:

```ts
export type AsyncStatus = "pending" | "running" | "done" | "failed";

export type ActivityItem = {
  id: string;
  title: string;
  description: string;
  time: string;
};
```

Create `frontend/src/data/student-workspace.ts` with:

```ts
export const studentWorkspace = {
  studentName: "刘佳浩",
  program: "软件工程",
  school: "信息工程学院",
  currentFocus: "毕业设计系统演示准备",
  quickLinks: [
    { label: "继续聊天分析", to: "/app/chat" },
    { label: "查看文档结果", to: "/app/documents" },
    { label: "整理选题资料", to: "/app/topics" },
    { label: "推进任务节点", to: "/app/taskboard" },
  ],
};
```

Expected: a single source of truth exists for student-facing copy and common lightweight types.

- [ ] **Step 2: Create dashboard mock data**

Create `frontend/src/features/dashboard/dashboard.mock.ts` with:

```ts
import { ActivityItem, AsyncStatus } from "@/types/app";

export const dashboardStats = [
  { id: "conversations", label: "会话总数", value: "12", hint: "近 7 天新增 4 个" },
  { id: "documents", label: "文档任务", value: "8", hint: "其中 2 个仍在处理中" },
  { id: "running", label: "进行中任务", value: "3", hint: "聊天与文档任务混合统计" },
  { id: "completed", label: "本周完成", value: "6", hint: "较上周多 2 个" },
];

export const dashboardTimeline = [
  { id: "w1", title: "完善聊天演示脚本", detail: "补充提问链路与系统回答节奏", status: "running" as AsyncStatus },
  { id: "w2", title: "复核文献总结结果", detail: "对比两篇相关论文的研究方法", status: "pending" as AsyncStatus },
  { id: "w3", title: "整理任务看板节点", detail: "把实现与论文写作阶段对齐", status: "done" as AsyncStatus },
];

export const dashboardActivities: ActivityItem[] = [
  { id: "a1", title: "AI 助手完成了一次课题分析", description: "《智能问答在学术场景中的应用》对比摘要已生成。", time: "10 分钟前" },
  { id: "a2", title: "PDF 文档解析进入运行中", description: "《RAG for Education.pdf》正在抽取与总结。", time: "35 分钟前" },
  { id: "a3", title: "任务看板更新了答辩准备节点", description: "新增“演示稿彩排”与“截图整理”。", time: "今天 09:20" },
];
```

Expected: dashboard content can be rendered from a feature-local mock source.

- [ ] **Step 3: Build the login page**

Create `frontend/src/pages/login/login-page.tsx` with:

```tsx
import { BookMarked, KeyRound } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { useAppStore } from "@/app/store";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

export function LoginPage() {
  const navigate = useNavigate();
  const login = useAppStore((state) => state.login);

  return (
    <div className="flex min-h-screen items-center justify-center px-4 py-10">
      <div className="grid w-full max-w-6xl gap-6 lg:grid-cols-[1.15fr_0.85fr]">
        <section className="rounded-[32px] border border-white/70 bg-white/70 p-8 shadow-soft backdrop-blur md:p-12">
          <p className="text-sm font-semibold uppercase tracking-[0.32em] text-primary/70">Academic Copilot</p>
          <h1 className="mt-6 max-w-2xl text-4xl font-semibold tracking-tight text-slate-950 md:text-5xl">
            面向毕业设计全过程的 AI 学术助手工作台
          </h1>
          <p className="mt-6 max-w-2xl text-base leading-8 text-slate-600">
            将异步聊天、文档处理、选题辅助和任务推进整合到同一套学生端工作空间中，适合演示完整的毕业设计产品链路。
          </p>
          <div className="mt-8 grid gap-4 md:grid-cols-2">
            <Card className="border-white/80 bg-[#faf8f3]">
              <CardContent className="p-5">
                <BookMarked className="h-5 w-5 text-primary" />
                <h2 className="mt-4 text-lg font-semibold">聚焦学术工作流</h2>
                <p className="mt-2 text-sm leading-6 text-muted-foreground">聊天、文档和阶段任务围绕毕业设计推进自然串联。</p>
              </CardContent>
            </Card>
            <Card className="border-white/80 bg-[#faf8f3]">
              <CardContent className="p-5">
                <KeyRound className="h-5 w-5 text-primary" />
                <h2 className="mt-4 text-lg font-semibold">学生端答辩视角</h2>
                <p className="mt-2 text-sm leading-6 text-muted-foreground">本轮使用静态登录入口和假数据，专注建立稳定工作台骨架。</p>
              </CardContent>
            </Card>
          </div>
        </section>

        <Card className="border-white/80 bg-white/88 shadow-soft">
          <CardContent className="p-8">
            <div className="space-y-2">
              <p className="text-sm font-semibold uppercase tracking-[0.24em] text-primary/70">Student Access</p>
              <h2 className="text-2xl font-semibold tracking-tight">登录工作台</h2>
              <p className="text-sm text-muted-foreground">使用学生端入口进入当前学期工作空间。</p>
            </div>
            <div className="mt-8 space-y-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">学号或用户名</label>
                <Input defaultValue="20220001" />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">密码</label>
                <Input defaultValue="demo-password" type="password" />
              </div>
              <Button
                className="mt-4 h-11 w-full rounded-2xl"
                onClick={() => {
                  login();
                  navigate("/app/dashboard");
                }}
              >
                进入 AI 学术助手工作台
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
```

Expected: login visually introduces the product and performs fake auth into the app shell.

- [ ] **Step 4: Build the dashboard page**

Create `frontend/src/pages/dashboard/dashboard-page.tsx` with:

```tsx
import { ArrowRight, Bot, CheckCircle2, Clock3, Files } from "lucide-react";
import { Link } from "react-router-dom";

import { PageSection } from "@/components/layout/page-section";
import { SectionHeading } from "@/components/shared/section-heading";
import { StatCard } from "@/components/shared/stat-card";
import { StatusBadge } from "@/components/shared/status-badge";
import { studentWorkspace } from "@/data/student-workspace";
import { dashboardActivities, dashboardStats, dashboardTimeline } from "@/features/dashboard/dashboard.mock";

const statIcons = [Bot, Files, Clock3, CheckCircle2];

export function DashboardPage() {
  return (
    <div className="space-y-6">
      <PageSection className="overflow-hidden bg-[linear-gradient(135deg,rgba(12,74,71,0.12),rgba(255,255,255,0.9))]">
        <p className="text-sm font-semibold uppercase tracking-[0.28em] text-primary/70">Current Focus</p>
        <h2 className="mt-4 text-3xl font-semibold tracking-tight">{studentWorkspace.currentFocus}</h2>
        <p className="mt-3 max-w-3xl text-sm leading-7 text-slate-600">
          你正在围绕聊天分析、文档总结、选题整理和答辩准备推进毕业设计。这个首页优先展示最近工作、任务状态与下一步动作。
        </p>
      </PageSection>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {dashboardStats.map((stat, index) => {
          const Icon = statIcons[index];

          return <StatCard key={stat.id} label={stat.label} value={stat.value} hint={stat.hint} icon={<Icon className="h-5 w-5" />} />;
        })}
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
        <PageSection>
          <SectionHeading title="近期工作" description="把近期最重要的推进事项集中在同一视图中。" />
          <div className="mt-6 space-y-4">
            {dashboardTimeline.map((item) => (
              <div key={item.id} className="flex items-start justify-between gap-4 rounded-2xl border border-border/70 bg-[#fcfbf8] p-4">
                <div>
                  <h3 className="font-medium">{item.title}</h3>
                  <p className="mt-2 text-sm text-muted-foreground">{item.detail}</p>
                </div>
                <StatusBadge status={item.status} />
              </div>
            ))}
          </div>
        </PageSection>

        <PageSection>
          <SectionHeading title="快捷入口" description="从主页直接进入当前最常用的演示链路。" />
          <div className="mt-6 space-y-3">
            {studentWorkspace.quickLinks.map((item) => (
              <Link
                key={item.to}
                to={item.to}
                className="flex items-center justify-between rounded-2xl border border-border/70 bg-[#fcfbf8] px-4 py-4 text-sm font-medium transition hover:border-primary/40 hover:text-primary"
              >
                <span>{item.label}</span>
                <ArrowRight className="h-4 w-4" />
              </Link>
            ))}
          </div>
        </PageSection>
      </div>

      <PageSection>
        <SectionHeading title="最近活动" description="帮助答辩演示时快速讲清系统的近期状态变化。" />
        <div className="mt-6 grid gap-4 lg:grid-cols-3">
          {dashboardActivities.map((item) => (
            <article key={item.id} className="rounded-2xl border border-border/70 bg-[#fcfbf8] p-4">
              <p className="text-xs uppercase tracking-[0.2em] text-primary/70">{item.time}</p>
              <h3 className="mt-3 font-medium">{item.title}</h3>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">{item.description}</p>
            </article>
          ))}
        </div>
      </PageSection>
    </div>
  );
}
```

Expected: dashboard looks like a product workbench, not a generic table-first admin.

- [ ] **Step 5: Commit the login and dashboard slice**

Run:

```bash
git add frontend/src/types frontend/src/data frontend/src/features/dashboard frontend/src/pages/login frontend/src/pages/dashboard
git commit -m "feat: add frontend login and dashboard pages"
```

Expected: one focused commit for the entry flow and homepage.

### Task 7: Build the chat and documents skeleton pages

**Files:**
- Create: `frontend/src/features/chat/chat.mock.ts`
- Create: `frontend/src/features/documents/documents.mock.ts`
- Create: `frontend/src/pages/chat/chat-page.tsx`
- Create: `frontend/src/pages/documents/documents-page.tsx`

- [ ] **Step 1: Create chat and document mock data**

Create `frontend/src/features/chat/chat.mock.ts` with:

```ts
export const conversations = [
  { id: "conv-1", title: "RAG 在学术问答中的应用", updatedAt: "刚刚" },
  { id: "conv-2", title: "毕业设计任务拆解建议", updatedAt: "今天 11:10" },
  { id: "conv-3", title: "开题报告研究现状整理", updatedAt: "昨天" },
];

export const messages = [
  { id: "m-1", role: "user", content: "请帮我梳理一下答辩演示应该如何突出系统的异步能力。", status: null },
  { id: "m-2", role: "assistant", content: "建议从受理、排队、处理中和结果回写四个阶段讲解。", status: "done" as const },
  { id: "m-3", role: "assistant", content: "正在补充 PDF 任务链路说明…", status: "running" as const },
  { id: "m-4", role: "assistant", content: "一个历史任务因为超时而失败，可在页面中清楚展示。", status: "failed" as const },
  { id: "m-5", role: "assistant", content: "", status: "pending" as const },
];
```

Create `frontend/src/features/documents/documents.mock.ts` with:

```ts
export const documentTasks = [
  { id: "doc-1", filename: "RAG-for-Education.pdf", status: "running" as const, currentStage: "chunk_summarizing", progress: "8 / 12 页块" },
  { id: "doc-2", filename: "Thesis-Outline.pdf", status: "done" as const, currentStage: "final_result", progress: "已完成" },
  { id: "doc-3", filename: "Survey-Paper.pdf", status: "failed" as const, currentStage: "pdf_extract", progress: "解析失败" },
];

export const documentDetail = {
  id: "doc-1",
  filename: "RAG-for-Education.pdf",
  status: "running" as const,
  taskType: "summary",
  language: "zh",
  stages: [
    { label: "上传受理", value: "done" as const },
    { label: "PDF 解析", value: "done" as const },
    { label: "分块总结", value: "running" as const },
    { label: "聚合结果", value: "pending" as const },
  ],
  summary:
    "该论文聚焦检索增强生成在教育场景中的应用价值，强调知识可信度、来源可追溯和回答结构化呈现。",
  bulletPoints: [
    "提出面向学习者问答的 RAG 流程设计。",
    "关注引用透明度与知识更新问题。",
    "适合映射到本项目的学术助手场景。",
  ],
};
```

Expected: both pages have feature-local mock data aligned with their future async use cases.

- [ ] **Step 2: Build the chat page**

Create `frontend/src/pages/chat/chat-page.tsx` with:

```tsx
import { SendHorizonal } from "lucide-react";

import { PageSection } from "@/components/layout/page-section";
import { SectionHeading } from "@/components/shared/section-heading";
import { StatusBadge } from "@/components/shared/status-badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { conversations, messages } from "@/features/chat/chat.mock";

export function ChatPage() {
  return (
    <div className="grid gap-6 xl:grid-cols-[280px_minmax(0,1fr)_320px]">
      <PageSection className="p-4">
        <SectionHeading title="会话列表" description="预留后续会话拉取与切换能力。" />
        <div className="mt-5 space-y-3">
          {conversations.map((item) => (
            <div key={item.id} className="rounded-2xl border border-border/70 bg-[#fcfbf8] p-4">
              <h3 className="font-medium">{item.title}</h3>
              <p className="mt-2 text-xs text-muted-foreground">更新于 {item.updatedAt}</p>
            </div>
          ))}
        </div>
      </PageSection>

      <PageSection className="flex min-h-[72vh] flex-col">
        <SectionHeading title="消息流" description="天然预留 assistant 异步状态显示与后续轮询空间。" />
        <ScrollArea className="mt-6 flex-1 pr-3">
          <div className="space-y-4">
            {messages.map((message) => (
              <div
                key={message.id}
                className={message.role === "user" ? "ml-auto max-w-[80%] rounded-3xl bg-primary p-4 text-primary-foreground" : "mr-auto max-w-[85%] rounded-3xl border border-border/70 bg-[#fcfbf8] p-4"}
              >
                <div className="flex items-center justify-between gap-3">
                  <p className="text-xs uppercase tracking-[0.2em] opacity-70">{message.role}</p>
                  {message.status ? <StatusBadge status={message.status} /> : null}
                </div>
                <p className="mt-3 text-sm leading-7">{message.content || "等待任务受理后生成内容…"}</p>
              </div>
            ))}
          </div>
        </ScrollArea>
        <div className="mt-6 flex items-center gap-3 rounded-3xl border border-border/70 bg-white p-3">
          <Input className="border-0 shadow-none focus-visible:ring-0" placeholder="输入你想继续推进的问题…" />
          <Button size="icon" className="rounded-2xl">
            <SendHorizonal className="h-4 w-4" />
          </Button>
        </div>
      </PageSection>

      <PageSection>
        <SectionHeading title="当前会话摘要" description="这里预留 job 状态、上下文与观察面板。" />
        <div className="mt-6 space-y-4">
          <div className="rounded-2xl border border-border/70 bg-[#fcfbf8] p-4">
            <p className="text-sm font-medium">上下文类型</p>
            <p className="mt-2 text-sm text-muted-foreground">general</p>
          </div>
          <div className="rounded-2xl border border-border/70 bg-[#fcfbf8] p-4">
            <p className="text-sm font-medium">异步说明</p>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              下一轮这里可以展示 `job_id`、最近一次状态变化和失败原因。
            </p>
          </div>
        </div>
      </PageSection>
    </div>
  );
}
```

Expected: chat clearly visualizes the four async states even before any API integration.

- [ ] **Step 3: Build the documents page**

Create `frontend/src/pages/documents/documents-page.tsx` with:

```tsx
import { Upload } from "lucide-react";

import { PageSection } from "@/components/layout/page-section";
import { SectionHeading } from "@/components/shared/section-heading";
import { StatusBadge } from "@/components/shared/status-badge";
import { Button } from "@/components/ui/button";
import { documentDetail, documentTasks } from "@/features/documents/documents.mock";

export function DocumentsPage() {
  return (
    <div className="space-y-6">
      <PageSection className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.28em] text-primary/70">Document Pipeline</p>
          <h2 className="mt-3 text-2xl font-semibold tracking-tight">PDF 分析与总结任务</h2>
          <p className="mt-2 text-sm leading-7 text-muted-foreground">本轮只展示静态骨架，但页面结构已经为上传受理、任务推进与结果回写预留位置。</p>
        </div>
        <Button className="rounded-2xl">
          <Upload className="mr-2 h-4 w-4" />
          上传 PDF
        </Button>
      </PageSection>

      <div className="grid gap-6 xl:grid-cols-[340px_minmax(0,1fr)]">
        <PageSection>
          <SectionHeading title="任务列表" description="左侧保留后续轮询驱动的任务概览区。" />
          <div className="mt-6 space-y-3">
            {documentTasks.map((task) => (
              <div key={task.id} className="rounded-2xl border border-border/70 bg-[#fcfbf8] p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h3 className="font-medium">{task.filename}</h3>
                    <p className="mt-2 text-xs text-muted-foreground">{task.currentStage}</p>
                  </div>
                  <StatusBadge status={task.status} />
                </div>
                <p className="mt-3 text-sm text-muted-foreground">{task.progress}</p>
              </div>
            ))}
          </div>
        </PageSection>

        <PageSection>
          <SectionHeading title="任务详情" description="右侧详情区承接阶段状态、摘要结果与失败反馈。" />
          <div className="mt-6 flex items-start justify-between gap-4 rounded-2xl border border-border/70 bg-[#fcfbf8] p-4">
            <div>
              <h3 className="font-medium">{documentDetail.filename}</h3>
              <p className="mt-2 text-sm text-muted-foreground">task_type: {documentDetail.taskType} · language: {documentDetail.language}</p>
            </div>
            <StatusBadge status={documentDetail.status} />
          </div>

          <div className="mt-5 grid gap-3 md:grid-cols-2">
            {documentDetail.stages.map((stage) => (
              <div key={stage.label} className="rounded-2xl border border-border/70 bg-white p-4">
                <p className="text-sm font-medium">{stage.label}</p>
                <div className="mt-3">
                  <StatusBadge status={stage.value} />
                </div>
              </div>
            ))}
          </div>

          <div className="mt-5 rounded-2xl border border-border/70 bg-white p-5">
            <h3 className="font-medium">摘要结果</h3>
            <p className="mt-3 text-sm leading-7 text-muted-foreground">{documentDetail.summary}</p>
            <ul className="mt-4 space-y-2 text-sm text-slate-700">
              {documentDetail.bulletPoints.map((point) => (
                <li key={point} className="rounded-xl bg-[#fcfbf8] px-3 py-3">
                  {point}
                </li>
              ))}
            </ul>
          </div>
        </PageSection>
      </div>
    </div>
  );
}
```

Expected: documents has a clear left-list/right-detail split that can absorb real task polling later.

- [ ] **Step 4: Commit the chat and documents slice**

Run:

```bash
git add frontend/src/features/chat frontend/src/features/documents frontend/src/pages/chat frontend/src/pages/documents
git commit -m "feat: add frontend chat and documents skeleton pages"
```

Expected: one focused commit for the two core async pages.

### Task 8: Build the topics and taskboard skeleton pages

**Files:**
- Create: `frontend/src/features/topics/topics.mock.ts`
- Create: `frontend/src/features/taskboard/taskboard.mock.ts`
- Create: `frontend/src/pages/topics/topics-page.tsx`
- Create: `frontend/src/pages/taskboard/taskboard-page.tsx`

- [ ] **Step 1: Create topics and taskboard mock data**

Create `frontend/src/features/topics/topics.mock.ts` with:

```ts
export const topics = [
  {
    id: "topic-1",
    title: "面向毕业设计场景的 AI 学术助手工作台设计与实现",
    summary: "围绕异步聊天、PDF 文档处理与任务协同构建学生端产品。",
    requirements: "熟悉 React、Flask、异步任务队列与学术场景分析。",
    keywords: ["AI 助手", "异步任务", "文档理解"],
    capacity: 2,
  },
  {
    id: "topic-2",
    title: "学术问答系统中的检索增强与结果可解释性研究",
    summary: "重点探索引用溯源、知识更新与回答结构化表达。",
    requirements: "具备 NLP 或信息检索基础更佳。",
    keywords: ["RAG", "可解释性", "问答系统"],
    capacity: 1,
  },
];
```

Create `frontend/src/features/taskboard/taskboard.mock.ts` with:

```ts
export const taskColumns = [
  {
    id: "phase-1",
    title: "开题与调研",
    items: [
      { id: "t1", title: "补充研究现状对比", due: "5 月 10 日", priority: "高" },
      { id: "t2", title: "整理参考文献笔记", due: "5 月 12 日", priority: "中" },
    ],
  },
  {
    id: "phase-2",
    title: "系统实现",
    items: [
      { id: "t3", title: "完成前端应用壳", due: "5 月 8 日", priority: "高" },
      { id: "t4", title: "联调聊天与文档接口", due: "5 月 15 日", priority: "高" },
    ],
  },
  {
    id: "phase-3",
    title: "论文与答辩",
    items: [
      { id: "t5", title: "整理系统设计章节", due: "5 月 18 日", priority: "中" },
      { id: "t6", title: "准备答辩演示稿", due: "5 月 22 日", priority: "高" },
    ],
  },
];
```

Expected: the P1 pages have enough context to demonstrate breadth without any backend integration.

- [ ] **Step 2: Build the topics page**

Create `frontend/src/pages/topics/topics-page.tsx` with:

```tsx
import { PageSection } from "@/components/layout/page-section";
import { SectionHeading } from "@/components/shared/section-heading";
import { topics } from "@/features/topics/topics.mock";

export function TopicsPage() {
  return (
    <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
      <PageSection>
        <SectionHeading title="题目浏览" description="以选题辅助视角组织题目，而不是简单表格管理。" />
        <div className="mt-6 space-y-4">
          {topics.map((topic) => (
            <article key={topic.id} className="rounded-2xl border border-border/70 bg-[#fcfbf8] p-5">
              <h3 className="text-lg font-semibold">{topic.title}</h3>
              <p className="mt-3 text-sm leading-7 text-muted-foreground">{topic.summary}</p>
              <div className="mt-4 flex flex-wrap gap-2">
                {topic.keywords.map((keyword) => (
                  <span key={keyword} className="rounded-full bg-secondary px-3 py-1 text-xs font-medium text-secondary-foreground">
                    {keyword}
                  </span>
                ))}
              </div>
            </article>
          ))}
        </div>
      </PageSection>

      <PageSection>
        <SectionHeading title="题目详情摘要" description="预留后续详情查看与志愿状态展示区域。" />
        <div className="mt-6 rounded-2xl border border-border/70 bg-[#fcfbf8] p-5">
          <h3 className="text-lg font-semibold">{topics[0].title}</h3>
          <p className="mt-4 text-sm font-medium">研究要求</p>
          <p className="mt-2 text-sm leading-7 text-muted-foreground">{topics[0].requirements}</p>
          <p className="mt-4 text-sm font-medium">容量</p>
          <p className="mt-2 text-sm text-muted-foreground">{topics[0].capacity} 人</p>
        </div>
      </PageSection>
    </div>
  );
}
```

Expected: topics feels like a guided browse surface instead of a generic backend list.

- [ ] **Step 3: Build the taskboard page**

Create `frontend/src/pages/taskboard/taskboard-page.tsx` with:

```tsx
import { PageSection } from "@/components/layout/page-section";
import { SectionHeading } from "@/components/shared/section-heading";
import { taskColumns } from "@/features/taskboard/taskboard.mock";

export function TaskboardPage() {
  return (
    <div className="space-y-6">
      <PageSection>
        <SectionHeading title="毕业任务看板" description="以阶段推进的方式展示从开题到答辩准备的整体节奏。" />
      </PageSection>

      <div className="grid gap-6 xl:grid-cols-3">
        {taskColumns.map((column) => (
          <PageSection key={column.id} className="bg-[#fbfaf6]">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold">{column.title}</h3>
              <span className="rounded-full bg-secondary px-3 py-1 text-xs text-secondary-foreground">{column.items.length} 项</span>
            </div>
            <div className="mt-5 space-y-3">
              {column.items.map((item) => (
                <div key={item.id} className="rounded-2xl border border-border/70 bg-white p-4">
                  <h4 className="font-medium">{item.title}</h4>
                  <p className="mt-2 text-sm text-muted-foreground">截止时间：{item.due}</p>
                  <p className="mt-1 text-sm text-muted-foreground">优先级：{item.priority}</p>
                </div>
              ))}
            </div>
          </PageSection>
        ))}
      </div>
    </div>
  );
}
```

Expected: taskboard presents graduation progress as a structured process rather than a raw checklist.

- [ ] **Step 4: Commit the P1 breadth pages**

Run:

```bash
git add frontend/src/features/topics frontend/src/features/taskboard frontend/src/pages/topics frontend/src/pages/taskboard
git commit -m "feat: add frontend topics and taskboard skeleton pages"
```

Expected: one commit capturing the supporting breadth pages.

### Task 9: Verify the integrated frontend and document the run path

**Files:**
- Modify: `frontend/README.md`

- [ ] **Step 1: Add a concise frontend README**

Create or replace `frontend/README.md` with:

```md
# Frontend

## Run

```bash
npm install
npm run dev
```

## Build

```bash
npm run build
```

This round provides a static student-facing app shell and page skeletons only. No real API calls are wired yet.
```

Expected: future contributors have a minimal run/build guide inside the frontend workspace.

- [ ] **Step 2: Run the final production build**

Run:

```bash
npm run build
```

Workdir:

```text
frontend/
```

Expected: TypeScript and Vite compile the final app without errors.

- [ ] **Step 3: Smoke-test the route entry locally**

Run:

```bash
npm run dev -- --host 127.0.0.1 --port 4173
```

Workdir:

```text
frontend/
```

Expected: the dev server starts successfully and the following paths render:
- `/login`
- `/app/dashboard` after fake login
- `/app/chat`
- `/app/documents`
- `/app/topics`
- `/app/taskboard`

- [ ] **Step 4: Commit the verified frontend slice**

Run:

```bash
git add frontend/README.md frontend
git commit -m "feat: build frontend round1 academic workbench shell"
```

Expected: the final commit includes the verified working frontend for Round 1.
