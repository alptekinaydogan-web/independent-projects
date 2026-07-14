import { useEffect, useState } from "react";
import api, { formatApiError } from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { toast } from "sonner";

const STATUS_STYLE = {
  pending_review:     { bg: "#F5F0E1", color: "#B45309", label: "Pending" },
  approved:           { bg: "#E6F2EA", color: "#166534", label: "Approved" },
  rejected:           { bg: "#FBEBEB", color: "#991B1B", label: "Rejected" },
  revision_requested: { bg: "#EEF2FF", color: "#0033A0", label: "Revision" },
};

const fmt = (n) => n == null ? "—" : `$${Number(n).toLocaleString()}`;

export default function ProposalsReview() {
  const [banners, setBanners] = useState([]);
  const [tv, setTv] = useState([]);
  const [notes, setNotes] = useState({});
  const [filter, setFilter] = useState("pending_review");

  const load = async () => {
    const [a, b] = await Promise.all([api.get("/campaigns"), api.get("/sponsorships")]);
    setBanners(a.data); setTv(b.data);
  };
  useEffect(() => { load(); }, []);

  const decideBanner = async (id, decision) => {
    try {
      await api.patch(`/campaigns/${id}/decision`, { decision, admin_notes: notes[id] || "" });
      toast.success(`Proposal ${decision.replace("_", " ")}`);
      await load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };
  const decideTV = async (id, decision) => {
    try {
      await api.patch(`/sponsorships/${id}/decision`, { decision, admin_notes: notes[id] || "" });
      toast.success(`Proposal ${decision.replace("_", " ")}`);
      await load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };

  const filterFn = (i) => filter === "all" || i.status === filter;

  return (
    <div>
      <PageHeader eyebrow="Commercial · Review" title="Proposals awaiting your decision"
        description="Confidential commercial proposals submitted by representatives across the network. Approve, request revision, or reject with a note." />
      <div className="px-10 py-10 space-y-6">
        <div className="flex gap-2" data-testid="review-filters">
          {["pending_review", "revision_requested", "approved", "rejected", "all"].map(f => (
            <button key={f} onClick={() => setFilter(f)} data-testid={`filter-${f}`}
              className={`px-3 py-2 text-xs uppercase tracking-widest border ${filter === f ? "bg-[#0A0A0A] text-white border-[#0A0A0A]" : "bg-white border-[#E4E4E1] hover:border-[#0A0A0A]"}`}>
              {f === "all" ? "All" : (STATUS_STYLE[f]?.label || f)}
            </button>
          ))}
        </div>

        <Tabs defaultValue="banner">
          <TabsList className="rounded-none border border-[#E4E4E1] bg-white p-0 h-auto">
            <TabsTrigger value="banner" className="rounded-none data-[state=active]:bg-[#0A0A0A] data-[state=active]:text-white px-4 py-2 text-xs uppercase tracking-widest" data-testid="tab-banner">Banner ({banners.filter(filterFn).length})</TabsTrigger>
            <TabsTrigger value="tv" className="rounded-none data-[state=active]:bg-[#0A0A0A] data-[state=active]:text-white px-4 py-2 text-xs uppercase tracking-widest" data-testid="tab-tv">TV Sponsorship ({tv.filter(filterFn).length})</TabsTrigger>
          </TabsList>

          <TabsContent value="banner" className="mt-4">
            <ProposalList items={banners.filter(filterFn)} kind="banner" notes={notes} setNotes={setNotes} onDecide={decideBanner} />
          </TabsContent>
          <TabsContent value="tv" className="mt-4">
            <ProposalList items={tv.filter(filterFn)} kind="tv" notes={notes} setNotes={setNotes} onDecide={decideTV} />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}

function ProposalList({ items, kind, notes, setNotes, onDecide }) {
  if (items.length === 0) return <div className="imh-card p-16 text-center text-[#52525B]">Nothing to review here.</div>;
  return (
    <div className="space-y-4">
      {items.map(p => {
        const s = STATUS_STYLE[p.status] || STATUS_STYLE.pending_review;
        return (
          <article key={p.id} className="imh-card p-6" data-testid={`review-${p.id}`}>
            <div className="flex items-start justify-between gap-6">
              <div className="flex-1">
                <div className="flex items-center gap-3">
                  <span className="imh-eyebrow">{kind === "banner" ? `${p.network_name} · ${p.position_name}` : p.tv_project_title}</span>
                  <span className="px-2 py-0.5 text-[10px] uppercase tracking-widest font-mono-imh" style={{ background: s.bg, color: s.color }}>{s.label}</span>
                </div>
                <h3 className="font-editorial text-2xl mt-2">{p.campaign_name || p.proposal_name}</h3>
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
                {p.admin_notes && <div className="text-sm text-[#52525B] mt-3">Previous note: {p.admin_notes}</div>}
              </div>

              {p.status === "pending_review" && (
                <div className="w-[300px] shrink-0">
                  <Textarea placeholder="Note to representative (optional)" className="rounded-none h-24 text-xs"
                            onChange={e => setNotes({ ...notes, [p.id]: e.target.value })}
                            data-testid={`review-notes-${p.id}`} />
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
