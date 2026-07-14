import { useEffect, useMemo, useState, useRef } from "react";
import { Link, useLocation } from "react-router-dom";
import api from "@/lib/api";
import { Bell, Check, CheckCheck, Sparkles } from "lucide-react";

function relativeTime(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  const s = Math.floor((Date.now() - d.getTime()) / 1000);
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s/60)}m ago`;
  if (s < 86400) return `${Math.floor(s/3600)}h ago`;
  return `${Math.floor(s/86400)}d ago`;
}

const EVENT_DOT_COLOR = {
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

export default function NotificationBell({ notificationsBase }) {
  const [items, setItems] = useState([]);
  const [unread, setUnread] = useState(0);
  const [open, setOpen] = useState(false);
  const wrapRef = useRef(null);
  const location = useLocation();

  const load = async () => {
    const [a, b] = await Promise.all([
      api.get("/notifications?limit=8"),
      api.get("/notifications/unread-count"),
    ]);
    setItems(a.data); setUnread(b.data.count);
  };

  useEffect(() => {
    load();
    const t = setInterval(load, 45000);
    return () => clearInterval(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Re-fetch on route change (a lot of actions change notification state)
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [location.pathname]);

  // Close dropdown on outside click
  useEffect(() => {
    const on = (e) => { if (open && wrapRef.current && !wrapRef.current.contains(e.target)) setOpen(false); };
    window.addEventListener("mousedown", on);
    return () => window.removeEventListener("mousedown", on);
  }, [open]);

  const markOne = async (id, e) => {
    e?.stopPropagation?.();
    e?.preventDefault?.();
    await api.patch(`/notifications/${id}/read`);
    load();
  };

  const markAll = async () => {
    await api.post("/notifications/mark-all-read", {});
    load();
  };

  const preview = useMemo(() => items.slice(0, 6), [items]);

  return (
    <div ref={wrapRef} className="relative">
      <button
        data-testid="notification-bell"
        onClick={() => setOpen(v => !v)}
        className="relative w-10 h-10 flex items-center justify-center border border-[#334155] hover:bg-[#111a34] text-white"
        style={{ transition: "background 160ms" }}>
        <Bell size={16} strokeWidth={1.5} />
        {unread > 0 && (
          <span data-testid="notif-badge"
            className="absolute -top-1 -right-1 min-w-[18px] h-[18px] px-1 bg-[#0033A0] text-white text-[10px] font-mono-imh flex items-center justify-center">
            {unread > 99 ? "99+" : unread}
          </span>
        )}
      </button>

      {open && (
        <div data-testid="notif-panel"
          className="absolute right-0 top-12 w-[380px] max-w-[92vw] bg-white border border-[#0A0A0A] text-[#0A0A0A] z-50 shadow-[0_20px_50px_rgba(0,0,0,0.15)]">
          <div className="px-4 py-3 border-b border-[#E4E4E1] flex items-center justify-between">
            <div>
              <div className="imh-eyebrow">Notifications</div>
              <div className="font-editorial text-lg mt-0.5">Latest activity</div>
            </div>
            <button onClick={markAll} data-testid="notif-mark-all"
              className="text-[11px] uppercase tracking-widest text-[#0033A0] hover:text-[#002277] inline-flex items-center gap-1">
              <CheckCheck size={12} /> Mark all read
            </button>
          </div>

          <ul className="max-h-[420px] overflow-y-auto">
            {preview.length === 0 && (
              <li className="px-4 py-10 text-center text-sm text-[#52525B]" data-testid="notif-empty">
                <Sparkles size={16} className="mx-auto mb-2 text-[#A1A1AA]" />
                Nothing new yet.
              </li>
            )}
            {preview.map(n => (
              <li key={n.id} className={`px-4 py-3 border-b border-[#E4E4E1] last:border-b-0 flex gap-3 items-start hover:bg-[#F9F9F6]`}
                data-testid={`notif-item-${n.id}`}>
                <span className="imh-dot mt-1.5" style={{ background: EVENT_DOT_COLOR[n.event_type] || "#52525B" }} />
                <div className="flex-1 min-w-0">
                  {n.link ? (
                    <Link to={n.link} onClick={() => { markOne(n.id); setOpen(false); }} className="block">
                      <div className={`text-sm ${n.read ? "text-[#52525B]" : "text-[#0A0A0A] font-medium"} truncate`}>{n.title}</div>
                      <div className="text-xs text-[#52525B] line-clamp-2 mt-0.5">{n.message}</div>
                    </Link>
                  ) : (
                    <div>
                      <div className={`text-sm ${n.read ? "text-[#52525B]" : "text-[#0A0A0A] font-medium"} truncate`}>{n.title}</div>
                      <div className="text-xs text-[#52525B] line-clamp-2 mt-0.5">{n.message}</div>
                    </div>
                  )}
                  <div className="text-[10px] uppercase tracking-widest text-[#A1A1AA] mt-1 font-mono-imh">{relativeTime(n.created_at)}</div>
                </div>
                {!n.read && (
                  <button onClick={(e) => markOne(n.id, e)} data-testid={`notif-mark-${n.id}`} className="text-[#A1A1AA] hover:text-[#0033A0]" title="Mark read">
                    <Check size={14} />
                  </button>
                )}
              </li>
            ))}
          </ul>

          <div className="px-4 py-3 border-t border-[#E4E4E1] text-center">
            <Link to={notificationsBase} onClick={() => setOpen(false)}
                  data-testid="notif-view-all"
                  className="text-xs uppercase tracking-widest text-[#0033A0] hover:text-[#002277]">
              View all notifications →
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
