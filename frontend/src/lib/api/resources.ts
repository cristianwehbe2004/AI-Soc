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

export interface NetworkObservation {
  source_zone: "internet" | "dmz" | "internal" | "restricted" | "unknown";
  destination_zone: "internet" | "dmz" | "internal" | "restricted" | "unknown";
  destination_port: number;
  protocol: "tcp" | "udp";
  disposition: "allowed" | "blocked" | "unknown";
}

export interface IncidentEvidencePayload {
  kind: "analyst_observation" | "network_observation" | "asset_configuration" | "identity_activity" | "vulnerability_report";
  source: string;
  summary: string;
  observed_at?: string | null;
  network?: NetworkObservation | null;
}

export interface IncidentEvidence extends IncidentEvidencePayload {
  id: string;
  incident_id: string;
  submitted_by: string;
  sensitive_redacted: boolean;
  created_at: string;
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

export interface IncidentClassification {
  status: string;
  model_version: string | null;
  probabilities?: Record<string, number>;
  reason?: string | null;
}

export type ResponseActionType = "revoke_app_sessions" | "disable_aws_access_key" | "block_s3_public_access";
export interface ResponseAction {
  id: string;
  incident_id: string;
  action_type: ResponseActionType;
  target: string;
  account_id: string | null;
  status: "proposed" | "approved" | "running" | "succeeded" | "failed" | "rejected";
  rationale: string;
  impact: string;
  evidence_refs: string[];
  proposed_by: string;
  approved_by: string | null;
  result: Record<string, unknown> | null;
  error: string | null;
  created_at: string;
  updated_at: string;
}

export interface ResponseActionPayload {
  action_type: ResponseActionType;
  target: string;
  account_id: string | null;
  rationale: string;
  impact: string;
  evidence_refs: string[];
  idempotency_key: string;
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

export interface IncidentCreatePayload {
  title: string;
  description: string;
  severity: "low" | "medium" | "high" | "critical";
  primary_username?: string;
  primary_source_ip?: string;
  preset_scenario?: "custom" | "brute_force" | "privilege_escalation" | "data_exfiltration";
}

export function createIncident(payload: IncidentCreatePayload) {
  return apiRequest<IncidentDetailResponse>("/incidents", {
    method: "POST",
    body: JSON.stringify(payload),
  });
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

export function listIncidentEvidence(incidentId: string) {
  return apiRequest<IncidentEvidence[]>(`/incidents/${incidentId}/evidence`);
}

export function createIncidentEvidence(incidentId: string, payload: IncidentEvidencePayload) {
  return apiRequest<IncidentEvidence>(`/incidents/${incidentId}/evidence`, { method: "POST", body: JSON.stringify(payload) });
}

export function getIncidentClassification(incidentId: string) {
  return apiRequest<IncidentClassification>(`/incidents/${incidentId}/classification`);
}

export function listResponseActions(incidentId: string) {
  return apiRequest<ResponseAction[]>(`/incidents/${incidentId}/response-actions`);
}

export function proposeResponseAction(incidentId: string, payload: ResponseActionPayload) {
  return apiRequest<ResponseAction>(`/incidents/${incidentId}/response-actions`, { method: "POST", body: JSON.stringify(payload) });
}

export function decideResponseAction(actionId: string, decision: "approve" | "reject") {
  return apiRequest<ResponseAction>(`/response-actions/${actionId}/${decision}`, { method: "POST" });
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
