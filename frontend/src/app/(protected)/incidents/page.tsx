import { SectionPlaceholder } from "@/components/ui/section-placeholder";
import { ShieldAlert } from "lucide-react";

export default function IncidentsPage() {
  return <SectionPlaceholder eyebrow="Correlation" title="Incidents" description="Prioritize correlated credential-compromise activity and its evidence timeline." icon={ShieldAlert} />;
}
