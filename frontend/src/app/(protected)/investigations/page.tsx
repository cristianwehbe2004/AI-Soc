import Link from "next/link";
import { ArrowRight, BrainCircuit } from "lucide-react";
import { PageHeading } from "@/components/ui/page-heading";

export default function InvestigationsPage() {
  return <div className="page-stack"><PageHeading eyebrow="AI analysis" title="Incident investigations" description="Investigations are launched from an incident so every narrative stays anchored to its evidence." action={<BrainCircuit size={22} />} /><section className="panel scoped-index"><div className="scoped-index-icon"><BrainCircuit size={30} /></div><p className="eyebrow">Incident-scoped workflow</p><h2>Choose an incident to investigate</h2><p>The investigation queue belongs to each incident. Open the incident queue to review existing analyses or request a new one.</p><Link className="primary-link" href="/incidents">Open incident queue <ArrowRight size={15} /></Link></section></div>;
}
