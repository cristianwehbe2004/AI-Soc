import type { components } from "./schema";
import { apiRequest } from "./client";

type EventResponse = components["schemas"]["EventResponse"];
type EventListResponse = components["schemas"]["EventListResponse"];
type IncidentListResponse = components["schemas"]["IncidentListResponse"];
type IncidentDetailResponse = components["schemas"]["IncidentDetail"];
type InvestigationResponse = components["schemas"]["InvestigationResponse"];
type InvestigationListResponse = components["schemas"]["InvestigationListResponse"];
type MitreTechniqueResponse = components["schemas"]["MitreTechniqueResponse"];
type MitreTechniqueListResponse = components["schemas"]["MitreTechniqueListResponse"];
type RuleTechniqueResponse = components["schemas"]["RuleTechniqueResponse"];

export interface DashboardSummary {
  events_total: number;
  incidents_open: number;
  alerts_active: number;
  investigations_active: number;
  model_status: string;
  model_version: string | null;
  as_of: string;
}

export interface IncidentNote {
  id: string;
  incident_id: string;
  author_id: string;
  content: string;
  created_at: string;
  updated_at: string;
}

export interface IncidentML {
  status: "available" | "unavailable";
  model_version: string | null;
  feature_version: string | null;
  score: number | null;
  threshold: number | null;
  is_anomaly: boolean | null;
  features: Record<string, number>;
  explanation: string[];
  message: string | null;
}

export interface RealtimeTicket {
  ticket: string;
  expires_in: number;
}

export interface EventFilters {
  start_time?: string;
  end_time?: string;
  event_type?: string;
  category?: string;
  source_ip?: string;
  username?: string;
  severity?: string;
  limit?: number;
  offset?: number;
}

export interface IncidentFilters {
  status?: string;
  severity?: string;
  username?: string;
  source_ip?: string;
  limit?: number;
  offset?: number;
}

export interface MitreFilters {
  tactic?: string;
  search?: string;
  limit?: number;
  offset?: number;
}

function withQuery(path: string, values: object) {
  const query = new URLSearchParams();
  Object.entries(values as Record<string, string | number | undefined>).forEach(([key, value]) => {
    if (value !== undefined && value !== "") query.set(key, String(value));
  });
  const encoded = query.toString();
  return encoded ? `${path}?${encoded}` : path;
}

export function getDashboardSummary() {
  return apiRequest<DashboardSummary>("/dashboard/summary");
}

export function createRealtimeTicket() {
  return apiRequest<RealtimeTicket>("/auth/realtime-ticket", { method: "POST" });
}

export function listEvents(filters: EventFilters = {}) {
  return apiRequest<EventListResponse>(withQuery("/events", filters));
}

export function getEvent(eventId: string) {
  return apiRequest<EventResponse>(`/events/${encodeURIComponent(eventId)}`);
}

export function listIncidents(filters: IncidentFilters = {}) {
  return apiRequest<IncidentListResponse>(withQuery("/incidents", filters));
}

export function getIncident(incidentId: string) {
  return apiRequest<IncidentDetailResponse & { notes: IncidentNote[] }>(`/incidents/${incidentId}`);
}

export function getIncidentML(incidentId: string) {
  return apiRequest<IncidentML>(`/incidents/${incidentId}/ml`);
}

export function listIncidentNotes(incidentId: string) {
  return apiRequest<IncidentNote[]>(`/incidents/${incidentId}/notes`);
}

export function createIncidentNote(incidentId: string, content: string) {
  return apiRequest<IncidentNote>(`/incidents/${incidentId}/notes`, {
    method: "POST",
    body: JSON.stringify({ content }),
  });
}

export function updateIncidentNote(incidentId: string, noteId: string, content: string) {
  return apiRequest<IncidentNote>(`/incidents/${incidentId}/notes/${noteId}`, {
    method: "PATCH",
    body: JSON.stringify({ content }),
  });
}

export function listInvestigations(incidentId: string) {
  return apiRequest<InvestigationListResponse>(`/incidents/${incidentId}/investigations`);
}

export function getInvestigation(investigationId: string) {
  return apiRequest<InvestigationResponse>(`/investigations/${investigationId}`);
}

export function requestInvestigation(incidentId: string) {
  return apiRequest<InvestigationResponse>(`/incidents/${incidentId}/investigations`, { method: "POST" });
}

export function listMitreTechniques(filters: MitreFilters = {}) {
  return apiRequest<MitreTechniqueListResponse>(withQuery("/mitre/techniques", filters));
}

export function getMitreTechnique(externalId: string) {
  return apiRequest<MitreTechniqueResponse>(`/mitre/techniques/${encodeURIComponent(externalId)}`);
}

export function getRuleTechniques(ruleId: string) {
  return apiRequest<RuleTechniqueResponse>(`/mitre/rules/${encodeURIComponent(ruleId)}/techniques`);
}