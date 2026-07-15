import { useEffect, useState } from "react";
import api, { formatApiError } from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { toast } from "sonner";
import ProposalHistoryDrawer from "@/components/ProposalHistoryDrawer";
import { Archive, ArchiveRestore, History, FileDown } from "lucide-react";

const STATUS_STYLE = {
  pending_review:     { bg: "#F5F0E1", color: "#B45309", label: "Submitted" },
  submitted:          { bg: "#F5F0E1", color: "#B45309", label: "Submitted" },
  revised:            { bg: "#EEF2FF", color: "#0033A0", label: "Revised" },
  approved:           { bg: "#E6F2EA", color: "#166534", label: "Approved" },
  rejected:           { bg: "#FBEBEB", color: "#991B1B", label: "Rejected" },
  revision_requested: { bg: "#EEF2FF", color: "#0033A0", label: "Revision requested" },
  archived:           { bg: "#EFEEEA", color: "#52525B", label: "Archived" },
};

const fmt = (n) => n == null ? "—" : `$${Number(n).toLocaleString()}`;

// Statuses considered "actionable" and shown in the pending queue
const PENDING = new Set(["pending_review", "submitted", "revised", "revision_requested"]);

export default function ProposalsReview() {
  const [banners, setBanners] = useState([]);
  const [tv, setTv] = useState([]);
  const [feedback, setFeedback] = useState({});   // representative-visible
  const [internal, setInternal] = useState({});   // admin-only
  const [filter, setFilter] = useState("pending");
  const [includeArchived, setIncludeArchived] = useState(false);
  const [historyOf, setHistoryOf] = useState(null);

  const load = async () => {
    const params = includeArchived ? "?include_archived=true" : "";
    const [a, b] = await Promise.all([
      api.get("/campaigns" + params),
      api.get("/sponsorships" + params),
    ]);
    setBanners(a.data); setTv(b.data);
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [includeArchived]);

  const decideBanner = async (id, decision) => {
    try {
      await api.patch(`/campaigns/${id}/decision`, {
        decision,
        representative_feedback: feedback[id] || "",
        internal_notes: internal[id] || "",
      });
      toast.success(`Proposal ${decision.replace("_", " ")}`);
      await load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };
  const decideTV = async (id, decision) => {
    try {
      await api.patch(`/sponsorships/${id}/decision`, {
        decision,
        representative_feedback: feedback[id] || "",
        internal_notes: internal[id] || "",
      });
      toast.success(`Proposal ${decision.replace("_", " ")}`);
      await load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };

  const archive = async (kind, id) => {
    const reason = window.prompt("Archive reason (internal note, optional):", "") ?? "";
    try {
      const url = kind === "banner" ? `/campaigns/${id}/archive` : `/sponsorships/${id}/archive`;
      await api.post(url, { reason });
      toast.success("Proposal archived");
      await load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };
  const unarchive = async (kind, id) => {
    try {
      const url = kind === "banner" ? `/campaigns/${id}/unarchive` : `/sponsorships/${id}/unarchive`;
      await api.post(url, {});
      toast.success("Proposal restored");
      await load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };

  const downloadPdf = async (kind, id) => {
    const path = kind === "banner" ? `/campaigns/${id}/proposal.pdf` : `/sponsorships/${id}/proposal.pdf`;
    try {
      const r = await api.get(path, { responseType: "blob" });
      const url = URL.createObjectURL(new Blob([r.data], { type: "application/pdf" }));
      const a = document.createElement("a");
      a.href = url; a.download = `IMN-${kind}-${id.slice(0, 8)}.pdf`;
      document.body.appendChild(a); a.click(); a.remove();
      URL.revokeObjectURL(url);
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };

  const filterFn = (i) => {
    if (filter === "all") return true;
    if (filter === "pending") return PENDING.has(i.status) && !i.is_archived;
    if (filter === "archived") return !!i.is_archived;
    return i.status === filter;
  };

  return (
    <div>
      <PageHeader eyebrow="Commercial · Review" title="Proposals awaiting your decision"
        description="Confidential commercial proposals submitted by representatives. Approve, request revision, reject or archive. Internal notes stay confidential — only representative feedback is shared with the rep."
      />
      <div className="px-10 py-10 space-y-6">
        <div className="flex flex-wrap gap-2 items-center" data-testid="review-filters">
          {["pending", "revision_requested", "approved", "rejected", "archived", "all"].map(f => (
            <button key={f} onClick={() => setFilter(f)} data-testid={`filter-${f}`}
              className={`px-3 py-2 text-xs uppercase tracking-widest border ${filter === f ? "bg-[#0A0A0A] text-white border-[#0A0A0A]" : "bg-white border-[#E4E4E1] hover:border-[#0A0A0A]"}`}
              style={{ transition: "background 120ms, border-color 120ms" }}>
              {f === "all" ? "All" : f === "pending" ? "Pending" : (STATUS_STYLE[f]?.label || f)}
            </button>
          ))}
          <label className="ml-auto text-[11px] uppercase tracking-widest text-[#52525B] inline-flex items-center gap-2 cursor-pointer" data-testid="toggle-archived">
            <input type="checkbox" checked={includeArchived}
                    onChange={(e) => setIncludeArchived(e.target.checked)} />
            Include archived
          </label>
        </div>

        <Tabs defaultValue="banner">
          <TabsList className="rounded-none border border-[#E4E4E1] bg-white p-0 h-auto">
            <TabsTrigger value="banner" className="rounded-none data-[state=active]:bg-[#0A0A0A] data-[state=active]:text-white px-4 py-2 text-xs uppercase tracking-widest" data-testid="tab-banner">Banner ({banners.filter(filterFn).length})</TabsTrigger>
            <TabsTrigger value="tv" className="rounded-none data-[state=active]:bg-[#0A0A0A] data-[state=active]:text-white px-4 py-2 text-xs uppercase tracking-widest" data-testid="tab-tv">TV Sponsorship ({tv.filter(filterFn).length})</TabsTrigger>
          </TabsList>

          <TabsContent value="banner" className="mt-4">
            <ProposalList items={banners.filter(filterFn)} kind="banner"
                          feedback={feedback} setFeedback={setFeedback}
                          internal={internal} setInternal={setInternal}
                          onDecide={decideBanner} onArchive={(id) => archive("banner", id)}
                          onUnarchive={(id) => unarchive("banner", id)}
                          onHistory={setHistoryOf}
                          onDownloadPdf={(id) => downloadPdf("banner", id)} />
          </TabsContent>
          <TabsContent value="tv" className="mt-4">
            <ProposalList items={tv.filter(filterFn)} kind="tv"
                          feedback={feedback} setFeedback={setFeedback}
                          internal={internal} setInternal={setInternal}
                          onDecide={decideTV} onArchive={(id) => archive("tv", id)}
                          onUnarchive={(id) => unarchive("tv", id)}
                          onHistory={setHistoryOf}
                          onDownloadPdf={(id) => downloadPdf("tv", id)} />
          </TabsContent>
        </Tabs>
      </div>

      <ProposalHistoryDrawer open={!!historyOf} onOpenChange={(v) => !v && setHistoryOf(null)}
                             proposal={historyOf} isAdminView={true} />
    </div>
  );
}

function ProposalList({ items, kind, feedback, setFeedback, internal, setInternal,
                        onDecide, onArchive, onUnarchive, onHistory, onDownloadPdf }) {
  if (items.length === 0) return <div className="imh-card p-16 text-center text-[#52525B]">Nothing to review here.</div>;
  return (
    <div className="space-y-4">
      {items.map(p => {
        const s = STATUS_STYLE[p.status] || STATUS_STYLE.pending_review;
        const actionable = ["pending_review", "submitted", "revised"].includes(p.status) && !p.is_archived;
        return (
          <article key={p.id} className={`imh-card p-6 ${p.is_archived ? "opacity-70" : ""}`} data-testid={`review-${p.id}`}>
            <div className="flex items-start justify-between gap-6">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-3 flex-wrap">
                  <span className="imh-eyebrow">{kind === "banner" ? `${p.network_name} · ${p.position_name}` : p.tv_project_title}</span>
                  <span className="px-2 py-0.5 text-[10px] uppercase tracking-widest font-mono-imh" style={{ background: s.bg, color: s.color }}>{s.label}</span>
                  {p.is_archived && <span className="px-2 py-0.5 text-[10px] uppercase tracking-widest font-mono-imh bg-[#EFEEEA] text-[#52525B]">Archived</span>}
                  {p.parent_proposal_id && (
                    <span className="text-[10px] font-mono-imh text-[#0033A0]">Revision of #{String(p.parent_proposal_id).slice(0, 8)}</span>
                  )}
                </div>
                <h3 className="font-editorial text-2xl mt-2 break-words">{p.campaign_name || p.proposal_name}</h3>
                <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-6 text-sm">
                  <Fact label="Representative" value={p.agency_name || p.rep_name} />
                  <Fact label="Client reference" value={p.client_reference || p.client_name || "—"} />
                  {kind === "banner" ? (
                    <>
                      <Fact label="Flights" value={p.start_date && p.end_date ? `${p.start_date.slice(0,10)} → ${p.end_date.slice(0,10)}` : "—"} />
                      <Fact label="Impressions" value={p.impressions ? Number(p.impressions).toLocaleString() : "Negotiable"} />
                    </>
                  ) : (
                    <>
                      <Fact label="Episodes" value={`${p.episode_count} (${(p.episode_numbers || []).map(n => String(n).padStart(3, "0")).join(", ")})`} />
                      <Fact label="Notes" value={p.notes || "—"} />
                    </>
                  )}
                  <Fact label="Offer to IMN" value={<span className="text-[#0A0A0A] text-lg font-editorial">{fmt(p.offer_amount_usd)}</span>} />
                </div>
                {p.notes && kind === "banner" && <div className="text-sm text-[#52525B] mt-3 italic">"{p.notes}"</div>}
                {p.representative_feedback && <div className="text-xs text-[#52525B] mt-3">Last rep-visible feedback: {p.representative_feedback}</div>}
                {p.internal_notes && (
                  <div className="mt-3 text-xs bg-[#FFFAF3] border-l-2 border-[#B45309] px-3 py-2">
                    <div className="imh-eyebrow" style={{ color: "#B45309" }}>Internal (admin only)</div>
                    <div className="mt-1 text-[#0A0A0A]">{p.internal_notes}</div>
                  </div>
                )}

                <div className="mt-4 flex gap-2 flex-wrap">
                  <button onClick={() => onHistory(p)} data-testid={`admin-history-${p.id}`}
                          className="h-8 px-3 border border-[#E4E4E1] hover:border-[#0A0A0A] text-[11px] uppercase tracking-widest inline-flex items-center gap-1"
                          style={{ transition: "border-color 120ms" }}>
                    <History size={12} /> Lifecycle history
                  </button>
                  {p.status === "approved" && (
                    <button onClick={() => onDownloadPdf(p.id)} data-testid={`admin-pdf-${p.id}`}
                            className="h-8 px-3 border border-[#166534] text-[#166534] hover:bg-[#166534] hover:text-white text-[11px] uppercase tracking-widest inline-flex items-center gap-1"
                            style={{ transition: "background 120ms, color 120ms" }}>
                      <FileDown size={12} /> Proposal PDF
                    </button>
                  )}
                  {p.is_archived ? (
                    <button onClick={() => onUnarchive(p.id)} data-testid={`admin-unarchive-${p.id}`}
                            className="h-8 px-3 border border-[#E4E4E1] hover:border-[#0A0A0A] text-[11px] uppercase tracking-widest inline-flex items-center gap-1"
                            style={{ transition: "border-color 120ms" }}>
                      <ArchiveRestore size={12} /> Restore
                    </button>
                  ) : (
                    <button onClick={() => onArchive(p.id)} data-testid={`admin-archive-${p.id}`}
                            className="h-8 px-3 border border-[#E4E4E1] text-[#52525B] hover:border-[#0A0A0A] hover:text-[#0A0A0A] text-[11px] uppercase tracking-widest inline-flex items-center gap-1"
                            style={{ transition: "border-color 120ms" }}>
                      <Archive size={12} /> Archive
                    </button>
                  )}
                </div>
              </div>

              {actionable && (
                <div className="w-[320px] shrink-0 space-y-2" data-testid={`decision-panel-${p.id}`}>
                  <div>
                    <div className="imh-eyebrow" style={{ color: "#0033A0" }}>Feedback to representative</div>
                    <Textarea placeholder="Shared with the rep. Explain approval or requested revision."
                              className="rounded-none h-20 text-xs mt-1"
                              onChange={e => setFeedback({ ...feedback, [p.id]: e.target.value })}
                              data-testid={`rep-feedback-${p.id}`} />
                  </div>
                  <div>
                    <div className="imh-eyebrow" style={{ color: "#B45309" }}>Internal notes (admin only)</div>
                    <Textarea placeholder="Confidential. Never visible to representatives."
                              className="rounded-none h-20 text-xs mt-1 bg-[#FFFAF3]"
                              onChange={e => setInternal({ ...internal, [p.id]: e.target.value })}
                              data-testid={`internal-notes-${p.id}`} />
                  </div>
                  <div className="mt-2 grid grid-cols-3 gap-2">
                    <Button size="sm" onClick={() => onDecide(p.id, "approved")} data-testid={`decide-approve-${p.id}`}
                      className="rounded-none bg-[#166534] hover:bg-[#0f4a25] text-white">Approve</Button>
                    <Button size="sm" onClick={() => onDecide(p.id, "revision_requested")} data-testid={`decide-revise-${p.id}`}
                      className="rounded-none bg-[#0033A0] hover:bg-[#002277] text-white">Revise</Button>
                    <Button size="sm" variant="outline" onClick={() => onDecide(p.id, "rejected")} data-testid={`decide-reject-${p.id}`}
                      className="rounded-none border-[#991B1B] text-[#991B1B]">Reject</Button>
                  </div>
                </div>
              )}
            </div>
          </article>
        );
      })}
    </div>
  );
}

const Fact = ({ label, value }) => (
  <div>
    <div className="text-[10px] uppercase tracking-widest text-[#A1A1AA]">{label}</div>
    <div className="mt-1 text-[#0A0A0A]">{value}</div>
  </div>
);
