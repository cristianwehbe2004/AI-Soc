"use client";

import Link from "next/link";
import { ArrowLeft, CheckCircle2, CircleAlert } from "lucide-react";
import { useParams } from "next/navigation";
import { useInvestigation } from "@/lib/api/hooks";
import { ErrorState, LoadingState } from "@/components/ui/data-state";
import { PageHeading } from "@/components/ui/page-heading";

export default function InvestigationDetailPage() {
  const params = useParams<{ investigationId: string }>();
  const investigation = useInvestigation(params.investigationId);
  if (investigation.isLoading) return <LoadingState label="Loading investigation" />;
  if (investigation.isError || !investigation.data) return <ErrorState error={investigation.error instanceof Error ? investigation.error : new Error("Investigation not found.")} onRetry={() => void investigation.refetch()} />;

  const item = investigation.data;
  const result = item.result;
  return <div className="page-stack">
    <Link className="back-link" href={`/incidents/${item.incident_id}`}><ArrowLeft size={15} /> Back to incident</Link>
    <PageHeading eyebrow="AI investigation" title={result?.executive_summary ?? `${item.status} investigation`} description={`${item.provider} · ${item.model}`} action={<span className={`status-badge status-${item.status}`}>{item.status}</span>} />
    {item.status === "failed" ? <section className="panel result-warning"><CircleAlert size={20} /><div><h2>Investigation failed</h2><p>{item.error ?? "The provider did not return a valid result."}</p>{item.validation_errors.length ? <ul>{item.validation_errors.map((error) => <li key={error}>{error}</li>)}</ul> : null}</div></section> : null}
    {result ? <div className="result-grid">
      <section className="panel result-section result-span-two"><p className="eyebrow">Narrative</p><h2>Attack story</h2><p>{result.attack_story}</p><div className="confidence-bar"><span style={{ width: `${Math.round(result.confidence * 100)}%` }} /><strong>{Math.round(result.confidence * 100)}% model confidence · analyst verification required</strong></div></section>
      <section className="panel result-section"><p className="eyebrow">Evidence analysis</p><h2>Findings</h2><div className="result-list">{result.findings.map((finding, index) => <article key={`${finding.title}-${index}`}><strong>{finding.title}</strong><span className={`severity-badge severity-${finding.severity}`}>{finding.severity} · {Math.round(finding.confidence * 100)}%</span><p>{finding.summary}</p><small>Sources: {finding.evidence_refs?.join(", ") || "None supplied"}</small></article>)}</div></section>
      <section className="panel result-section"><p className="eyebrow">Risk analysis</p><h2>{result.risk_analysis.score} / 100</h2><span className={`severity-badge severity-${result.risk_analysis.severity}`}>{result.risk_analysis.severity}</span><p>{result.risk_analysis.rationale}</p><div className="result-list compact">{(result.risk_analysis.factors ?? []).map((factor) => <span key={factor}>{factor}</span>)}</div></section>
      <section className="panel result-section result-span-two"><p className="eyebrow">Coverage limits</p><h2>Evidence gaps to verify</h2><ul>{result.evidence_gaps.length ? result.evidence_gaps.map((gap, index) => <li key={`${index}-${gap}`}>{gap}</li>) : <li>No explicit gaps were returned; this is not proof the investigation is complete.</li>}</ul></section>
      <section className="panel result-section result-span-two"><p className="eyebrow">Defensive action</p><h2>Recommendations</h2><p>Review impact and submit a response proposal from the incident page. AI recommendations do not change network or AWS controls.</p><div className="recommendation-grid">{result.recommendations.map((recommendation, index) => <article key={`${recommendation.title}-${index}`}><div><strong>{recommendation.title}</strong><span className="status-badge status-investigating">{recommendation.priority}</span></div><p>{recommendation.rationale}</p><ul>{recommendation.actions.map((action) => <li key={action}>{action}</li>)}</ul><small>Sources: {recommendation.evidence_refs?.join(", ") || "None supplied"}</small></article>)}</div></section>
      <section className="panel result-section result-span-two"><p className="eyebrow">MITRE context</p><h2>Mapped techniques</h2><div className="technique-list">{result.mitre_context.map((technique) => <article className="technique-item" key={technique.technique_id}><strong>{technique.name}</strong><span>{technique.technique_id} · {technique.tactics.join(" / ")}</span><p>{technique.relevance}</p></article>)}</div></section>
    </div> : <section className="panel scoped-index"><CheckCircle2 size={24} /><h2>Analysis is {item.status}</h2><p>The result will appear here when the investigation worker completes.</p></section>}
  </div>;
}
