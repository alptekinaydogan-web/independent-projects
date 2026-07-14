import { useEffect, useState, useMemo } from "react";
import api, { formatApiError } from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { REGIONS, usd } from "@/lib/constants";
import { Save } from "lucide-react";

export default function BannerInventory() {
  const [rows, setRows] = useState([]);
  const [dirty, setDirty] = useState({});
  const [filter, setFilter] = useState("All");

  useEffect(() => { api.get("/banner-inventory").then(r => setRows(r.data)); }, []);

  const grouped = useMemo(() => {
    const map = {};
    for (const r of rows) {
      if (filter !== "All" && r.region !== filter) continue;
      (map[r.region] ||= []).push(r);
    }
    for (const k of Object.keys(map)) map[k].sort((a, b) => a.country_name.localeCompare(b.country_name));
    return map;
  }, [rows, filter]);

  const setPrice = (code, price) => {
    setRows(rows.map(r => r.country_code === code ? { ...r, price_cpm_usd: price } : r));
    setDirty({ ...dirty, [code]: true });
  };

  const saveAll = async () => {
    const changed = rows.filter(r => dirty[r.country_code]);
    if (changed.length === 0) { toast.info("No changes to save"); return; }
    try {
      await Promise.all(changed.map(r => api.put(`/admin/banner-inventory/${r.country_code}`, {
        country_code: r.country_code, country_name: r.country_name, region: r.region,
        price_cpm_usd: Number(r.price_cpm_usd) || 0, min_impressions: r.min_impressions || 10000,
      })));
      toast.success(`Saved ${changed.length} price update(s)`);
      setDirty({});
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };

  return (
    <div>
      <PageHeader
        eyebrow="Commercial · Inventory"
        title="Banner Inventory"
        description="Internal CPM pricing per country. These are representative costs — representatives sell at their own margin."
        actions={
          <Button onClick={saveAll} data-testid="save-inventory" className="rounded-none bg-[#0033A0] hover:bg-[#002277] text-white h-10">
            <Save size={16} className="mr-2" /> Save changes ({Object.keys(dirty).length})
          </Button>
        }
      />
      <div className="px-10 py-10 space-y-8">
        <div className="flex items-center gap-2 flex-wrap" data-testid="region-filter">
          {["All", ...REGIONS].map(r => (
            <button key={r} onClick={() => setFilter(r)}
              className={`px-3 py-2 text-xs uppercase tracking-widest border ${filter === r ? "bg-[#0A0A0A] text-white border-[#0A0A0A]" : "bg-white text-[#0A0A0A] border-[#E4E4E1] hover:border-[#0A0A0A]"}`}>
              {r}
            </button>
          ))}
        </div>

        {Object.entries(grouped).map(([region, items]) => (
          <section key={region} className="imh-card">
            <div className="px-6 py-4 border-b border-[#E4E4E1] flex items-center justify-between">
              <h3 className="font-editorial text-xl">{region}</h3>
              <span className="text-xs text-[#52525B] font-mono-imh">{items.length} countries</span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
              {items.map(r => (
                <div key={r.country_code} className="p-6 border-b border-r border-[#E4E4E1] last:border-r-0" data-testid={`inv-${r.country_code}`}>
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="font-mono-imh text-xs text-[#A1A1AA]">{r.country_code}</div>
                      <div className="text-base">{r.country_name}</div>
                    </div>
                    {dirty[r.country_code] && <span className="text-[10px] uppercase tracking-widest text-[#B45309]">Unsaved</span>}
                  </div>
                  <div className="mt-4 flex items-center gap-2">
                    <span className="text-[11px] uppercase tracking-widest text-[#52525B]">CPM USD</span>
                    <Input
                      value={r.price_cpm_usd}
                      onChange={(e) => setPrice(r.country_code, e.target.value)}
                      type="number" step="0.5"
                      data-testid={`inv-price-${r.country_code}`}
                      className="rounded-none h-9 font-mono-imh" />
                  </div>
                  <div className="mt-3 text-[11px] text-[#52525B]">
                    Preview at 100k impressions: <span className="font-mono-imh text-[#0A0A0A]">{usd((r.price_cpm_usd || 0) * 100)}</span>
                  </div>
                </div>
              ))}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}
