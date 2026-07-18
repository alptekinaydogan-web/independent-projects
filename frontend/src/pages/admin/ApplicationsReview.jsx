import { useEffect, useState } from "react";
import api, { formatApiError } from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";
import { Link } from "react-router-dom";
import { FilmIcon, ExternalLink } from "lucide-react";

/**
 * ApplicationsReview — Admins review "Apply to Produce" applications
 * submitted by country partners. Approve, request revision, or decline.
 */
const STATUS_STYLE = {
  submitted:           { bg: "#F5F0E1", color: "#B45309", label: "Submitted" },
  revision_requested:  { bg: "#EEF2FF", color: "#0033A0", label: "Revision requested" },
  approved:            { bg: "#E6F2EA", color: "#166534", label: "Approved" },
  rejected:            { bg: "#FBEBEB", color: "#991B1B", label: "Declined" },
};

const PENDING = new Set(["submitted", "revision_requested"]);

export default function ApplicationsReview() {
  const [apps, setApps] = useState([]);
  const [filter, setFilter] = useState("pending");
  const [feedback, setFeedback] = useState({});
  const [internal, setInternal] = useState({});

  const load = async () => {
    const r = await api.get("/productions");
    setApps(r.data);
  };
  useEffect(() => { load(); }, []);

  const decide = async (id, decision) => {
    try {
      await api.patch(`/productions/${id}/decision`, {
        decision,
        representative_feedback: feedback[id] || "",
        internal_notes: internal[id] || "",
      });
      toast.success(`Application ${decision.replace("_", " ")}`);
      await load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };

  const shown = apps.filter(a =>
    filter === "all" ? true :
    filter === "pending" ? PENDING.has(a.status) :
    a.status === filter
  );

  return (
    <div>
      <PageHeader eyebrow="Project Library · Review" title="Production applications"
                   description="Country partners applying to produce official projects in their territory. Approve, request revision, or decline each application." />
      <div className="px-10 py-10 space-y-6">
        <div className="flex flex-wrap gap-2 items-center" data-testid="review-filters">
          {["pending", "submitted", "revision_requested", "approved", "rejected", "all"].map(f => (
            <button key={f} onClick={() => setFilter(f)} data-testid={`filter-${f}`}
              className={`px-3 py-2 text-xs uppercase tracking-widest border ${filter === f ? "bg-[#0A0A0A] text-white border-[#0A0A0A]" : "bg-white border-[#E4E4E1] hover:border-[#0A0A0A]"}`}
              style={{ transition: "background 120ms, border-color 120ms" }}>
              {f === "all" ? "All" : f === "pending" ? "Pending" : (STATUS_STYLE[f]?.label || f)}
            </button>
          ))}
          <span className="ml-auto text-[11px] uppercase tracking-widest text-[#52525B]">{shown.length} application{shown.length === 1 ? "" : "s"}</span>
        </div>

        {shown.length === 0 && <div className="imh-card p-16 text-center text-[#52525B]">Nothing to review here.</div>}

        <div className="space-y-4">
          {shown.map(a => {
            const s = STATUS_STYLE[a.status] || STATUS_STYLE.submitted;
            const actionable = PENDING.has(a.status);
            return (
              <article key={a.id} className="imh-card p-6" data-testid={`application-${a.id}`}>
                <div className="flex items-start justify-between gap-6 flex-wrap">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 flex-wrap">
                      <span className="imh-eyebrow flex items-center gap-1"><FilmIcon size={11} /> {a.tv_project_title}</span>
                      <span className="px-2 py-0.5 text-[10px] uppercase tracking-widest font-mono-imh"
                             style={{ background: s.bg, color: s.color }}>{s.label}</span>
                      <Link to={`/admin/tv-projects/${a.tv_project_id}`} data-testid={`open-project-${a.id}`}
                            className="text-[11px] uppercase tracking-widest text-[#0033A0] inline-flex items-center gap-1 hover:text-[#002277]">
                        Open project <ExternalLink size={11} />
                      </Link>
                    </div>
                    <h3 className="font-editorial text-2xl mt-2">{a.agency_name || a.rep_name}</h3>
                    <div className="mt-1 text-sm text-[#52525B]">{a.rep_name} · {a.country || "—"}</div>

                    <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                      <div>
                        <div className="text-[10px] uppercase tracking-widest text-[#A1A1AA]">Target launch</div>
                        <div className="mt-1">{a.target_launch_date || "—"}</div>
                      </div>
                      <div>
                        <div className="text-[10px] uppercase tracking-widest text-[#A1A1AA]">Submitted at</div>
                        <div className="mt-1 font-mono-imh text-[11px] text-[#52525B]">{(a.created_at || "").slice(0, 16).replace("T", " ")}</div>
                      </div>
                    </div>

                    {a.message && (
                      <div className="mt-4 border-l-2 border-[#0033A0] pl-3 text-sm text-[#0A0A0A] italic">
                        "{a.message}"
                      </div>
                    )}

                    {a.representative_feedback && (
                      <div className="mt-4 text-xs text-[#52525B]">Last shared feedback: {a.representative_feedback}</div>
                    )}
                    {a.internal_notes && (
                      <div className="mt-3 text-xs bg-[#FFFAF3] border-l-2 border-[#B45309] px-3 py-2">
                        <div className="imh-eyebrow" style={{ color: "#B45309" }}>Internal (admin only)</div>
                        <div className="mt-1 text-[#0A0A0A]">{a.internal_notes}</div>
                      </div>
                    )}
                  </div>

                  {actionable && (
                    <div className="w-full lg:w-[320px] shrink-0 space-y-2" data-testid={`decision-panel-${a.id}`}>
                      <div>
                        <div className="imh-eyebrow" style={{ color: "#0033A0" }}>Feedback to country partner</div>
                        <Textarea placeholder="Shared with the partner. Explain approval or requested revision."
                                   className="rounded-none h-20 text-xs mt-1"
                                   onChange={e => setFeedback({ ...feedback, [a.id]: e.target.value })}
                                   data-testid={`rep-feedback-${a.id}`} />
                      </div>
                      <div>
                        <div className="imh-eyebrow" style={{ color: "#B45309" }}>Internal notes (admin only)</div>
                        <Textarea placeholder="Confidential. Never visible to country partners."
                                   className="rounded-none h-20 text-xs mt-1 bg-[#FFFAF3]"
                                   onChange={e => setInternal({ ...internal, [a.id]: e.target.value })}
                                   data-testid={`internal-notes-${a.id}`} />
                      </div>
                      <div className="mt-2 grid grid-cols-3 gap-2">
                        <Button size="sm" onClick={() => decide(a.id, "approved")} data-testid={`decide-approve-${a.id}`}
                          className="rounded-none bg-[#166534] hover:bg-[#0f4a25] text-white">Approve</Button>
                        <Button size="sm" onClick={() => decide(a.id, "revision_requested")} data-testid={`decide-revise-${a.id}`}
                          className="rounded-none bg-[#0033A0] hover:bg-[#002277] text-white">Revise</Button>
                        <Button size="sm" variant="outline" onClick={() => decide(a.id, "rejected")} data-testid={`decide-reject-${a.id}`}
                          className="rounded-none border-[#991B1B] text-[#991B1B]">Decline</Button>
                      </div>
                    </div>
                  )}
                </div>
              </article>
            );
          })}
        </div>
      </div>
    </div>
  );
}
