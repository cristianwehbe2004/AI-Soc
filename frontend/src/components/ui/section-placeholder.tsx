import { ArrowUpRight, type LucideIcon } from "lucide-react";
import { PageHeading } from "./page-heading";

export function SectionPlaceholder({
  eyebrow,
  title,
  description,
  icon: Icon,
  sprint = "Sprint 10",
}: {
  eyebrow: string;
  title: string;
  description: string;
  icon: LucideIcon;
  sprint?: string;
}) {
  return (
    <div className="page-stack">
      <PageHeading eyebrow={eyebrow} title={title} description={description} />
      <section className="empty-state panel">
        <div className="empty-icon"><Icon size={30} /></div>
        <span className="status-pill neutral">Foundation ready</span>
        <h2>The secure route and API contract are connected.</h2>
        <p>Data-rich controls and operational workflows arrive in {sprint}.</p>
        <span className="future-label">Next capability <ArrowUpRight size={14} /></span>
      </section>
    </div>
  );
}
