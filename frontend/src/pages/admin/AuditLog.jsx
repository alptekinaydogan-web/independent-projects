import { useEffect, useMemo, useState } from "react";
import api from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

const ACTION_LABELS = {
  "campaign.create": "Created banner campaign",
  "sponsorship.create": "Confirmed TV sponsorship",
  "proposal.create": "Submitted TV proposal",
  "proposal.approved": "Approved TV proposal",
  "proposal.rejected": "Rejected TV proposal",
  "proposal.in_review": "Reset proposal to review",
  "representative.create": "Created representative",
  "representative.update": "Updated representative",
  "representative.delete": "Removed representative",
  "inventory.update": "Updated banner inventory",
  "tv_project.create": "Published TV project",
  "tv_project.update": "Updated TV project",
  "tv_project.delete": "Deleted TV project",
  "tv_project.status.active": "Reactivated TV project",
  "tv_project.status.draft": "Moved TV project to draft",
  "tv_project.status.closed": "Closed TV project",
  "admin.create": "Created administrator",
  "admin.delete": "Removed administrator",
};

const ACTOR_ROLES = ["all", "owner", "admin", "representative"];
const ENTITY_TYPES = ["all", "campaign", "sponsorship", "proposal", "user", "banner_inventory", "tv_project"];

function relativeTime(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  const s = Math.floor((Date.now() - d.getTime()) / 1000);
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s/60)}m ago`;
  if (s < 86400) return `${Math.floor(s/3600)}h ago`;
  return `${Math.floor(s/86400)}d ago`;
}

export default function AuditLog() {
  const [items, setItems] = useState([]);
  const [entityType, setEntityType] = useState("all");
  const [actorRole, setActorRole] = useState("all");

  const load = () => {
    const params = new URLSearchParams();
    if (entityType !== "all") params.set("entity_type", entityType);
    if (actorRole !== "all") params.set("actor_role", actorRole);
    api.get(`/admin/audit-log?${params.toString()}`).then(r => setItems(r.data));
  };
  useEffect(load, [entityType, actorRole]);

  return (
    <div>
      <PageHeader eyebrow="Compliance" title="Audit log"
        description="Every state-changing action taken on Independent Media Hub — by representatives and administrators alike. Kept as an immutable stream for accountability."
      />
      <div className="px-10 py-10 space-y-4">
        <div className="flex gap-3 items-center">
          <div>
            <div className="imh-eyebrow mb-1">Entity</div>
            <Select value={entityType} onValueChange={setEntityType}>
              <SelectTrigger className="w-[220px] rounded-none h-10" data-testid="audit-entity-filter"><SelectValue /></SelectTrigger>
              <SelectContent>{ENTITY_TYPES.map(e => <SelectItem key={e} value={e}>{e === "all" ? "All entities" : e}</SelectItem>)}</SelectContent>
            </Select>
          </div>
          <div>
            <div className="imh-eyebrow mb-1">Actor role</div>
            <Select value={actorRole} onValueChange={setActorRole}>
              <SelectTrigger className="w-[200px] rounded-none h-10" data-testid="audit-role-filter"><SelectValue /></SelectTrigger>
              <SelectContent>{ACTOR_ROLES.map(r => <SelectItem key={r} value={r}>{r === "all" ? "All roles" : r}</SelectItem>)}</SelectContent>
            </Select>
          </div>
          <div className="ml-auto text-[11px] font-mono-imh text-[#52525B]" data-testid="audit-count">{items.length} entries</div>
        </div>

        <div className="imh-card overflow-hidden" data-testid="audit-table">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left border-b border-[#E4E4E1] bg-[#F9F9F6]">
                <Th>When</Th><Th>Actor</Th><Th>Role</Th><Th>Action</Th><Th>Entity</Th><Th>Details</Th>
              </tr>
            </thead>
            <tbody>
              {items.map(a => (
                <tr key={a.id} className="border-b border-[#E4E4E1] last:border-b-0" data-testid={`audit-${a.id}`}>
                  <Td className="font-mono-imh text-xs text-[#52525B] whitespace-nowrap">{relativeTime(a.created_at)}</Td>
                  <Td>
                    <div>{a.actor_name}</div>
                    <div className="font-mono-imh text-[10px] text-[#A1A1AA]">{a.actor_email}</div>
                  </Td>
                  <Td>
                    <span className="text-[10px] uppercase tracking-widest font-mono-imh px-2 py-0.5"
                      style={{
                        background: a.actor_role === "owner" ? "#0A1128" : a.actor_role === "admin" ? "#E6F2EA" : "#F5F0E1",
                        color: a.actor_role === "owner" ? "#FFFFFF" : a.actor_role === "admin" ? "#166534" : "#B45309",
                      }}>{a.actor_role}</span>
                  </Td>
                  <Td className="font-editorial">{ACTION_LABELS[a.action] || a.action}</Td>
                  <Td className="font-mono-imh text-xs text-[#52525B]">{a.entity_type}</Td>
                  <Td className="font-mono-imh text-[11px] text-[#0A0A0A] max-w-[360px] truncate">
                    {a.details && Object.keys(a.details).length > 0 ? JSON.stringify(a.details) : "—"}
                  </Td>
                </tr>
              ))}
              {items.length === 0 && <tr><Td colSpan={6} className="text-center py-16 text-[#52525B]">No audit entries match the current filter.</Td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

const Th = ({ children }) => <th className="px-6 py-4 text-[11px] uppercase tracking-widest text-[#52525B] font-medium">{children}</th>;
const Td = ({ children, className = "", colSpan }) => <td colSpan={colSpan} className={`px-6 py-4 text-[#0A0A0A] ${className}`}>{children}</td>;
