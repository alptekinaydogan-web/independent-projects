import { useEffect, useState } from "react";
import api from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import ProposalHistoryDrawer from "@/components/ProposalHistoryDrawer";
import DuplicateProposalDialog from "@/components/DuplicateProposalDialog";
import { Copy, History } from "lucide-react";

const STATUS_STYLE = {
  pending_review:     { bg: "#F5F0E1", color: "#B45309", label: "Submitted" },
  submitted:          { bg: "#F5F0E1", color: "#B45309", label: "Submitted" },
  revised:            { bg: "#EEF2FF", color: "#0033A0", label: "Revised" },
  approved:           { bg: "#E6F2EA", color: "#166534", label: "Approved" },
  rejected:           { bg: "#FBEBEB", color: "#991B1B", label: "Rejected" },
  revision_requested: { bg: "#EEF2FF", color: "#0033A0", label: "Revision requested" },
  archived:           { bg: "#EFEEEA", color: "#52525B", label: "Archived" },
};

export default function Sponsorships() {
  const [items, setItems] = useState([]);
  const [historyOf, setHistoryOf] = useState(null);
  const [duplicateOf, setDuplicateOf] = useState(null);

  const load = () => api.get("/sponsorships").then(r => setItems(r.data));
  useEffect(() => { load(); }, []);

  return (
    <div>
      <PageHeader eyebrow="Independent TV" title="Your sponsorship proposals"
                   description="Every TV sponsorship proposal you have submitted. Track the review lifecycle and resubmit revised proposals in one click." />
      <div className="px-10 py-10">
        <div className="imh-card overflow-hidden">
          <table className="w-full text-sm" data-testid="sponsorships-table">
            <thead>
              <tr className="text-left border-b border-[#E4E4E1] bg-[#F9F9F6]">
                <Th>Project</Th><Th>Client ref</Th><Th className="text-right">Episodes</Th><Th>Status</Th>
                <Th className="text-right">Actions</Th>
              </tr>
            </thead>
            <tbody>
              {items.map(s => {
                const st = STATUS_STYLE[s.status] || STATUS_STYLE.pending_review;
                const canDuplicate = s.status === "revision_requested";
                const feedback = s.representative_feedback || s.admin_notes;
                return (
                  <tr key={s.id} className="border-b border-[#E4E4E1] last:border-b-0 align-top" data-testid={`sp-${s.id}`}>
                    <Td>
                      <div className="font-editorial">{s.tv_project_title}</div>
                      {s.parent_proposal_id && (
                        <div className="text-[10px] font-mono-imh text-[#0033A0] mt-1">
                          Revision of #{String(s.parent_proposal_id).slice(0, 8)}
                        </div>
                      )}
                    </Td>
                    <Td>{s.client_reference || s.client_name || "—"}</Td>
                    <Td className="text-right font-mono-imh">{s.episode_count}</Td>
                    <Td>
                      <span className="inline-block px-2 py-0.5 text-[10px] uppercase tracking-widest font-mono-imh"
                            style={{ background: st.bg, color: st.color }} data-testid={`sp-status-${s.id}`}>{st.label}</span>
                      {feedback && <div className="text-xs text-[#52525B] italic mt-1 max-w-md">Feedback: {feedback}</div>}
                    </Td>
                    <Td className="text-right">
                      <div className="inline-flex items-center gap-1">
                        <button onClick={() => setHistoryOf(s)}
                          data-testid={`sp-history-${s.id}`}
                          className="h-8 px-2 border border-[#E4E4E1] hover:border-[#0A0A0A] text-[11px] uppercase tracking-widest inline-flex items-center gap-1"
                          style={{ transition: "border-color 120ms" }}>
                          <History size={12} /> History
                        </button>
                        {canDuplicate && (
                          <button onClick={() => setDuplicateOf(s)}
                            data-testid={`sp-duplicate-${s.id}`}
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
                <tr>
                  <Td colSpan={5} className="text-center py-16 text-[#52525B]">No sponsorship proposals yet.</Td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <ProposalHistoryDrawer open={!!historyOf} onOpenChange={(v) => !v && setHistoryOf(null)}
                             proposal={historyOf} isAdminView={false} />
      <DuplicateProposalDialog kind="sponsorship" original={duplicateOf}
                                open={!!duplicateOf} onOpenChange={(v) => !v && setDuplicateOf(null)}
                                onDone={load} />
    </div>
  );
}

const Th = ({ children, className = "" }) => <th className={`px-6 py-4 text-[11px] uppercase tracking-widest text-[#52525B] font-medium ${className}`}>{children}</th>;
const Td = ({ children, className = "", colSpan }) => <td colSpan={colSpan} className={`px-6 py-4 text-[#0A0A0A] ${className}`}>{children}</td>;
