import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import { usd } from "@/lib/constants";

export default function TVCatalog() {
  const [items, setItems] = useState([]);
  useEffect(() => { api.get("/tv-projects").then(r => setItems(r.data)); }, []);
  return (
    <div>
      <PageHeader eyebrow="Independent TV" title="Sponsorship catalog"
        description="Original productions from Independent TV. Each project presents like an investment proposal — read the vision, then decide which episodes to sponsor." />
      <div className="px-10 py-10">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8" data-testid="tv-catalog-grid">
          {items.map((p, i) => {
            const sponsored = p.sponsored_episodes?.length || 0;
            const pct = Math.round((sponsored / (p.total_episodes || 1)) * 100);
            return (
              <Link key={p.id} to={`/rep/tv/${p.id}`} className="group imh-card overflow-hidden hover:border-[#0A0A0A]" style={{ transition: "border-color 200ms ease" }} data-testid={`tv-tile-${p.id}`}>
                <div className="aspect-[16/9] bg-[#0A1128] overflow-hidden">
                  {p.hero_image_url && <img src={p.hero_image_url} alt="" className="w-full h-full object-cover group-hover:scale-[1.02]" style={{ transition: "transform 500ms ease" }} />}
                </div>
                <div className="p-6">
                  <div className="flex items-center justify-between">
                    <span className="imh-eyebrow">Now Available</span>
                    <span className="font-mono-imh text-[11px] text-[#52525B]">{String(i+1).padStart(2,"0")} / {String(items.length).padStart(2,"0")}</span>
                  </div>
                  <h3 className="font-editorial text-3xl mt-3 leading-tight">{p.title}</h3>
                  <p className="text-[15px] text-[#52525B] mt-3 line-clamp-2 leading-relaxed">{p.tagline}</p>
                  <div className="mt-6 grid grid-cols-3 gap-4 border-t border-[#E4E4E1] pt-5">
                    <Stat label="Episodes" value={p.total_episodes} />
                    <Stat label="Sponsored" value={`${pct}%`} />
                    <Stat label="Model" value="Proposal" />
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      </div>
    </div>
  );
}
const Stat = ({ label, value }) => (
  <div><div className="text-[10px] uppercase tracking-widest text-[#A1A1AA]">{label}</div><div className="font-mono-imh text-lg mt-1 text-[#0A0A0A]">{value}</div></div>
);
