import { RoleGuard } from "@/components/auth/role-guard";
import type { ReactNode } from "react";

export default function AdminLayout({ children }: { children: ReactNode }) {
  return <RoleGuard permission="users:manage">{children}</RoleGuard>;
}
