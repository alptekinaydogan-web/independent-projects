import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from "@/components/ui/sheet";
import { CheckCircle2, XCircle, Clock, RefreshCcw, RotateCcw, Archive, ArchiveRestore } from "lucide-react";

const STATUS_META = {
  submitted:          { label: "Submitted",          Icon: Clock,         color: "#B45309", bg: "#F5F0E1" },
  pending_review:     { label: "Submitted",          Icon: Clock,         color: "#B45309", bg: "#F5F0E1" },
  revision_requested: { label: "Revision Requested", Icon: RefreshCcw,    color: "#0033A0", bg: "#EEF2FF" },
  revised:            { label: "Revised",            Icon: RotateCcw,     color: "#0033A0", bg: "#EEF2FF" },
  approved:           { label: "Approved",           Icon: CheckCircle2,  color: "#166534", bg: "#E6F2EA" },
  rejected:           { label: "Rejected",           Icon: XCircle,       color: "#991B1B", bg: "#FBEBEB" },
  archived:           { label: "Archived",           Icon: Archive,       color: "#52525B", bg: "#EFEEEA" },
  unarchived:         { label: "Unarchived",         Icon: ArchiveRestore, color: "#52525B", bg: "#EFEEEA" },
};

const fmtDate = (iso) => {
  if (!iso) return "";
  try {
    const d = new Date(iso);
    return d.toLocaleString(undefined, { year: "numeric", month: "short", day: "2-digit", hour: "2-digit", minute: "2-digit" });
  } catch { return iso; }
};

export default function ProposalHistoryDrawer({ open, onOpenChange, proposal, isAdminView = false }) {
  const history = Array.isArray(proposal?.history) ? proposal.history : [];
  const title = proposal?.campaign_name || proposal?.proposal_name || "Proposal";
  const subtitle = proposal?.kind === "banner"
    ? `${proposal?.network_name || ""} · ${proposal?.position_name || ""}`
    : `${proposal?.tv_project_title || ""} · ${proposal?.episode_count || (proposal?.episode_numbers || []).length || 0} episode(s)`;

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="rounded-none sm:max-w-md w-full border-l border-[#E4E4E1] bg-white p-0 overflow-y-auto" data-testid="proposal-history-drawer">
        <SheetHeader className="px-6 pt-6 pb-4 border-b border-[#E4E4E1] text-left">
          <div className="imh-eyebrow">Proposal history</div>
          <SheetTitle className="font-editorial text-2xl">{title}</SheetTitle>
          <SheetDescription className="text-xs text-[#52525B]">{subtitle}</SheetDescription>
          {proposal?.parent_proposal_id && (
            <div className="mt-2 text-[11px] font-mono-imh text-[#52525B]">
              Revision of&nbsp;
              <span className="text-[#0033A0]">#{String(proposal.parent_proposal_id).slice(0, 8)}</span>
            </div>
          )}
        </SheetHeader>

        <div className="px-6 py-6 space-y-4">
          {history.length === 0 && (
            <div className="text-sm text-[#52525B] italic">
              No lifecycle history recorded yet. Historic proposals created before the history feature will only show new events going forward.
            </div>
          )}
          <ol className="relative border-l border-[#E4E4E1] ml-3 space-y-6">
            {history.map((h, i) => {
              const meta = STATUS_META[h.status] || { label: h.status, Icon: Clock, color: "#0A0A0A", bg: "#F9F9F6" };
              const Icon = meta.Icon;
              return (
                <li key={i} className="pl-6" data-testid={`history-entry-${i}`}>
                  <span className="absolute -left-[9px] flex items-center justify-center w-4 h-4 border border-[#E4E4E1]"
                        style={{ background: meta.bg, color: meta.color }}>
                    <Icon size={9} strokeWidth={2} />
                  </span>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="inline-block px-2 py-0.5 text-[10px] uppercase tracking-widest font-mono-imh"
                          style={{ background: meta.bg, color: meta.color }}>
                      {meta.label}
                    </span>
                    <span className="text-[11px] font-mono-imh text-[#52525B]">{fmtDate(h.at)}</span>
                  </div>
                  <div className="text-xs text-[#52525B]">
                    by <span className="text-[#0A0A0A]">{h.actor_name || "—"}</span>
                    {h.actor_role && <span className="text-[#A1A1AA]"> · {h.actor_role}</span>}
                  </div>
                  {h.representative_feedback && (
                    <div className="mt-2 text-sm text-[#0A0A0A] bg-[#F9F9F6] border-l-2 border-[#0033A0] px-3 py-2">
                      <div className="imh-eyebrow" style={{ color: "#0033A0" }}>Feedback to you</div>
                      <div className="mt-1">{h.representative_feedback}</div>
                    </div>
                  )}
                  {isAdminView && h.internal_notes && (
                    <div className="mt-2 text-sm bg-[#FFFAF3] border-l-2 border-[#B45309] px-3 py-2">
                      <div className="imh-eyebrow" style={{ color: "#B45309" }}>Internal (admin only)</div>
                      <div className="mt-1 text-[#0A0A0A]">{h.internal_notes}</div>
                    </div>
                  )}
                </li>
              );
            })}
          </ol>
        </div>
      </SheetContent>
    </Sheet>
  );
}

export { STATUS_META };
