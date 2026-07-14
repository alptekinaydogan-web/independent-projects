import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "@/lib/api";
import { AlertOctagon, Clock, ChevronRight } from "lucide-react";

const SEV_STYLE = {
  action_required: { dot: "#991B1B", label: "Action required", Icon: AlertOctagon },
  reminder:        { dot: "#B45309", label: "Reminder",        Icon: Clock },
};

function relativeTime(iso) {
  if (!iso) return "";
  const s = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s/60)}m ago`;
  if (s < 86400) return `${Math.floor(s/3600)}h ago`;
  return `${Math.floor(s/86400)}d ago`;
}

export default function ActionableStrip({ base = "/rep" }) {
  const [items, setItems] = useState([]);

  useEffect(() => {
    api.get("/notifications/actionable?limit=5").then(r => setItems(r.data));
  }, []);

  if (items.length === 0) return null;

  return (
    <section className="imh-card" data-testid="actionable-strip">
      <div className="px-6 py-4 border-b border-[#E4E4E1] flex items-center justify-between">
        <div>
          <div className="imh-eyebrow" style={{ color: "#991B1B" }}>Needs your attention</div>
          <h3 className="font-editorial text-xl mt-1">{items.length} item{items.length !== 1 ? "s" : ""} awaiting action</h3>
        </div>
        <Link to={`${base}/notifications`} className="text-xs uppercase tracking-widest text-[#0033A0] hover:text-[#002277]"
              data-testid="actionable-see-all">
          Open notification center →
        </Link>
      </div>
      <ul className="divide-y divide-[#E4E4E1]">
        {items.map(n => {
          const s = SEV_STYLE[n.severity] || SEV_STYLE.reminder;
          const Icon = s.Icon;
          return (
            <li key={n.id} data-testid={`actionable-${n.id}`}>
              <Link to={n.link || `${base}/notifications`}
                    className="flex items-center gap-4 px-6 py-4 hover:bg-[#F9F9F6]"
                    style={{ transition: "background 120ms" }}>
                <span className="w-8 h-8 border flex items-center justify-center shrink-0" style={{ borderColor: s.dot, color: s.dot }}>
                  <Icon size={14} />
                </span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="imh-eyebrow" style={{ color: s.dot }}>{s.label}</span>
                    <span className="text-[10px] uppercase tracking-widest text-[#A1A1AA] font-mono-imh">{relativeTime(n.created_at)}</span>
                  </div>
                  <div className="text-[15px] mt-0.5 truncate">{n.title}</div>
                </div>
                <ChevronRight size={16} className="text-[#A1A1AA]" />
              </Link>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
