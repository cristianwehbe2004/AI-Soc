"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createIncident,
  createIncidentNote,
  getDashboardSummary,
  getEvent,
  getIncident,
  getIncidentML,
  getIncidentClassification,
  getInvestigation,
  getMitreTechnique,
  getRuleTechniques,
  listEvents,
  listIncidentNotes,
  listIncidents,
  listInvestigations,
  listMitreTechniques,
  listResponseActions,
  proposeResponseAction,
  decideResponseAction,
  requestInvestigation,
  updateIncidentNote,
  type EventFilters,
  type IncidentCreatePayload,
  type IncidentFilters,
  type MitreFilters,
  type ResponseActionPayload,
} from "./resources";

export function useDashboardSummary() {
  return useQuery({ queryKey: ["dashboard", "summary"], queryFn: getDashboardSummary });
}

export function useEvents(filters: EventFilters = {}) {
  return useQuery({ queryKey: ["events", filters], queryFn: () => listEvents(filters) });
}

export function useEvent(eventId: string | undefined) {
  return useQuery({ queryKey: ["events", eventId], queryFn: () => getEvent(eventId!), enabled: Boolean(eventId) });
}

export function useIncidents(filters: IncidentFilters = {}) {
  return useQuery({ queryKey: ["incidents", filters], queryFn: () => listIncidents(filters) });
}

export function useCreateIncident() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: IncidentCreatePayload) => createIncident(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["incidents"] });
    },
  });
}

export function useIncident(incidentId: string | undefined) {
  return useQuery({ queryKey: ["incidents", incidentId], queryFn: () => getIncident(incidentId!), enabled: Boolean(incidentId) });
}


export function useIncidentML(incidentId: string | undefined) {
  return useQuery({ queryKey: ["incidents", incidentId, "ml"], queryFn: () => getIncidentML(incidentId!), enabled: Boolean(incidentId) });
}

export function useIncidentClassification(incidentId: string | undefined) {
  return useQuery({ queryKey: ["incidents", incidentId, "classification"], queryFn: () => getIncidentClassification(incidentId!), enabled: Boolean(incidentId) });
}

export function useResponseActions(incidentId: string) {
  return useQuery({ queryKey: ["incidents", incidentId, "response-actions"], queryFn: () => listResponseActions(incidentId) });
}

export function useProposeResponseAction(incidentId: string) {
  const queryClient = useQueryClient();
  return useMutation({ mutationFn: (payload: ResponseActionPayload) => proposeResponseAction(incidentId, payload), onSuccess: () => { void queryClient.invalidateQueries({ queryKey: ["incidents", incidentId, "response-actions"] }); } });
}

export function useDecideResponseAction(incidentId: string) {
  const queryClient = useQueryClient();
  return useMutation({ mutationFn: ({ actionId, decision }: { actionId: string; decision: "approve" | "reject" }) => decideResponseAction(actionId, decision), onSuccess: () => { void queryClient.invalidateQueries({ queryKey: ["incidents", incidentId, "response-actions"] }); } });
}

export function useIncidentNotes(incidentId: string | undefined) {
  return useQuery({ queryKey: ["incidents", incidentId, "notes"], queryFn: () => listIncidentNotes(incidentId!), enabled: Boolean(incidentId) });
}

export function useCreateIncidentNote(incidentId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (content: string) => createIncidentNote(incidentId, content),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["incidents", incidentId] });
    },
  });
}

export function useUpdateIncidentNote(incidentId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ noteId, content }: { noteId: string; content: string }) => updateIncidentNote(incidentId, noteId, content),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["incidents", incidentId] });
    },
  });
}

export function useInvestigations(incidentId: string | undefined) {
  return useQuery({ queryKey: ["incidents", incidentId, "investigations"], queryFn: () => listInvestigations(incidentId!), enabled: Boolean(incidentId) });
}

export function useInvestigation(investigationId: string | undefined) {
  return useQuery({ queryKey: ["investigations", investigationId], queryFn: () => getInvestigation(investigationId!), enabled: Boolean(investigationId) });
}

export function useRequestInvestigation(incidentId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => requestInvestigation(incidentId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["incidents", incidentId, "investigations"] });
    },
  });
}

export function useMitreTechniques(filters: MitreFilters = {}) {
  return useQuery({ queryKey: ["mitre", "techniques", filters], queryFn: () => listMitreTechniques(filters) });
}

export function useMitreTechnique(externalId: string | undefined) {
  return useQuery({ queryKey: ["mitre", "techniques", externalId], queryFn: () => getMitreTechnique(externalId!), enabled: Boolean(externalId) });
}

export function useRuleTechniques(ruleId: string | undefined) {
  return useQuery({ queryKey: ["mitre", "rules", ruleId], queryFn: () => getRuleTechniques(ruleId!), enabled: Boolean(ruleId) });
}
