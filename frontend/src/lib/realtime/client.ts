export type RealtimeStatus = "connecting" | "connected" | "reconnecting" | "disconnected";

export interface RealtimeMessage {
  id: string;
  type: string;
  entity_id: string;
  occurred_at: string;
  version: number;
  payload: Record<string, unknown>;
}

export function realtimeUrl(ticket: string) {
  const configuredUrl = process.env.NEXT_PUBLIC_REALTIME_WS_URL;
  const url = new URL(configuredUrl ?? window.location.origin, window.location.origin);
  if (!configuredUrl) url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  url.pathname = process.env.NEXT_PUBLIC_REALTIME_WS_PATH || "/api/v1/realtime";
  url.searchParams.set("ticket", ticket);
  return url.toString();
}