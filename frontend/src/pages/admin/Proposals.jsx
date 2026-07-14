import { useEffect, useState } from "react";
import api, { formatApiError } from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";

const STATUS_STYLE = {
  in_review: { bg: "#F5F0E1", color: "#B45309", label: "In review" },
  approved: { bg: "#E6F2EA", color: "#166534", label: "Approved" },
  rejected: { bg: "#FBEBEB", color: "#991B1B", label: "Rejected" },
};

export default function Proposals() {
  const [items, setItems] = useState([]);
  const [notes, setNotes] = useState({});

  const load = () => api.get("/proposals").then(r => setItems(r.data));
  useEffect(() => { load(); }, []);

  const decide = async (id, status) => {
    try {
      await api.patch(`/admin/proposals/${id}`, { status, admin_notes: notes[id] || "" });
      toast.success(`Proposal ${status}`);
      await load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };

  return (
    <div>
      <PageHeader eyebrow="Commercial" title="Project Proposals" description="TV production ideas submitted by representatives from around the world." />
      <div className="px-10 py-10 space-y-4">
        {items.length === 0 && <div className="text-center py-16 text-[#52525B] imh-card">No proposals yet.</div>}
        {items.map(p => {
          const s = STATUS_STYLE[p.status] || STATUS_STYLE.in_review;
          return (
            <article key={p.id} className="imh-card p-6" data-testid={`proposal-${p.id}`}>
              <div className="flex items-start justify-between gap-6">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3">
                    <span className="imh-eyebrow">{p.format} · {p.country}</span>
                    <span className="px-2 py-0.5 text-[10px] uppercase tracking-widest" style={{ background: s.bg, color: s.color }}>{s.label}</span>
                  </div>
                  <h3 className="font-editorial text-2xl mt-2">{p.title}</h3>
                  <p className="text-sm text-[#52525B] mt-2 max-w-3xl">{p.description}</p>
                  <div className="mt-4 flex flex-wrap gap-6 text-xs text-[#52525B]">
                    <span>Submitted by <b className="text-[#0A0A0A]">{p.rep_name}</b> · {p.agency_name}</span>
                    <span>Estimated episodes: <b className="text-[#0A0A0A] font-mono-imh">{p.estimated_episodes}</b></span>
                    {p.budget_hint_usd > 0 && <span>Budget hint: <b className="font-mono-imh text-[#0A0A0A]">${Number(p.budget_hint_usd).toLocaleString()}</b></span>}
                  </div>
                  {p.admin_notes && <div className="mt-3 text-xs text-[#52525B] italic">Admin notes: {p.admin_notes}</div>}
                </div>
                {p.status === "in_review" && (
                  <div className="w-[260px] shrink-0">
                    <Textarea placeholder="Notes (optional)" className="rounded-none h-20 text-xs"
                      onChange={e => setNotes({ ...notes, [p.id]: e.target.value })} data-testid={`proposal-notes-${p.id}`} />
                    <div className="mt-2 flex gap-2">
                      <Button size="sm" onClick={() => decide(p.id, "approved")} data-testid={`approve-${p.id}`} className="rounded-none bg-[#166534] hover:bg-[#0f4a25] flex-1">Approve</Button>
                      <Button size="sm" onClick={() => decide(p.id, "rejected")} data-testid={`reject-${p.id}`} variant="outline" className="rounded-none border-[#991B1B] text-[#991B1B] flex-1">Reject</Button>
                    </div>
                  </div>
                )}
              </div>
            </article>
          );
        })}
      </div>
    </div>
  );
}
