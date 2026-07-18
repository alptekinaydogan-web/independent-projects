import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import api from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { Plus, Send, Sparkles, Rewind, Check, X } from "lucide-react";

const STATUS_STYLE = {
  draft:              { bg: "#EBEBE6", color: "#52525B", label: "Draft" },
  submitted:          { bg: "#F5F0E1", color: "#B45309", label: "Awaiting review" },
  revision_requested: { bg: "#EEF2FF", color: "#0033A0", label: "Revision requested" },
  approved:           { bg: "#E6F2EA", color: "#166534", label: "Approved" },
  rejected:           { bg: "#FBEBEB", color: "#991B1B", label: "Not approved" },
};
const ICON = { submitted: Send, revision_requested: Rewind, approved: Check, rejected: X, draft: Plus };

export default function SubmitProposal() {
  const [items, setItems] = useState([]);
  const nav = useNavigate();

  const load = () => api.get("/my-projects").then(r => setItems(r.data));
  useEffect(() => { load(); }, []);

  return (
    <div>
      <PageHeader eyebrow="Country Partner Submissions" title="Your projects"
                   description="Pitch new project ideas using the same professional editor Independent Media Network administrators use. Save drafts freely, submit when ready, and pick your revisions right up from where you left off."
                   actions={
                    <Button onClick={() => nav("/rep/projects/new")} data-testid="rep-new-project"
                             className="rounded-none h-10 bg-[#0033A0] hover:bg-[#002277] text-white">
                      <Plus size={14} className="mr-2" /> New project
                    </Button>
                   } />
      <div className="px-10 py-10 grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {items.length === 0 && (
          <div className="col-span-full imh-card p-16 text-center text-[#52525B]">
            <Sparkles size={22} className="mx-auto text-[#0033A0]" />
            <div className="mt-3">You haven't submitted any projects yet. Click <b>New project</b> to open the editor.</div>
          </div>
        )}
        {items.map(p => {
          const s = STATUS_STYLE[p.moderation_status] || STATUS_STYLE.draft;
          const Ico = ICON[p.moderation_status] || Sparkles;
          return (
            <Link key={p.id} to={`/rep/projects/${p.id}`} data-testid={`my-project-${p.id}`}
                   className="imh-card p-5 hover:border-[#0A0A0A]" style={{ transition: "border-color 160ms" }}>
              <div className="flex items-center gap-2">
                <span className="px-2 py-0.5 text-[10px] uppercase tracking-widest font-mono-imh flex items-center gap-1" style={{ background: s.bg, color: s.color }}>
                  <Ico size={10} /> {s.label}
                </span>
                <span className="ml-auto text-[10px] font-mono-imh text-[#A1A1AA]">{p.production_format || "—"}</span>
              </div>
              <h3 className="font-editorial text-xl mt-2">{p.title || "Untitled draft"}</h3>
              <p className="text-sm text-[#52525B] mt-2 line-clamp-3">{p.overview || p.synopsis || "No description yet."}</p>
              {p.admin_feedback && (
                <div className="mt-3 border-l-2 border-[#0033A0] pl-3 text-xs italic text-[#0A0A0A]">"{p.admin_feedback}"</div>
              )}
              <div className="mt-4 text-[10px] font-mono-imh text-[#A1A1AA]">
                {p.moderation_status === "draft" ? `Draft since ${(p.created_at || "").slice(0, 10)}` : `Submitted ${(p.submitted_at || p.created_at || "").slice(0, 10)}`}
              </div>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
