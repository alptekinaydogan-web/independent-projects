import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import api from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { Check, CheckCheck, Sparkles } from "lucide-react";

function relativeTime(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  const s = Math.floor((Date.now() - d.getTime()) / 1000);
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s/60)}m ago`;
  if (s < 86400) return `${Math.floor(s/3600)}h ago`;
  return `${Math.floor(s/86400)}d ago`;
}

const EVENT_LABEL = {
  "proposal.approved": "Proposal approved",
  "proposal.rejected": "Proposal declined",
  "proposal.in_review": "Proposal revision",
  "proposal.submitted": "New proposal",
  "campaign.created": "New banner campaign",
  "sponsorship.created": "New TV sponsorship",
  "tv_project.launched": "TV project launched",
  "tv_project.status.active": "TV project reopened",
  "tv_project.status.closed": "TV project frozen",
  "representative.suspended": "Account suspended",
  "representative.reactivated": "Account reactivated",
  "representative.password_reset": "Password reset by admin",
};

const EVENT_COLOR = {
  "proposal.approved": "#166534",
  "proposal.rejected": "#991B1B",
  "proposal.in_review": "#B45309",
  "proposal.submitted": "#0033A0",
  "campaign.created": "#0033A0",
  "sponsorship.created": "#0033A0",
  "tv_project.launched": "#0033A0",
  "tv_project.status.active": "#166534",
  "tv_project.status.closed": "#991B1B",
  "representative.suspended": "#991B1B",
  "representative.reactivated": "#166534",
  "representative.password_reset": "#B45309",
};

const FILTERS = ["all", "unread"];

export default function Notifications() {
  const [items, setItems] = useState([]);
  const [filter, setFilter] = useState("all");

  const load = () => api.get(`/notifications?limit=200${filter === "unread" ? "&unread_only=true" : ""}`).then(r => setItems(r.data));
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [filter]);

  const markOne = async (id) => { await api.patch(`/notifications/${id}/read`); await load(); };
  const markAll = async () => {
    await api.post("/notifications/mark-all-read", {});
    toast.success("All notifications marked as read");
    await load();
  };

  const unreadCount = useMemo(() => items.filter(i => !i.read).length, [items]);

  return (
    <div>
      <PageHeader
        eyebrow="Signal · Not noise"
        title="Notifications"
        description="A focused stream of meaningful commercial and operational events on Independent Media Hub."
        actions={
          <Button data-testid="notif-page-mark-all" onClick={markAll} disabled={unreadCount === 0}
                  className="rounded-none h-10 bg-[#0033A0] hover:bg-[#002277] text-white">
            <CheckCheck size={14} className="mr-2" /> Mark all read ({unreadCount})
          </Button>
        }
      />
      <div className="px-10 py-10 space-y-4">
        <div className="flex gap-2" data-testid="notif-filters">
          {FILTERS.map(f => (
            <button key={f} onClick={() => setFilter(f)} data-testid={`notif-filter-${f}`}
              className={`px-3 py-2 text-xs uppercase tracking-widest border ${filter === f ? "bg-[#0A0A0A] text-white border-[#0A0A0A]" : "bg-white border-[#E4E4E1] hover:border-[#0A0A0A]"}`}>
              {f === "all" ? "All" : "Unread only"}
            </button>
          ))}
        </div>

        {items.length === 0 ? (
          <div className="imh-card p-16 text-center">
            <Sparkles size={20} className="mx-auto mb-3 text-[#A1A1AA]" />
            <div className="font-editorial text-2xl">You're all caught up</div>
            <div className="text-sm text-[#52525B] mt-2">Meaningful events land here — proposal decisions, sponsorship activity, and administrator actions affecting you.</div>
          </div>
        ) : (
          <ul className="imh-card overflow-hidden divide-y divide-[#E4E4E1]" data-testid="notif-list">
            {items.map(n => (
              <li key={n.id} className={`px-6 py-4 flex items-start gap-4 hover:bg-[#F9F9F6] ${n.read ? "opacity-70" : ""}`}
                  data-testid={`notif-row-${n.id}`}>
                <span className="imh-dot mt-2 shrink-0" style={{ background: EVENT_COLOR[n.event_type] || "#52525B" }} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3">
                    <span className="imh-eyebrow" style={{ color: EVENT_COLOR[n.event_type] || "#52525B" }}>
                      {EVENT_LABEL[n.event_type] || n.event_type}
                    </span>
                    <span className="font-mono-imh text-[10px] text-[#A1A1AA]">{relativeTime(n.created_at)}</span>
                    {!n.read && <span className="text-[10px] uppercase tracking-widest text-[#0033A0]">• new</span>}
                  </div>
                  <h4 className={`mt-1 ${n.read ? "text-[#52525B]" : "text-[#0A0A0A]"} font-editorial text-lg`}>{n.title}</h4>
                  <p className="text-sm text-[#52525B] mt-1">{n.message}</p>
                  {n.link && (
                    <Link to={n.link} className="mt-2 inline-block text-xs uppercase tracking-widest text-[#0033A0] hover:text-[#002277]">Open →</Link>
                  )}
                </div>
                {!n.read && (
                  <button onClick={() => markOne(n.id)} data-testid={`notif-row-mark-${n.id}`} className="text-[#A1A1AA] hover:text-[#0033A0]">
                    <Check size={14} />
                  </button>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
