import { useEffect, useMemo, useState } from "react";
import api from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Search, X } from "lucide-react";

const ACTION_LABELS = {
  "campaign.create": "Created banner campaign",
  "sponsorship.create": "Confirmed TV sponsorship",
  "proposal.create": "Submitted TV proposal",
  "proposal.approved": "Approved TV proposal",
  "proposal.rejected": "Rejected TV proposal",
  "proposal.in_review": "Reset proposal to review",
  "proposal.banner.submitted":         "Submitted banner proposal",
  "proposal.banner.approved":          "Approved banner proposal",
  "proposal.banner.rejected":          "Rejected banner proposal",
  "proposal.banner.revision_requested":"Requested banner revision",
  "proposal.banner.revised":           "Rep resubmitted banner",
  "proposal.banner.archived":          "Archived banner proposal",
  "proposal.banner.unarchived":        "Restored banner proposal",
  "proposal.banner.pdf_emailed":       "Emailed banner proposal PDF",
  "proposal.banner.pdf_email_failed":  "Banner PDF email failed",
  "proposal.sponsorship.submitted":         "Submitted TV sponsorship",
  "proposal.sponsorship.approved":          "Approved TV sponsorship",
  "proposal.sponsorship.rejected":          "Rejected TV sponsorship",
  "proposal.sponsorship.revision_requested":"Requested TV revision",
  "proposal.sponsorship.revised":           "Rep resubmitted sponsorship",
  "proposal.sponsorship.archived":          "Archived TV sponsorship",
  "proposal.sponsorship.unarchived":        "Restored TV sponsorship",
  "proposal.sponsorship.pdf_emailed":       "Emailed sponsorship PDF",
  "proposal.sponsorship.pdf_email_failed":  "Sponsorship PDF email failed",
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

// Predefined action groups exposed as dropdown quick filters. Values ending
// with `*` are sent as prefix filters to the backend.
const ACTION_PRESETS = [
  { value: "all",                                label: "All actions" },
  { value: "proposal.banner.*",                  label: "Banner proposals (all events)" },
  { value: "proposal.sponsorship.*",             label: "TV sponsorships (all events)" },
  { value: "proposal.banner.approved",           label: "· Banner approvals only" },
  { value: "proposal.sponsorship.approved",      label: "· TV approvals only" },
  { value: "proposal.banner.pdf_email*",         label: "· Banner email deliveries" },
  { value: "proposal.sponsorship.pdf_email*",    label: "· TV email deliveries" },
  { value: "tv_project.*",                       label: "TV project management" },
  { value: "representative.*",                   label: "Representative management" },
  { value: "admin.*",                            label: "Admin management" },
  { value: "inventory.*",                        label: "Inventory changes" },
];

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
  const [actionPreset, setActionPreset] = useState("all");
  const [actionQuery, setActionQuery] = useState("");
  const [loading, setLoading] = useState(false);

  // Whichever is more specific wins: free-text search overrides the dropdown.
  const effectiveActionFilter = useMemo(() => {
    const q = actionQuery.trim();
    if (q) return q.includes("*") ? q : `${q}*`;   // free-text always wildcard-suffixed for prefix search
    return actionPreset === "all" ? "" : actionPreset;
  }, [actionPreset, actionQuery]);

  const load = () => {
    const params = new URLSearchParams();
    if (entityType !== "all") params.set("entity_type", entityType);
    if (actorRole !== "all") params.set("actor_role", actorRole);
    if (effectiveActionFilter) params.set("action", effectiveActionFilter);
    params.set("limit", "300");
    setLoading(true);
    api.get(`/admin/audit-log?${params.toString()}`)
       .then(r => setItems(r.data))
       .finally(() => setLoading(false));
  };
  useEffect(load, [entityType, actorRole, effectiveActionFilter]);

  const clearAll = () => {
    setEntityType("all"); setActorRole("all"); setActionPreset("all"); setActionQuery("");
  };
  const hasAnyFilter = entityType !== "all" || actorRole !== "all" || actionPreset !== "all" || actionQuery !== "";

  return (
    <div>
      <PageHeader eyebrow="Compliance" title="Audit log"
        description="Every state-changing action taken on Independent Projects — by representatives and administrators alike. Kept as an immutable stream for accountability."
      />
      <div className="px-10 py-10 space-y-4">
        <div className="imh-card p-4 space-y-3" data-testid="audit-filters">
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-3 items-end">
            <div>
              <div className="imh-eyebrow mb-1">Action</div>
              <Select value={actionPreset} onValueChange={(v) => { setActionPreset(v); setActionQuery(""); }}>
                <SelectTrigger className="w-full rounded-none h-10" data-testid="audit-action-preset"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {ACTION_PRESETS.map(p => (
                    <SelectItem key={p.value} value={p.value}>{p.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="lg:col-span-2">
              <div className="imh-eyebrow mb-1">Search action (prefix)</div>
              <div className="relative">
                <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#A1A1AA]" />
                <Input value={actionQuery}
                       onChange={e => setActionQuery(e.target.value)}
                       placeholder="e.g. proposal.banner or tv_project.status"
                       data-testid="audit-action-search"
                       className="rounded-none h-10 pl-9 pr-9 font-mono-imh text-xs" />
                {actionQuery && (
                  <button onClick={() => setActionQuery("")} data-testid="audit-action-clear"
                          className="absolute right-2 top-1/2 -translate-y-1/2 text-[#A1A1AA] hover:text-[#0A0A0A]">
                    <X size={14} />
                  </button>
                )}
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <div className="imh-eyebrow mb-1">Entity</div>
                <Select value={entityType} onValueChange={setEntityType}>
                  <SelectTrigger className="rounded-none h-10" data-testid="audit-entity-filter"><SelectValue /></SelectTrigger>
                  <SelectContent>{ENTITY_TYPES.map(e => <SelectItem key={e} value={e}>{e === "all" ? "All entities" : e}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div>
                <div className="imh-eyebrow mb-1">Role</div>
                <Select value={actorRole} onValueChange={setActorRole}>
                  <SelectTrigger className="rounded-none h-10" data-testid="audit-role-filter"><SelectValue /></SelectTrigger>
                  <SelectContent>{ACTOR_ROLES.map(r => <SelectItem key={r} value={r}>{r === "all" ? "All roles" : r}</SelectItem>)}</SelectContent>
                </Select>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2 text-[11px] font-mono-imh text-[#52525B]" data-testid="audit-summary">
            {effectiveActionFilter && (
              <span className="inline-flex items-center gap-1 px-2 py-1 bg-[#EEF2FF] text-[#0033A0]">
                action = <code>{effectiveActionFilter}</code>
              </span>
            )}
            {hasAnyFilter && (
              <button onClick={clearAll} data-testid="audit-clear-all"
                      className="text-[10px] uppercase tracking-widest text-[#B45309] hover:underline">Clear filters</button>
            )}
            <span className="ml-auto" data-testid="audit-count">
              {loading ? "Loading…" : `${items.length} entries`}
            </span>
          </div>
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
                  <Td>
                    <div className="font-editorial">{ACTION_LABELS[a.action] || a.action}</div>
                    <div className="font-mono-imh text-[10px] text-[#A1A1AA] mt-0.5">{a.action}</div>
                  </Td>
                  <Td className="font-mono-imh text-xs text-[#52525B]">{a.entity_type}</Td>
                  <Td className="font-mono-imh text-[11px] text-[#0A0A0A] max-w-[360px] truncate">
                    {a.details && Object.keys(a.details).length > 0 ? JSON.stringify(a.details) : "—"}
                  </Td>
                </tr>
              ))}
              {items.length === 0 && !loading && <tr><Td colSpan={6} className="text-center py-16 text-[#52525B]">No audit entries match the current filter.</Td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

const Th = ({ children }) => <th className="px-6 py-4 text-[11px] uppercase tracking-widest text-[#52525B] font-medium">{children}</th>;
const Td = ({ children, className = "", colSpan }) => <td colSpan={colSpan} className={`px-6 py-4 text-[#0A0A0A] ${className}`}>{children}</td>;
