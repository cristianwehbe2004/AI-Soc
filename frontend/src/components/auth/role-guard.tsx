"use client";

import { useAuth } from "@/components/providers/auth-provider";
import { hasPermission, type Permission } from "@/lib/auth/permissions";
import { ShieldX } from "lucide-react";
import type { ReactNode } from "react";

export function RoleGuard({
  permission,
  children,
}: {
  permission: Permission;
  children: ReactNode;
}) {
  const { user } = useAuth();
  if (!user || !hasPermission(user.role_name, permission)) {
    return (
      <section className="empty-state">
        <ShieldX size={30} />
        <p className="eyebrow">Access denied</p>
        <h1>This workspace requires administrator privileges.</h1>
        <p>The API will also reject this action with a 403 response.</p>
      </section>
    );
  }
  return children;
}
