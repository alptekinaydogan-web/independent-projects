import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import api from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { Check, CheckCheck, Sparkles, AlertOctagon, Clock, Info, Archive } from "lucide-react";

function relativeTime(iso) {
  if (!iso) return "";
  const s = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s/60)}m ago`;
  if (s < 86400) return `${Math.floor(s/3600)}h ago`;
  return `${Math.floor(s/86400)}d ago`;
}

const EVENT_LABEL = {
  "proposal.approved": "Partner project approved",
  "proposal.rejected": "Partner project declined",
  "proposal.in_review": "Partner project revision requested",
  "proposal.submitted": "New partner project",
  "production.applied":            "New production application",
  "production.approved":           "Production application approved",
  "production.rejected":           "Production application declined",
  "production.revision_requested": "Production application needs revision",
  "tv_project.launched":       "Project published",
  "tv_project.status.active":  "Project reopened",
  "tv_project.status.closed":  "Project frozen",
  "representative.suspended":     "Account suspended",
  "representative.reactivated":   "Account reactivated",
  "representative.password_reset": "Password reset by admin",
};

const SEV_META = {
  action_required: { color: "#991B1B", label: "Action Required", Icon: AlertOctagon, bg: "#FBEBEB" },
  reminder:        { color: "#B45309", label: "Reminder",        Icon: Clock,        bg: "#F5F0E1" },
  info:            { color: "#166534", label: "Information",     Icon: Info,         bg: "#E6F2EA" },
};

const TABS = [
  { key: "all",             label: "All" },
  { key: "action_required", label: "Action required" },
  { key: "reminder",        label: "Reminders" },
  { key: "info",            label: "Information" },
  { key: "archived",        label: "Archive" },
];

export default function Notifications() {
  const [items, setItems] = useState([]);
  const [tab, setTab] = useState("all");
  const [unreadOnly, setUnreadOnly] = useState(false);

  const load = async () => {
    const params = new URLSearchParams({ limit: "200" });
    if (tab === "archived") params.set("include_archived", "true");
    else if (["action_required", "reminder", "info"].includes(tab)) params.set("severity", tab);
    if (unreadOnly && tab !== "archived") params.set("unread_only", "true");
    const { data } = await api.get(`/notifications?${params.toString()}`);
    // For archived tab we want ONLY archived ones
    setItems(tab === "archived" ? data.filter(d => d.archived) : data);
  };

  useEffect(() => { load(); /* eslint-disable-next-line */ }, [tab, unreadOnly]);

  const markOne = async (id) => { await api.patch(`/notifications/${id}/read`); load(); };
  const archiveOne = async (id) => { await api.post(`/notifications/${id}/archive`, {}); toast.success("Archived"); load(); };
  const markAll = async () => { await api.post("/notifications/mark-all-read", {}); toast.success("All read"); load(); };
  const archiveRead = async () => {
    if (!confirm("Archive every notification you have already read?")) return;
    const { data } = await api.post("/notifications/archive-read", {});
    toast.success(`Archived ${data.archived} notification(s)`);
    load();
  };

  const grouped = useMemo(() => {
    if (tab === "archived") return { archived: items };
    const g = { action_required: [], reminder: [], info: [] };
    for (const n of items) {
      const sev = SEV_META[n.severity] ? n.severity : "info";
      g[sev].push(n);
    }
    return g;
  }, [items, tab]);

  const totalUnread = items.filter(i => !i.read && !i.archived).length;

  return (
    <div>
      <PageHeader
        eyebrow="Notification Center"
        title="Signal, not noise."
        description="Meaningful commercial and operational events, categorized by importance. Clear the noise, act on what matters."
        actions={
          <div className="flex gap-2">
            <Button onClick={archiveRead} data-testid="notif-archive-read" variant="outline"
                    className="rounded-none h-10 border-[#E4E4E1] hover:border-[#0A0A0A]">
              <Archive size={14} className="mr-2" /> Archive all read
            </Button>
            <Button onClick={markAll} disabled={totalUnread === 0} data-testid="notif-page-mark-all"
                    className="rounded-none h-10 bg-[#0033A0] hover:bg-[#002277] text-white">
              <CheckCheck size={14} className="mr-2" /> Mark all read ({totalUnread})
            </Button>
          </div>
        }
      />
      <div className="px-10 py-10 space-y-4">
        {/* Tabs */}
        <div className="flex items-center gap-2 flex-wrap" data-testid="notif-filters">
          {TABS.map(t => (
            <button key={t.key} onClick={() => setTab(t.key)} data-testid={`notif-tab-${t.key}`}
              className={`px-3 py-2 text-xs uppercase tracking-widest border ${tab === t.key ? "bg-[#0A0A0A] text-white border-[#0A0A0A]" : "bg-white border-[#E4E4E1] hover:border-[#0A0A0A]"}`}>
              {t.label}
            </button>
          ))}
          {tab !== "archived" && (
            <label className="ml-2 flex items-center gap-2 text-xs text-[#52525B] cursor-pointer">
              <input type="checkbox" checked={unreadOnly} onChange={e => setUnreadOnly(e.target.checked)}
                     data-testid="notif-unread-only" />
              Unread only
            </label>
          )}
        </div>

        {/* Empty state */}
        {items.length === 0 && (
          <div className="imh-card p-16 text-center" data-testid="notif-empty">
            <Sparkles size={20} className="mx-auto mb-3 text-[#A1A1AA]" />
            <div className="font-editorial text-2xl">You're all caught up</div>
            <div className="text-sm text-[#52525B] mt-2">
              {tab === "archived" ? "Nothing has been archived yet." : "Meaningful events land here — application decisions, project launches, and administrator actions affecting you."}
            </div>
          </div>
        )}

        {/* Grouped sections (only when tab === all) */}
        {tab === "all" && ["action_required", "reminder", "info"].map(sev => {
          const bucket = grouped[sev] || [];
          if (bucket.length === 0) return null;
          const meta = SEV_META[sev];
          const Icon = meta.Icon;
          return (
            <section key={sev} className="imh-card overflow-hidden" data-testid={`notif-section-${sev}`}>
              <div className="px-6 py-4 border-b border-[#E4E4E1] flex items-center gap-3" style={{ background: meta.bg }}>
                <span className="w-8 h-8 border flex items-center justify-center" style={{ borderColor: meta.color, color: meta.color }}>
                  <Icon size={14} />
                </span>
                <div className="flex-1">
                  <div className="imh-eyebrow" style={{ color: meta.color }}>{meta.label}</div>
                  <div className="font-editorial text-lg leading-tight">{bucket.length} notification{bucket.length !== 1 ? "s" : ""}</div>
                </div>
              </div>
              <NotifRows rows={bucket} onMark={markOne} onArchive={archiveOne} />
            </section>
          );
        })}

        {/* Single flat list for severity/archive tabs */}
        {tab !== "all" && items.length > 0 && (
          <div className="imh-card overflow-hidden" data-testid="notif-list">
            <NotifRows rows={items} onMark={markOne} onArchive={archiveOne} showArchived={tab === "archived"} />
          </div>
        )}
      </div>
    </div>
  );
}

function NotifRows({ rows, onMark, onArchive, showArchived = false }) {
  return (
    <ul className="divide-y divide-[#E4E4E1]">
      {rows.map(n => {
        const label = EVENT_LABEL[n.event_type] || n.event_type;
        const meta = SEV_META[n.severity] || SEV_META.info;
        return (
          <li key={n.id} className={`px-6 py-4 flex items-start gap-4 hover:bg-[#F9F9F6] ${n.read ? "opacity-70" : ""}`}
              data-testid={`notif-row-${n.id}`}>
            <span className="imh-dot mt-2 shrink-0" style={{ background: meta.color }} />
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-3">
                <span className="imh-eyebrow" style={{ color: meta.color }}>{label}</span>
                <span className="font-mono-imh text-[10px] text-[#A1A1AA]">{relativeTime(n.created_at)}</span>
                {!n.read && !n.archived && <span className="text-[10px] uppercase tracking-widest text-[#0033A0]">• new</span>}
                {n.archived && <span className="text-[10px] uppercase tracking-widest text-[#A1A1AA]">archived</span>}
              </div>
              <h4 className={`mt-1 ${n.read ? "text-[#52525B]" : "text-[#0A0A0A]"} font-editorial text-lg`}>{n.title}</h4>
              <p className="text-sm text-[#52525B] mt-1">{n.message}</p>
              {n.link && (
                <Link to={n.link} className="mt-2 inline-block text-xs uppercase tracking-widest text-[#0033A0] hover:text-[#002277]">Open →</Link>
              )}
            </div>
            <div className="flex flex-col gap-2 shrink-0">
              {!n.read && !showArchived && (
                <button onClick={() => onMark(n.id)} data-testid={`notif-row-mark-${n.id}`} className="text-[#A1A1AA] hover:text-[#0033A0]" title="Mark read">
                  <Check size={14} />
                </button>
              )}
              {!n.archived && (
                <button onClick={() => onArchive(n.id)} data-testid={`notif-row-archive-${n.id}`} className="text-[#A1A1AA] hover:text-[#991B1B]" title="Archive">
                  <Archive size={14} />
                </button>
              )}
            </div>
          </li>
        );
      })}
    </ul>
  );
}
