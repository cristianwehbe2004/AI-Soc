import { PageHeading } from "@/components/ui/page-heading";
import { Activity, BrainCircuit, Radar, ShieldCheck, TrendingUp } from "lucide-react";
import type { CSSProperties } from "react";

const metrics = [
  { label: "Events observed", value: "—", note: "Live data in Sprint 10", icon: Activity },
  { label: "Open incidents", value: "—", note: "Correlation API ready", icon: Radar },
  { label: "Detection coverage", value: "6", note: "5 rules + ML anomaly", icon: ShieldCheck },
  { label: "AI investigations", value: "—", note: "Analyst initiated", icon: BrainCircuit },
];

export default function DashboardPage() {
  return (
    <div className="page-stack dashboard-page">
      <PageHeading
        eyebrow="Operational overview"
        title="Security posture, without the noise."
        description="A focused command surface for detection, correlation, and evidence-led investigation."
        action={<span className="status-pill live"><span /> Monitoring enabled</span>}
      />

      <section className="metric-grid" aria-label="SOC metrics">
        {metrics.map(({ label, value, note, icon: Icon }, index) => (
          <article className="metric-card panel" key={label} style={{ "--delay": `${index * 70}ms` } as CSSProperties}>
            <div className="metric-top"><span>{label}</span><Icon size={18} /></div>
            <strong>{value}</strong>
            <p>{note}</p>
          </article>
        ))}
      </section>

      <section className="dashboard-grid">
        <article className="panel priority-panel">
          <div className="panel-heading">
            <div><p className="eyebrow">Priority queue</p><h2>Incident triage</h2></div>
            <span className="status-pill neutral">Sprint 10</span>
          </div>
          <div className="radar-placeholder">
            <div className="radar-rings"><span /><span /><span /></div>
            <div><strong>Awaiting incident feed</strong><p>The protected incident endpoint is ready for the next UI sprint.</p></div>
          </div>
        </article>

        <article className="panel activity-panel">
          <div className="panel-heading">
            <div><p className="eyebrow">Pipeline</p><h2>Detection flow</h2></div>
            <TrendingUp size={20} />
          </div>
          <ol className="pipeline-list">
            <li><span>01</span><div><strong>Telemetry intake</strong><p>Service-key protected</p></div><i className="ok-dot" /></li>
            <li><span>02</span><div><strong>Rules + anomaly model</strong><p>Inline evaluation</p></div><i className="ok-dot" /></li>
            <li><span>03</span><div><strong>Incident correlation</strong><p>Identity-aware grouping</p></div><i className="ok-dot" /></li>
            <li><span>04</span><div><strong>AI investigation</strong><p>Analyst requested</p></div><i className="idle-dot" /></li>
          </ol>
        </article>

        <article className="panel span-two coverage-panel">
          <div><p className="eyebrow">Coverage map</p><h2>Evidence layers connected</h2></div>
          <div className="coverage-track">
            {["Events", "Rules", "ML", "Incidents", "MITRE", "AI"].map((item, index) => (
              <div key={item}><span>{String(index + 1).padStart(2, "0")}</span><strong>{item}</strong></div>
            ))}
          </div>
        </article>
      </section>
    </div>
  );
}
