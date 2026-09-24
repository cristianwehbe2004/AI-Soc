import { SectionPlaceholder } from "@/components/ui/section-placeholder";
import { Fingerprint } from "lucide-react";

export default function MitrePage() {
  return <SectionPlaceholder eyebrow="ATT&CK context" title="MITRE techniques" description="Trace deterministic detection rules to tactics and techniques." icon={Fingerprint} />;
}
