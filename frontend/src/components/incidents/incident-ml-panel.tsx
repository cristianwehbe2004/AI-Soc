import { BrainCircuit, Gauge } from "lucide-react";
import { useIncidentML } from "@/lib/api/hooks";
import { ErrorState, LoadingState } from "@/components/ui/data-state";

export function IncidentMLPanel({ incidentId }: { incidentId: string }) {
  const result = useIncidentML(incidentId);
  return (
    <section className="panel incident-panel">
      <div className="panel-heading"><div><p className="eyebrow">Anomaly model</p><h2>ML evidence</h2></div><BrainCircuit size={19} /></div>
      {result.isLoading ? <LoadingState label="Scoring incident evidence" /> : null}
      {result.isError ? <ErrorState error={result.error instanceof Error ? result.error : new Error("ML scoring failed.")} onRetry={() => void result.refetch()} /> : null}
      {result.data?.status === "unavailable" ? <div className="panel-empty"><strong>Model unavailable</strong><br />{result.data.message ?? "No active model is available for this incident."}</div> : null}
      {result.data?.status === "available" ? <div className="ml-content"><div className="ml-score"><Gauge size={17} /><div><span>Anomaly score</span><strong>{result.data.score?.toFixed(3)}</strong></div><em>{result.data.is_anomaly ? "Anomalous" : "Within baseline"}</em></div><div className="ml-meta"><span>Model {result.data.model_version}</span><span>Features {result.data.feature_version}</span><span>Threshold {result.data.threshold?.toFixed(3)}</span></div><div className="explanation-list"><p className="eyebrow">Top feature signals</p>{result.data.explanation.map((item) => <span key={item}>{item}</span>)}</div></div> : null}
    </section>
  );
}