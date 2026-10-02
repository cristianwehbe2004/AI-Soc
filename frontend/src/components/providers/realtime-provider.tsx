"use client";

import { useQueryClient } from "@tanstack/react-query";
import { createContext, type ReactNode, useContext, useEffect, useRef, useState } from "react";
import { createRealtimeTicket } from "@/lib/api/resources";
import { realtimeUrl, type RealtimeMessage, type RealtimeStatus } from "@/lib/realtime/client";
import { useAuth } from "./auth-provider";

interface RealtimeContextValue {
  status: RealtimeStatus;
  newEventCount: number;
  clearNewEvents: () => void;
}

const RealtimeContext = createContext<RealtimeContextValue | null>(null);
const MAX_RECONNECT_ATTEMPTS = 8;
const MAX_SEEN_MESSAGES = 1000;

export function RealtimeProvider({ children }: { children: ReactNode }) {
  const { status: authStatus } = useAuth();
  const queryClient = useQueryClient();
  const socket = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectAttempts = useRef(0);
  const seenMessages = useRef(new Set<string>());
  const versions = useRef(new Map<string, number>());
  const [status, setStatus] = useState<RealtimeStatus>("disconnected");
  const [newEventCount, setNewEventCount] = useState(0);

  useEffect(() => {
    if (authStatus !== "authenticated") {
      socket.current?.close();
      return;
    }

    let disposed = false;

    async function connect() {
      if (disposed) return;
      setStatus(reconnectAttempts.current ? "reconnecting" : "connecting");
      try {
        const { ticket } = await createRealtimeTicket();
        if (disposed) return;
        const connection = new WebSocket(realtimeUrl(ticket));
        socket.current = connection;
        connection.onopen = () => {
          reconnectAttempts.current = 0;
          setStatus("connected");
          void queryClient.invalidateQueries();
        };
        connection.onmessage = (event) => handleMessage(event.data);
        connection.onerror = () => connection.close();
        connection.onclose = () => {
          socket.current = null;
          if (disposed || reconnectAttempts.current >= MAX_RECONNECT_ATTEMPTS) {
            setStatus("disconnected");
            return;
          }
          const delay = Math.min(30_000, 1_000 * 2 ** reconnectAttempts.current);
          reconnectAttempts.current += 1;
          setStatus("reconnecting");
          reconnectTimer.current = setTimeout(() => void connect(), delay);
        };
      } catch {
        if (!disposed) {
          reconnectAttempts.current += 1;
          if (reconnectAttempts.current <= MAX_RECONNECT_ATTEMPTS) {
            reconnectTimer.current = setTimeout(() => void connect(), Math.min(30_000, 1_000 * 2 ** reconnectAttempts.current));
          } else {
            setStatus("disconnected");
          }
        }
      }
    }

    function handleMessage(raw: string) {
      let message: Partial<RealtimeMessage> & { type?: string };
      try {
        message = JSON.parse(raw) as Partial<RealtimeMessage> & { type?: string };
      } catch {
        return;
      }
      if (message.type === "system.heartbeat") {
        socket.current?.send(JSON.stringify({ type: "pong" }));
        return;
      }
      if (!message.id || !message.type || !message.entity_id || typeof message.version !== "number") return;
      if (seenMessages.current.has(message.id)) return;
      seenMessages.current.add(message.id);
      if (seenMessages.current.size > MAX_SEEN_MESSAGES) {
        const oldest = seenMessages.current.values().next().value;
        if (oldest) seenMessages.current.delete(oldest);
      }
      const versionKey = `${message.type}:${message.entity_id}`;
      if ((versions.current.get(versionKey) ?? -1) >= message.version) return;
      versions.current.set(versionKey, message.version);
      const [entity, action] = message.type.split(".");
      if (entity === "event" && action === "created") {
        setNewEventCount((count) => count + 1);
        void queryClient.invalidateQueries({ queryKey: ["dashboard", "summary"] });
      }
      if (entity === "alert") {
        void queryClient.invalidateQueries({ queryKey: ["dashboard", "summary"] });
        void queryClient.invalidateQueries({ queryKey: ["incidents"] });
      }
      if (entity === "incident") {
        void queryClient.invalidateQueries({ queryKey: ["dashboard", "summary"] });
        void queryClient.invalidateQueries({ queryKey: ["incidents"] });
        void queryClient.invalidateQueries({ queryKey: ["incidents", message.entity_id] });
      }
      if (entity === "investigation") {
        const incidentId = typeof message.payload?.incident_id === "string" ? message.payload.incident_id : undefined;
        void queryClient.invalidateQueries({ queryKey: ["investigations", message.entity_id] });
        if (incidentId) void queryClient.invalidateQueries({ queryKey: ["incidents", incidentId, "investigations"] });
      }
    }

    void connect();
    return () => {
      disposed = true;
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      socket.current?.close();
      socket.current = null;
    };
  }, [authStatus, queryClient]);

  return <RealtimeContext value={{ status, newEventCount, clearNewEvents: () => setNewEventCount(0) }}>{children}</RealtimeContext>;
}

export function useRealtime() {
  const context = useContext(RealtimeContext);
  if (!context) throw new Error("useRealtime must be used inside RealtimeProvider");
  return context;
}