"use client";

import Link from "next/link";
import { ArrowLeft, ExternalLink, Fingerprint } from "lucide-react";
import { useParams } from "next/navigation";
import { useMitreTechnique } from "@/lib/api/hooks";
import { ErrorState, LoadingState } from "@/components/ui/data-state";
import { PageHeading } from "@/components/ui/page-heading";

export default function MitreDetailPage() {
  const params = useParams<{ externalId: string }>();
  const externalId = decodeURIComponent(params.externalId);
  const technique = useMitreTechnique(externalId);
  if (technique.isLoading) return <LoadingState label="Loading technique" />;
  if (technique.isError || !technique.data) return <ErrorState error={technique.error instanceof Error ? technique.error : new Error("Technique not found.")} onRetry={() => void technique.refetch()} />;
  const item = technique.data;
  return <div className="page-stack"><Link className="back-link" href="/mitre"><ArrowLeft size={15} /> Back to MITRE catalog</Link><PageHeading eyebrow="Technique detail" title={item.name} description={item.external_id} action={<Fingerprint size={22} />} /><section className="panel detail-panel technique-detail"><div className="technique-detail-meta"><span>{item.tactics.join(" / ")}</span><span>{item.platforms.join(", ")}</span><span>{item.is_subtechnique ? `Subtechnique of ${item.parent_external_id ?? "parent technique"}` : "Top-level technique"}</span></div><p>{item.description}</p><a className="timeline-link" href={item.source_url} target="_blank" rel="noreferrer">Open ATT&CK source <ExternalLink size={13} /></a></section></div>;
}