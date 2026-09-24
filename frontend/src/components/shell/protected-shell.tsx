"use client";

import { AuthLoading } from "@/components/auth/auth-loading";
import { useAuth } from "@/components/providers/auth-provider";
import { useRouter } from "next/navigation";
import { type ReactNode, useEffect, useState } from "react";
import { AppHeader } from "./app-header";
import { AppSidebar } from "./app-sidebar";

export function ProtectedShell({ children }: { children: ReactNode }) {
  const { status } = useAuth();
  const router = useRouter();
  const [menuOpen, setMenuOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  useEffect(() => {
    if (status === "anonymous") router.replace("/login");
  }, [router, status]);

  function toggleSidebar() {
    setSidebarCollapsed((current) => !current);
  }

  if (status !== "authenticated") return <AuthLoading />;

  return (
    <div className="app-frame" data-collapsed={sidebarCollapsed}>
      <AppSidebar
        open={menuOpen}
        collapsed={sidebarCollapsed}
        onClose={() => setMenuOpen(false)}
        onToggleCollapse={toggleSidebar}
      />
      <div className="app-main">
        <AppHeader onOpenMenu={() => setMenuOpen(true)} />
        <main className="page-canvas">{children}</main>
      </div>
    </div>
  );
}
