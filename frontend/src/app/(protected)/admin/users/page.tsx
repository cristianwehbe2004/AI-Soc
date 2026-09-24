import { SectionPlaceholder } from "@/components/ui/section-placeholder";
import { Users } from "lucide-react";

export default function UsersPage() {
  return <SectionPlaceholder eyebrow="Administration" title="Users and roles" description="Manage human identities, fixed SOC roles, and account activation." icon={Users} />;
}
