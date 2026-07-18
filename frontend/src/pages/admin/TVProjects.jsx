import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import api, { formatApiError } from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { Plus, Star, Archive, EyeOff, Send } from "lucide-react";

const STATUS_STYLE = {
  active: { bg: "#E6F2EA", color: "#166534", label: "Active" },
  draft:  { bg: "#F5F0E1", color: "#B45309", label: "Draft" },
  closed: { bg: "#EBEBE6", color: "#52525B", label: "Closed" },
};
const MOD_STYLE = {
  approved:           { color: "#166534", label: "Approved" },
  submitted:          { color: "#B45309", label: "Submitted" },
  revision_requested: { color: "#0033A0", label: "Revision" },
  rejected:           { color: "#991B1B", label: "Rejected" },
  draft:              { color: "#52525B", label: "Draft" },
};
const SOURCE_STYLE = {
  admin:   { color: "#0A0A0A", label: "Official" },
  partner: { color: "#0033A0", label: "Partner" },
};
const FILTERS = [
  { value: "all", label: "All" },
  { value: "official", label: "Official" },
  { value: "partner", label: "Partner submissions" },
  { value: "featured", label: "Featured" },
  { value: "archived", label: "Archived" },
];

export default function TVProjects() {
  const [projects, setProjects] = useState([]);
  const [filter, setFilter] = useState("all");
  const nav = useNavigate();

  const load = () => api.get("/tv-projects").then(r => setProjects(r.data));
  useEffect(() => { load(); }, []);

  const shown = projects.filter(p => {
    if (filter === "all") return !p.archived;
    if (filter === "official") return p.source !== "partner" && !p.archived;
    if (filter === "partner") return p.source === "partner" && !p.archived;
    if (filter === "featured") return p.featured && !p.archived;
    if (filter === "archived") return p.archived;
    return true;
  });

  return (
    <div>
      <PageHeader
        eyebrow="Project Library"
        title="Projects"
        description="Modular project packages ready for country partner production. Click any project to open its complete Project Page and moderate in place. Admin-created Official Projects sit next to partner submissions — one library, one editor, one moderation flow."
        actions={
          <div className="flex gap-2 items-center">
            <div className="flex gap-1 border border-[#E4E4E1] bg-white" data-testid="tv-source-filter">
              {FILTERS.map(f => (
                <button key={f.value} onClick={() => setFilter(f.value)}
                  className={`px-3 py-2 text-[11px] uppercase tracking-widest ${filter === f.value ? "bg-[#0A0A0A] text-white" : "text-[#0A0A0A] hover:bg-[#F9F9F6]"}`}
                  data-testid={`filter-${f.value}`}>{f.label}</button>
              ))}
            </div>
            <Button data-testid="new-project-btn" onClick={() => nav("/admin/tv-projects/new")}
                     className="rounded-none h-10 bg-[#0033A0] hover:bg-[#002277] text-white">
              <Plus size={16} className="mr-2" /> New project
            </Button>
          </div>
        }
      />
      <div className="px-10 py-10 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {shown.map(p => {
          const s = STATUS_STYLE[p.status] || STATUS_STYLE.draft;
          const mod = MOD_STYLE[p.moderation_status] || MOD_STYLE.approved;
          const src = SOURCE_STYLE[p.source] || SOURCE_STYLE.admin;
          return (
            <Link key={p.id} to={`/admin/tv-projects/${p.id}`}
                   className="imh-card group overflow-hidden hover:border-[#0A0A0A]"
                   style={{ transition: "border-color 160ms ease" }}
                   data-testid={`tv-card-${p.id}`}>
              <div className="aspect-[16/10] bg-[#0A1128] overflow-hidden relative">
                {p.hero_image_url ? <img src={p.hero_image_url} alt="" className="w-full h-full object-cover group-hover:scale-[1.02]" style={{ transition: "transform 400ms ease" }} /> : null}
                {p.featured && <span className="absolute top-3 left-3 px-2 py-1 text-[10px] font-mono-imh uppercase tracking-widest bg-[#B45309] text-white flex items-center gap-1"><Star size={10} /> Featured</span>}
                {p.archived && <span className="absolute top-3 right-3 px-2 py-1 text-[10px] font-mono-imh uppercase tracking-widest bg-[#991B1B] text-white flex items-center gap-1"><Archive size={10} /> Archived</span>}
              </div>
              <div className="p-5">
                <div className="flex items-center justify-between flex-wrap gap-1">
                  <div className="imh-eyebrow flex items-center gap-2">
                    <span style={{ color: src.color }}>{src.label}</span>
                    <span className="text-[#A1A1AA]">·</span>
                    <span>{p.total_episodes || 0} episodes</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <span className="px-2 py-0.5 text-[10px] uppercase tracking-widest font-mono-imh" style={{ background: s.bg, color: s.color }}>{s.label}</span>
                    {!p.published && <span className="px-2 py-0.5 text-[10px] uppercase tracking-widest font-mono-imh border border-[#52525B] text-[#52525B]"><EyeOff size={9} className="inline mr-0.5" /> Hidden</span>}
                  </div>
                </div>
                <h3 className="font-editorial text-2xl mt-2 leading-tight">{p.title}</h3>
                <p className="text-sm text-[#52525B] mt-2 line-clamp-2">{p.tagline || p.overview || p.synopsis}</p>
                <div className="mt-4 flex items-center justify-between text-xs text-[#52525B]">
                  <span>{p.approved_applications_count || 0} approved · {p.pending_applications_count || 0} pending</span>
                  {p.source === "partner" && <span className="inline-flex items-center gap-1" style={{ color: mod.color }}><Send size={10} /> {mod.label}</span>}
                </div>
              </div>
            </Link>
          );
        })}
        {shown.length === 0 && <div className="col-span-full text-center py-16 text-[#52525B]">No projects match this filter.</div>}
      </div>
    </div>
  );
}
