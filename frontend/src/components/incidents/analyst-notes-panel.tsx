"use client";

import { Edit3, FileText, Save } from "lucide-react";
import { useState } from "react";
import { useAuth } from "@/components/providers/auth-provider";
import { useCreateIncidentNote, useIncidentNotes, useUpdateIncidentNote } from "@/lib/api/hooks";
import type { IncidentNote, getIncident } from "@/lib/api/resources";
import { hasPermission } from "@/lib/auth/permissions";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/data-state";

type Incident = Awaited<ReturnType<typeof getIncident>>;

export function AnalystNotesPanel({ incidentId, initialNotes }: { incidentId: string; initialNotes: Incident["notes"] }) {
  const { user } = useAuth();
  const notes = useIncidentNotes(incidentId);
  const create = useCreateIncidentNote(incidentId);
  const update = useUpdateIncidentNote(incidentId);
  const [content, setContent] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingContent, setEditingContent] = useState("");
  const canWrite = Boolean(user && hasPermission(user.role_name, "incidents:write"));
  const items: IncidentNote[] = notes.data ?? initialNotes;

  function submitNote() {
    if (content.trim().length < 1 || content.length > 10000) return;
    create.mutate(content.trim(), { onSuccess: () => setContent("") });
  }

  function submitEdit(note: IncidentNote) {
    if (editingContent.trim().length < 1 || editingContent.length > 10000) return;
    update.mutate({ noteId: note.id, content: editingContent.trim() }, { onSuccess: () => setEditingId(null) });
  }

  return (
    <section className="panel incident-panel">
      <div className="panel-heading"><div><p className="eyebrow">Analyst record</p><h2>Notes</h2></div><FileText size={19} /></div>
      {notes.isLoading ? <LoadingState label="Loading notes" /> : null}
      {notes.isError ? <ErrorState error={notes.error instanceof Error ? notes.error : new Error("Notes could not be loaded.")} onRetry={() => void notes.refetch()} /> : null}
      {!notes.isLoading && !notes.isError && items.length === 0 ? <EmptyState title="No analyst notes" description="Capture decisions, evidence gaps, and handoff context here." /> : null}
      <div className="notes-list">{items.map((note) => <article className="note-item" key={note.id}>{editingId === note.id ? <><textarea value={editingContent} maxLength={10000} onChange={(event) => setEditingContent(event.target.value)} aria-label="Edit analyst note" /><button className="secondary-button" type="button" onClick={() => submitEdit(note)} disabled={update.isPending}><Save size={14} /> Save note</button></> : <><p>{note.content}</p><small>{new Date(note.created_at).toLocaleString()}</small>{canWrite && (user?.id === note.author_id || user?.role_name === "admin") ? <button className="icon-button note-edit" type="button" aria-label="Edit note" onClick={() => { setEditingId(note.id); setEditingContent(note.content); }}><Edit3 size={14} /></button> : null}</>}</article>)}</div>
      {canWrite ? <div className="note-composer"><textarea value={content} maxLength={10000} placeholder="Add analyst context..." onChange={(event) => setContent(event.target.value)} aria-label="New analyst note" /><div><small>{content.length}/10000</small><button className="secondary-button" type="button" onClick={submitNote} disabled={create.isPending || content.trim().length === 0}><Save size={14} /> Add note</button></div></div> : <p className="panel-empty">Viewer access is read-only for analyst notes.</p>}
      {create.isError || update.isError ? <p className="inline-error">{(create.error ?? update.error) instanceof Error ? (create.error ?? update.error)?.message : "The note could not be saved."}</p> : null}
    </section>
  );
}