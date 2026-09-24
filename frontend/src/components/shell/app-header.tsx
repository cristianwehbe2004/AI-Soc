"use client";

import { apiRequest } from "@/lib/api/client";
import type { HealthResponse } from "@/lib/api/types";
import { useQuery } from "@tanstack/react-query";
import { Menu, Radio } from "lucide-react";

export function AppHeader({ onOpenMenu }: { onOpenMenu: () => void }) {
  const health = useQuery({
    queryKey: ["health"],
    queryFn: () => apiRequest<HealthResponse>("/health", { auth: false }),
    refetchInterval: 30_000,
  });
  const healthy = health.data?.status === "healthy";

  return (
    <header className="app-header">
      <button className="icon-button mobile-menu" onClick={onOpenMenu} aria-label="Open navigation">
        <Menu size={21} />
      </button>
      <div className="environment-chip">
        <span className="pulse-dot" data-healthy={healthy} />
        <span>{health.isPending ? "Checking systems" : healthy ? "Systems nominal" : "System degraded"}</span>
      </div>
      <div className="header-context">
        <Radio size={15} />
        <span>Local environment</span>
        <span className="request-mode">REST</span>
      </div>
    </header>
  );
}
