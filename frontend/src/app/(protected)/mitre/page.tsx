"use client";

import Link from "next/link";
import { Fingerprint, Search } from "lucide-react";
import { useState, type FormEvent } from "react";
import { useMitreTechniques } from "@/lib/api/hooks";
import type { MitreFilters } from "@/lib/api/resources";
import { DataTable } from "@/components/ui/data-table";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/data-state";
import { PageHeading } from "@/components/ui/page-heading";
import { PaginationControls } from "@/components/ui/pagination-controls";

const limit = 20;

function queryError(error: unknown) {
  return error instanceof Error ? error : new Error("The API returned an unknown error.");
}

export default function MitrePage() {
  const [filters, setFilters] = useState<MitreFilters>({ limit, offset: 0 });
  const techniques = useMitreTechniques(filters);

  function applyFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const values = new FormData(event.currentTarget);
    setFilters({ tactic: String(values.get("tactic") || undefined), search: String(values.get("search") || undefined), limit, offset: 0 });
  }

  return (
    <div className="page-stack">
      <PageHeading eyebrow="ATT&CK context" title="MITRE techniques" description="Trace detection rules to tactics and techniques across the active catalog." action={<span className="status-pill neutral"><Fingerprint size={13} /> {techniques.data?.total ?? "—"} techniques</span>} />
      <form className="filter-panel panel" onSubmit={applyFilters}><div className="filter-heading"><div><p className="eyebrow">Technique search</p><h2>Explore ATT&CK</h2></div><button className="secondary-button" type="submit"><Search size={15} /> Search catalog</button></div><div className="filter-grid mitre-filter-grid"><label>Search<input name="search" placeholder="credential access" /></label><label>Tactic<input name="tactic" placeholder="credential-access" /></label></div></form>
      <section className="panel table-panel">
        {techniques.isLoading ? <LoadingState label="Loading MITRE catalog" /> : null}
        {techniques.isError ? <ErrorState error={queryError(techniques.error)} onRetry={() => void techniques.refetch()} /> : null}
        {techniques.data?.items.length === 0 ? <EmptyState title="No techniques found" description="Try a broader tactic or search term." /> : null}
        {techniques.data?.items.length ? <><DataTable label="MITRE techniques"><thead><tr><th>Technique</th><th>Tactics</th><th>Platforms</th><th>Type</th><th>Version</th></tr></thead><tbody>{techniques.data.items.map((technique) => <tr key={technique.external_id}><td><Link className="table-link table-primary" href={`/mitre/${encodeURIComponent(technique.external_id)}`}>{technique.name}</Link><span className="table-subline">{technique.external_id}</span></td><td>{technique.tactics.join(" / ")}</td><td>{technique.platforms.join(", ")}</td><td>{technique.is_subtechnique ? "Subtechnique" : "Technique"}</td><td className="table-mono">{technique.version}</td></tr>)}</tbody></DataTable><PaginationControls total={techniques.data.total} limit={techniques.data.limit} offset={techniques.data.offset} onChange={(offset) => setFilters((current) => ({ ...current, offset }))} /></> : null}
      </section>
    </div>
  );
}
