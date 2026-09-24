import type { LucideIcon } from "lucide-react";
import {
  Activity,
  BrainCircuit,
  FileKey2,
  Fingerprint,
  Gauge,
  KeyRound,
  ScrollText,
  ShieldAlert,
  Users,
} from "lucide-react";
import type { Permission } from "@/lib/auth/permissions";
import { hasPermission } from "@/lib/auth/permissions";
import type { RoleName } from "@/lib/api/types";

export interface NavigationItem {
  label: string;
  href: string;
  icon: LucideIcon;
  permission?: Permission;
}

export const primaryNavigation: NavigationItem[] = [
  { label: "Overview", href: "/dashboard", icon: Gauge },
  { label: "Events", href: "/events", icon: Activity },
  { label: "Incidents", href: "/incidents", icon: ShieldAlert },
  { label: "Investigations", href: "/investigations", icon: BrainCircuit },
  { label: "MITRE ATT&CK", href: "/mitre", icon: Fingerprint },
];

export const adminNavigation: NavigationItem[] = [
  {
    label: "Users",
    href: "/admin/users",
    icon: Users,
    permission: "users:manage",
  },
  {
    label: "API keys",
    href: "/admin/api-keys",
    icon: KeyRound,
    permission: "api_keys:manage",
  },
  {
    label: "Audit log",
    href: "/admin/audit",
    icon: ScrollText,
    permission: "audit:read",
  },
];

export const productIcon = FileKey2;

export function adminNavigationForRole(role: RoleName) {
  return adminNavigation.filter(
    (item) => !item.permission || hasPermission(role, item.permission),
  );
}
