import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import ProposalHistoryDrawer from "@/components/ProposalHistoryDrawer";
import DuplicateProposalDialog from "@/components/DuplicateProposalDialog";
import { Plus, Copy, History, FileDown } from "lucide-react";

const STATUS_STYLE = {
  pending_review:     { bg: "#F5F0E1", color: "#B45309", label: "Submitted" },
  submitted:          { bg: "#F5F0E1", color: "#B45309", label: "Submitted" },
  revised:            { bg: "#EEF2FF", color: "#0033A0", label: "Revised" },
  approved:           { bg: "#E6F2EA", color: "#166534", label: "Approved" },
  rejected:           { bg: "#FBEBEB", color: "#991B1B", label: "Rejected" },
  revision_requested: { bg: "#EEF2FF", color: "#0033A0", label: "Revision requested" },
  archived:           { bg: "#EFEEEA", color: "#52525B", label: "Archived" },
};

const LIFECYCLE_STYLE = {
  active:    { color: "#166534", label: "Live" },
  scheduled: { color: "#0033A0", label: "Scheduled" },
  expired:   { color: "#991B1B", label: "Expired" },
};

export default function BannerProposals() {
  const [items, setItems] = useState([]);
  const [historyOf, setHistoryOf] = useState(null);
  const [duplicateOf, setDuplicateOf] = useState(null);

  const load = () => api.get("/campaigns").then(r => setItems(r.data));
  useEffect(() => { load(); }, []);

  const downloadPdf = async (e, path, filename) => {
    e.preventDefault();
    const r = await api.get(path, { responseType: "blob" });
    const url = URL.createObjectURL(new Blob([r.data], { type: "application/pdf" }));
    const a = document.createElement("a");
    a.href = url; a.download = filename;
    document.body.appendChild(a); a.click(); a.remove();
    URL.revokeObjectURL(url);
  };

  return (
    <div>
      <PageHeader eyebrow="Banner Inventory"
        title="Your commercial proposals"
        description="Every proposal you have submitted to Independent Media Network for the banner inventory. Track review status, requested revisions and approved flights."
        actions={
          <Link to="/rep/banners/new">
            <Button data-testid="new-proposal-btn" className="rounded-none h-10 bg-[#0033A0] hover:bg-[#002277]">
              <Plus size={16} className="mr-2" /> New proposal
            </Button>
          </Link>
        } />
      <div className="px-10 py-10">
        <div className="imh-card overflow-hidden">
          <table className="w-full text-sm" data-testid="proposals-table">
            <thead>
              <tr className="text-left border-b border-[#E4E4E1] bg-[#F9F9F6]">
                <Th>Proposal</Th><Th>Client ref</Th><Th>Inventory</Th>
                <Th>Status</Th><Th>Lifecycle</Th><Th>Flights</Th>
                <Th className="text-right">Actions</Th>
              </tr>
            </thead>
            <tbody>
              {items.map(c => {
                const s = STATUS_STYLE[c.status] || STATUS_STYLE.pending_review;
                const life = c.lifecycle ? LIFECYCLE_STYLE[c.lifecycle] : null;
                const canDuplicate = c.status === "revision_requested";
                const feedback = c.representative_feedback || c.admin_notes;
                return (
                  <tr key={c.id} className="border-b border-[#E4E4E1] last:border-b-0 align-top" data-testid={`proposal-${c.id}`}>
                    <Td>
                      <div className="font-editorial text-base">{c.campaign_name || c.proposal_name || "—"}</div>
                      {c.parent_proposal_id && (
                        <div className="text-[10px] font-mono-imh text-[#0033A0] mt-1">Revision of #{String(c.parent_proposal_id).slice(0, 8)}</div>
                      )}
                      {feedback && <div className="text-xs text-[#52525B] italic mt-1 max-w-md">Feedback: {feedback}</div>}
                    </Td>
                    <Td className="font-mono-imh text-xs">{c.client_reference || c.client_name || "—"}</Td>
                    <Td>
                      <div className="text-[11px] uppercase tracking-widest text-[#52525B]">{c.network_name}</div>
                      <div className="text-sm">{c.position_name}</div>
                    </Td>
                    <Td>
                      <span className="inline-block px-2 py-0.5 text-[10px] uppercase tracking-widest font-mono-imh"
                            style={{ background: s.bg, color: s.color }} data-testid={`proposal-status-${c.id}`}>
                        {s.label}
                      </span>
                    </Td>
                    <Td>
                      {life ? (
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] uppercase tracking-widest font-mono-imh" style={{ color: life.color }}>{life.label}</span>
                          {c.days_left != null && (
                            <span className="font-mono-imh text-[10px] text-[#52525B]">
                              {c.days_left < 0 ? `${Math.abs(c.days_left)}d ago` : `${c.days_left}d left`}
                            </span>
                          )}
                        </div>
                      ) : <span className="text-[10px] text-[#A1A1AA] font-mono-imh">—</span>}
                    </Td>
                    <Td className="font-mono-imh text-xs text-[#52525B]">
                      {c.start_date ? c.start_date.slice(0, 10) : "—"}{c.end_date ? <><br/>→ {c.end_date.slice(0, 10)}</> : null}
                    </Td>
                    <Td className="text-right">
                      <div className="inline-flex items-center gap-1">
                        <button onClick={() => setHistoryOf(c)}
                          data-testid={`proposal-history-${c.id}`}
                          className="h-8 px-2 border border-[#E4E4E1] hover:border-[#0A0A0A] text-[11px] uppercase tracking-widest inline-flex items-center gap-1"
                          style={{ transition: "border-color 120ms" }}>
                          <History size={12} /> History
                        </button>
                        {c.status === "approved" && (
                          <a href={`${process.env.REACT_APP_BACKEND_URL}/api/campaigns/${c.id}/proposal.pdf`}
                             target="_blank" rel="noreferrer"
                             onClick={(e) => downloadPdf(e, `/campaigns/${c.id}/proposal.pdf`, `IMN-proposal-${c.id.slice(0,8)}.pdf`)}
                             data-testid={`proposal-pdf-${c.id}`}
                             className="h-8 px-2 border border-[#166534] text-[#166534] hover:bg-[#166534] hover:text-white text-[11px] uppercase tracking-widest inline-flex items-center gap-1"
                             style={{ transition: "background 120ms, color 120ms" }}>
                            <FileDown size={12} /> Proposal PDF
                          </a>
                        )}
                        {canDuplicate && (
                          <button onClick={() => setDuplicateOf(c)}
                            data-testid={`proposal-duplicate-${c.id}`}
                            className="h-8 px-2 border border-[#0033A0] text-[#0033A0] hover:bg-[#0033A0] hover:text-white text-[11px] uppercase tracking-widest inline-flex items-center gap-1"
                            style={{ transition: "background 120ms, color 120ms" }}>
                            <Copy size={12} /> Duplicate & revise
                          </button>
                        )}
                      </div>
                    </Td>
                  </tr>
                );
              })}
              {items.length === 0 && (
                <tr><Td colSpan={7} className="text-center py-16 text-[#52525B]">
                  You haven't submitted any commercial proposals yet. <Link to="/rep/banners/new" className="text-[#0033A0] underline">Submit your first</Link>.
                </Td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <ProposalHistoryDrawer open={!!historyOf} onOpenChange={(v) => !v && setHistoryOf(null)}
                             proposal={historyOf} isAdminView={false} />
      <DuplicateProposalDialog kind="banner" original={duplicateOf}
                                open={!!duplicateOf} onOpenChange={(v) => !v && setDuplicateOf(null)}
                                onDone={load} />
    </div>
  );
}

const Th = ({ children, className = "" }) => <th className={`px-6 py-4 text-[11px] uppercase tracking-widest text-[#52525B] font-medium ${className}`}>{children}</th>;
const Td = ({ children, className = "", colSpan, style }) => <td colSpan={colSpan} style={style} className={`px-6 py-4 text-[#0A0A0A] ${className}`}>{children}</td>;
