import { SectionPlaceholder } from "@/components/ui/section-placeholder";
import { ScrollText } from "lucide-react";

export default function AuditPage() {
  return <SectionPlaceholder eyebrow="Administration" title="Security audit log" description="Inspect authentication, authorization, ingestion, and administrative activity." icon={ScrollText} />;
}
