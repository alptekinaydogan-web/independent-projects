import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import api from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import { useAuth } from "@/contexts/AuthContext";
import { ArrowUpRight } from "lucide-react";

export default function InventoryCatalog() {
  const { user } = useAuth();
  const isAdmin = user?.role === "owner" || user?.role === "admin";
  const base = isAdmin ? "/admin/inventory" : "/rep/inventory";
  const [data, setData] = useState({ networks: [], positions: [], items: [] });
  useEffect(() => { api.get("/inventory").then(r => setData(r.data)); }, []);

  const grouped = useMemo(() => {
    const g = new Map();
    for (const it of data.items) {
      if (!g.has(it.network_key)) g.set(it.network_key, { key: it.network_key, name: it.network_name, tagline: it.network_tagline, items: [] });
      g.get(it.network_key).items.push(it);
    }
    return Array.from(g.values());
  }, [data]);

  return (
    <div>
      <PageHeader eyebrow="Independent Media Network" title="Inventory catalog"
        description="Standardized advertising products across the Global Network and every thematic sub-network. Each product spans the entire relevant network — one line item, complete coverage." />
      <div className="px-10 py-10 space-y-6">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <Metric label="Networks" value={data.networks.length} testId="inv-metric-networks" />
          <Metric label="Positions" value={data.positions.length} testId="inv-metric-positions" />
          <Metric label="Products in catalog" value={data.items.length} testId="inv-metric-items" />
          <Metric label="Commercial model" value="Proposal-based" testId="inv-metric-model" />
        </div>

        {grouped.map(g => (
          <section key={g.key} className="imh-card overflow-hidden" data-testid={`inv-network-${g.key}`}>
            <div className="px-6 py-4 border-b border-[#E4E4E1] flex items-baseline justify-between">
              <div>
                <div className="imh-eyebrow">{g.key.replace("_", " ").toUpperCase()}</div>
                <h3 className="font-editorial text-xl mt-1">{g.name}</h3>
                <p className="text-xs text-[#52525B] mt-1">{g.tagline}</p>
              </div>
              <span className="text-[11px] font-mono-imh text-[#52525B]">{g.items.length} products</span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
              {g.items.map(it => (
                <Link key={it.id} to={`${base}/${it.id}`}
                      className="group p-5 border-b border-r border-[#E4E4E1] last:border-r-0 hover:bg-[#F9F9F6] block"
                      style={{ transition: "background 120ms" }}
                      data-testid={`inv-item-${it.id}`}>
                  <div className="imh-eyebrow flex items-center justify-between">
                    <span>{it.position_key.replace("_", " ")}</span>
                    <ArrowUpRight size={12} className="opacity-0 group-hover:opacity-100 text-[#0033A0]" style={{ transition: "opacity 120ms" }} />
                  </div>
                  <div className="font-editorial text-lg mt-1 group-hover:text-[#0033A0]" style={{ transition: "color 120ms" }}>{it.position_name}</div>
                  <div className="text-xs text-[#52525B] mt-2">{it.position_description}</div>
                </Link>
              ))}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}

function Metric({ label, value, testId }) {
  return (
    <div className="imh-card p-6" data-testid={testId}>
      <div className="imh-eyebrow">{label}</div>
      <div className="imh-metric-number text-3xl mt-3">{value}</div>
    </div>
  );
}
