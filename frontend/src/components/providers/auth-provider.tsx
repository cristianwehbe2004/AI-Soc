"use client";

import {
  clearAccessToken,
  loginSession,
  logoutSession,
  refreshSession,
  subscribeToSession,
} from "@/lib/api/client";
import type { ApiUser } from "@/lib/api/types";
import { useRouter } from "next/navigation";
import {
  createContext,
  type ReactNode,
  use,
  useEffect,
  useRef,
  useState,
} from "react";

type AuthStatus = "loading" | "authenticated" | "anonymous";

interface AuthContextValue {
  status: AuthStatus;
  user: ApiUser | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);
let bootstrapPromise: ReturnType<typeof refreshSession> | null = null;

export function AuthProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [user, setUser] = useState<ApiUser | null>(null);
  const refreshTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const channel = useRef<BroadcastChannel | null>(null);

  useEffect(() => {
    const unsubscribe = subscribeToSession((session) => {
      setUser(session?.user ?? null);
      setStatus(session ? "authenticated" : "anonymous");
      if (refreshTimer.current) clearTimeout(refreshTimer.current);
      if (session) {
        refreshTimer.current = setTimeout(
          () => void refreshSession(),
          Math.max(1_000, (session.expires_in - 60) * 1_000),
        );
      }
    });

    if (typeof BroadcastChannel !== "undefined") {
      channel.current = new BroadcastChannel("ai-soc-auth");
      channel.current.onmessage = (event) => {
        if (event.data === "logout") clearAccessToken();
      };
    }

    bootstrapPromise ??= refreshSession();
    void bootstrapPromise.then((session) => {
      if (!session) setStatus("anonymous");
    });

    return () => {
      unsubscribe();
      channel.current?.close();
      if (refreshTimer.current) clearTimeout(refreshTimer.current);
    };
  }, []);

  async function login(email: string, password: string) {
    await loginSession(email, password);
  }

  async function logout() {
    await logoutSession();
    channel.current?.postMessage("logout");
    router.replace("/login");
    router.refresh();
  }

  return (
    <AuthContext value={{ status, user, login, logout }}>
      {children}
    </AuthContext>
  );
}

export function useAuth() {
  const context = use(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}

export function resetAuthBootstrapForTests() {
  bootstrapPromise = null;
}
