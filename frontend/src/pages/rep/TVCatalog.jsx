import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "@/lib/api";
import PageHeader from "@/components/PageHeader";

const STATUS_STYLE = {
  submitted:          { color: "#B45309", label: "Application submitted" },
  revision_requested: { color: "#0033A0", label: "Revision requested" },
  approved:           { color: "#166534", label: "Production approved" },
  rejected:           { color: "#991B1B", label: "Application declined" },
};

export default function TVCatalog() {
  const [items, setItems] = useState([]);
  useEffect(() => { api.get("/tv-projects").then(r => setItems(r.data)); }, []);
  return (
    <div>
      <PageHeader eyebrow="Independent Projects" title="Project Library"
                   description="Premium project packages ready for country partner production. Each project ships with a production bible, brand guidelines and download center." />
      <div className="px-10 py-10">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8" data-testid="tv-catalog-grid">
          {items.map((p, i) => {
            const applied = p.my_application_status;
            const badge = STATUS_STYLE[applied];
            return (
              <Link key={p.id} to={`/rep/tv/${p.id}`}
                    className="group imh-card overflow-hidden hover:border-[#0A0A0A]"
                    style={{ transition: "border-color 200ms ease" }}
                    data-testid={`tv-tile-${p.id}`}>
                <div className="aspect-[16/9] bg-[#0A1128] overflow-hidden relative">
                  {p.hero_image_url && <img src={p.hero_image_url} alt="" className="w-full h-full object-cover group-hover:scale-[1.02]"
                                              style={{ transition: "transform 500ms ease" }} />}
                  {badge && (
                    <span className="absolute top-3 left-3 text-[10px] uppercase tracking-widest font-mono-imh px-2 py-1"
                           style={{ background: badge.color, color: "#fff" }}>
                      {badge.label}
                    </span>
                  )}
                </div>
                <div className="p-6">
                  <div className="flex items-center justify-between">
                    <span className="imh-eyebrow">{(p.category_slug || p.category || "TV Formats").replace(/_/g, " ")}</span>
                    <span className="font-mono-imh text-[11px] text-[#52525B]">{String(i+1).padStart(2,"0")} / {String(items.length).padStart(2,"0")}</span>
                  </div>
                  <h3 className="font-editorial text-3xl mt-3 leading-tight">{p.title}</h3>
                  <p className="text-[15px] text-[#52525B] mt-3 line-clamp-2 leading-relaxed">{p.tagline}</p>
                  <div className="mt-6 grid grid-cols-3 gap-4 border-t border-[#E4E4E1] pt-5">
                    <Stat label="Episodes" value={p.total_episodes} />
                    <Stat label="Applications" value={p.approved_applications_count || 0} />
                    <Stat label="Model" value="Produce" />
                  </div>
                </div>
              </Link>
            );
          })}
          {items.length === 0 && (
            <div className="col-span-full imh-card p-16 text-center text-[#52525B]">
              No projects are currently open to production. Check back soon — the network publishes new projects regularly.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
const Stat = ({ label, value }) => (
  <div><div className="text-[10px] uppercase tracking-widest text-[#A1A1AA]">{label}</div><div className="font-mono-imh text-lg mt-1 text-[#0A0A0A]">{value}</div></div>
);
