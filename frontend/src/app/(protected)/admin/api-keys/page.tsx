import { SectionPlaceholder } from "@/components/ui/section-placeholder";
import { KeyRound } from "lucide-react";

export default function ApiKeysPage() {
  return <SectionPlaceholder eyebrow="Administration" title="Ingestion API keys" description="Issue and revoke scoped machine credentials for telemetry producers." icon={KeyRound} />;
}
