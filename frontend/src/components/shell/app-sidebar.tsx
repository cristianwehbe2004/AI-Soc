"use client";

import { useAuth } from "@/components/providers/auth-provider";
import { LogOut, PanelLeftClose, PanelLeftOpen, X } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  adminNavigationForRole,
  primaryNavigation,
  productIcon as ProductIcon,
  type NavigationItem,
} from "./navigation";

function NavLink({ item, onNavigate }: { item: NavigationItem; onNavigate: () => void }) {
  const pathname = usePathname();
  const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
  const Icon = item.icon;
  return (
    <Link
      href={item.href}
      onClick={onNavigate}
      className="nav-link"
      data-active={active}
      aria-current={active ? "page" : undefined}
    >
      <Icon size={18} strokeWidth={1.8} />
      <span>{item.label}</span>
    </Link>
  );
}

export function AppSidebar({
  open,
  collapsed,
  onClose,
  onToggleCollapse,
}: {
  open: boolean;
  collapsed: boolean;
  onClose: () => void;
  onToggleCollapse: () => void;
}) {
  const { user, logout } = useAuth();
  if (!user) return null;
  const adminItems = adminNavigationForRole(user.role_name);

  return (
    <>
      <button
        className="sidebar-scrim"
        data-open={open}
        onClick={onClose}
        aria-label="Close navigation"
      />
      <aside className="app-sidebar" data-open={open} data-collapsed={collapsed}>
        <div className="brand-lockup">
          <div className="brand-mark"><ProductIcon size={21} /></div>
          <div>
            <strong>AI-SOC</strong>
            <span>Operations console</span>
          </div>
          <button className="icon-button sidebar-close" onClick={onClose} aria-label="Close menu">
            <X size={20} />
          </button>
          <button
            className="icon-button sidebar-collapse"
            onClick={onToggleCollapse}
            aria-label={collapsed ? "Expand navigation" : "Collapse navigation"}
          >
            {collapsed ? <PanelLeftOpen size={18} /> : <PanelLeftClose size={18} />}
          </button>
        </div>

        <nav className="sidebar-nav" aria-label="Primary navigation">
          <p className="nav-label">Monitor</p>
          {primaryNavigation.map((item) => (
            <NavLink key={item.href} item={item} onNavigate={onClose} />
          ))}
          {adminItems.length > 0 && <p className="nav-label admin-label">Administration</p>}
          {adminItems.map((item) => (
            <NavLink key={item.href} item={item} onNavigate={onClose} />
          ))}
        </nav>

        <div className="sidebar-user">
          <div className="avatar">{user.full_name.slice(0, 2).toUpperCase()}</div>
          <div className="user-copy">
            <strong>{user.full_name}</strong>
            <span>{user.role_name}</span>
          </div>
          <button className="icon-button" onClick={() => void logout()} aria-label="Log out">
            <LogOut size={18} />
          </button>
        </div>
      </aside>
    </>
  );
}
