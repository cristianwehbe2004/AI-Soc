import { SectionPlaceholder } from "@/components/ui/section-placeholder";
import { Activity } from "lucide-react";

export default function EventsPage() {
  return <SectionPlaceholder eyebrow="Telemetry" title="Security events" description="Explore normalized authentication, network, application, and cloud telemetry." icon={Activity} />;
}
