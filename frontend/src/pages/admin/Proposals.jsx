import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import api from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { Send, Sparkles } from "lucide-react";

/**
 * Partner Submissions inbox. Each row links straight to the FULL editor
 * in review mode (`/admin/tv-projects/{id}`), where the admin sees every
 * section of the project and can Approve / Request revision / Reject
 * with a real project page rather than a shallow form.
 */
const STATUS_STYLE = {
  submitted:          { bg: "#F5F0E1", color: "#B45309", label: "Awaiting review" },
  revision_requested: { bg: "#EEF2FF", color: "#0033A0", label: "Revision requested" },
  approved:           { bg: "#E6F2EA", color: "#166534", label: "Approved" },
  rejected:           { bg: "#FBEBEB", color: "#991B1B", label: "Rejected" },
};

export default function PartnerSubmissions() {
  const [items, setItems] = useState([]);
  const [filter, setFilter] = useState("pending");
  const nav = useNavigate();
  const [params] = useSearchParams();
  const openId = params.get("open");

  const load = () => api.get("/tv-projects?source=partner").then(r => setItems(r.data));
  useEffect(() => { load(); }, []);
  useEffect(() => { if (openId) nav(`/admin/tv-projects/${openId}`); }, [openId, nav]);

  const shown = items.filter(p => {
    if (filter === "all") return true;
    if (filter === "pending") return p.moderation_status === "submitted" || p.moderation_status === "revision_requested";
    return p.moderation_status === filter;
  });

  return (
    <div>
      <PageHeader eyebrow="Partner submissions" title="Project ideas from Country Partners"
                   description="Country partners submit new projects using the same modular editor Admins use. Click any submission to open the complete project page and moderate in place." />
      <div className="px-10 py-10 space-y-6">
        <div className="flex flex-wrap gap-2 items-center" data-testid="partner-filters">
          {["pending", "submitted", "revision_requested", "approved", "rejected", "all"].map(f => (
            <button key={f} onClick={() => setFilter(f)} data-testid={`filter-${f}`}
                     className={`px-3 py-2 text-xs uppercase tracking-widest border ${filter === f ? "bg-[#0A0A0A] text-white border-[#0A0A0A]" : "bg-white border-[#E4E4E1] hover:border-[#0A0A0A]"}`}
                     style={{ transition: "background 120ms, border-color 120ms" }}>
              {f === "all" ? "All" : f === "pending" ? "Pending" : (STATUS_STYLE[f]?.label || f)}
            </button>
          ))}
          <span className="ml-auto text-[11px] uppercase tracking-widest text-[#52525B]">{shown.length} submission{shown.length === 1 ? "" : "s"}</span>
        </div>

        {shown.length === 0 && <div className="imh-card p-16 text-center text-[#52525B]">Nothing to review here.</div>}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {shown.map(p => {
            const s = STATUS_STYLE[p.moderation_status] || STATUS_STYLE.submitted;
            return (
              <Link key={p.id} to={`/admin/tv-projects/${p.id}`}
                     className="imh-card p-5 hover:border-[#0A0A0A] group"
                     style={{ transition: "border-color 160ms" }}
                     data-testid={`partner-submission-${p.id}`}>
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="imh-eyebrow flex items-center gap-1"><Sparkles size={11} /> Partner submission</span>
                      <span className="px-2 py-0.5 text-[10px] uppercase tracking-widest font-mono-imh" style={{ background: s.bg, color: s.color }}>{s.label}</span>
                    </div>
                    <h3 className="font-editorial text-xl mt-2">{p.title}</h3>
                    <div className="mt-1 text-sm text-[#52525B]">
                      {p.submitted_by_agency || p.submitted_by_rep_name} · {p.submitted_by_country || "—"}
                    </div>
                    <p className="text-sm text-[#52525B] mt-3 line-clamp-3">{p.overview || p.synopsis}</p>
                  </div>
                </div>
                <div className="mt-4 flex items-center justify-between text-[11px] font-mono-imh text-[#A1A1AA]">
                  <span>Submitted {(p.submitted_at || p.created_at || "").slice(0, 10)}</span>
                  <span className="text-[#0033A0] group-hover:text-[#002277] uppercase tracking-widest inline-flex items-center gap-1">Open full project <Send size={10} /></span>
                </div>
              </Link>
            );
          })}
        </div>
      </div>
    </div>
  );
}
