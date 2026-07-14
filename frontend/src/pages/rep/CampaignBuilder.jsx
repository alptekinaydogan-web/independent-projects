import { useEffect, useMemo, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import api, { formatApiError } from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { toast } from "sonner";
import { REGIONS, usd } from "@/lib/constants";
import { ArrowRight } from "lucide-react";

export default function CampaignBuilder() {
  const nav = useNavigate();
  const [inv, setInv] = useState([]);
  const [selected, setSelected] = useState(new Set());
  const [impressions, setImpressions] = useState(500000);
  const [campaignName, setCampaignName] = useState("");
  const [clientName, setClientName] = useState("");
  const [clientPrice, setClientPrice] = useState("");
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => { api.get("/banner-inventory").then(r => setInv(r.data)); }, []);

  const grouped = useMemo(() => {
    const g = {};
    for (const i of inv) (g[i.region] ||= []).push(i);
    for (const k of Object.keys(g)) g[k].sort((a, b) => a.country_name.localeCompare(b.country_name));
    return g;
  }, [inv]);

  const toggle = (code) => {
    const s = new Set(selected);
    s.has(code) ? s.delete(code) : s.add(code);
    setSelected(s);
  };

  const toggleRegion = (region) => {
    const s = new Set(selected);
    const codes = grouped[region].map(i => i.country_code);
    const allSelected = codes.every(c => s.has(c));
    codes.forEach(c => { allSelected ? s.delete(c) : s.add(c); });
    setSelected(s);
  };

  const selectAll = () => setSelected(new Set(inv.map(i => i.country_code)));
  const clear = () => setSelected(new Set());

  const perCountry = useMemo(() => {
    return inv.filter(i => selected.has(i.country_code)).map(i => ({
      ...i, internal_cost: Math.round(i.price_cpm_usd * impressions / 1000 * 100) / 100
    }));
  }, [inv, selected, impressions]);

  const totalInternal = perCountry.reduce((a, b) => a + b.internal_cost, 0);
  const priceNum = Number(clientPrice) || 0;
  const margin = Math.round((priceNum - totalInternal) * 100) / 100;
  const marginPct = priceNum > 0 ? Math.round((margin / priceNum) * 100) : 0;

  const submit = async () => {
    if (!campaignName || !clientName || selected.size === 0 || !impressions || !priceNum) {
      toast.error("Fill all fields and select at least one country"); return;
    }
    setBusy(true);
    try {
      await api.post("/campaigns", {
        campaign_name: campaignName, client_name: clientName,
        country_codes: Array.from(selected),
        impressions: Number(impressions),
        client_total_price: priceNum, notes,
      });
      toast.success("Campaign confirmed");
      nav("/rep/banners");
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
    finally { setBusy(false); }
  };

  return (
    <div>
      <PageHeader eyebrow="Banner Campaigns" title="Build a new campaign"
        description="Select target countries, set impressions and your client selling price. Internal costs shown are yours — never disclosed to your client."
        actions={<Link to="/rep/banners" className="text-sm text-[#52525B] hover:text-[#0A0A0A]">← All campaigns</Link>} />

      <div className="px-10 py-10 grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: country picker */}
        <div className="lg:col-span-8 imh-card">
          <div className="px-6 py-4 border-b border-[#E4E4E1] flex items-center justify-between">
            <div>
              <div className="imh-eyebrow">Targeting</div>
              <h3 className="font-editorial text-xl mt-1">Choose countries</h3>
            </div>
            <div className="flex gap-2">
              <button data-testid="select-all" onClick={selectAll} className="px-3 py-1.5 text-xs uppercase tracking-widest border border-[#0A0A0A] hover:bg-[#0A0A0A] hover:text-white" style={{ transition: "background 160ms" }}>Select all</button>
              <button data-testid="clear-all" onClick={clear} className="px-3 py-1.5 text-xs uppercase tracking-widest border border-[#E4E4E1] hover:border-[#0A0A0A]">Clear</button>
            </div>
          </div>
          <div className="divide-y divide-[#E4E4E1]">
            {REGIONS.map(region => (
              <div key={region} className="px-6 py-5">
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <div className="font-editorial text-lg">{region}</div>
                    <div className="text-xs text-[#52525B]">{grouped[region]?.length || 0} countries · Selected {(grouped[region] || []).filter(i => selected.has(i.country_code)).length}</div>
                  </div>
                  <button onClick={() => toggleRegion(region)} data-testid={`toggle-region-${region}`} className="text-xs uppercase tracking-widest text-[#0033A0] hover:text-[#002277]">Toggle region</button>
                </div>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                  {(grouped[region] || []).map(c => {
                    const isSel = selected.has(c.country_code);
                    return (
                      <button key={c.country_code} onClick={() => toggle(c.country_code)}
                        data-testid={`country-${c.country_code}`}
                        className={`flex items-center justify-between px-3 py-2 border text-sm ${isSel ? "bg-[#0033A0] text-white border-[#0033A0]" : "bg-white text-[#0A0A0A] border-[#E4E4E1] hover:border-[#0A0A0A]"}`}
                        style={{ transition: "border-color 120ms ease, background-color 120ms ease" }}>
                        <span className="truncate">{c.country_name}</span>
                        <span className={`font-mono-imh text-[11px] ${isSel ? "text-white/80" : "text-[#52525B]"}`}>${c.price_cpm_usd}</span>
                      </button>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right: summary */}
        <div className="lg:col-span-4 space-y-4">
          <div className="imh-card p-6">
            <div className="imh-eyebrow">Campaign details</div>
            <div className="mt-4 space-y-4">
              <F label="Campaign name"><Input data-testid="campaign-name" value={campaignName} onChange={e => setCampaignName(e.target.value)} /></F>
              <F label="Client name"><Input data-testid="campaign-client" value={clientName} onChange={e => setClientName(e.target.value)} /></F>
              <F label="Impressions per country"><Input data-testid="campaign-impressions" type="number" value={impressions} onChange={e => setImpressions(e.target.value)} /></F>
              <F label="Client total price (USD)"><Input data-testid="campaign-price" type="number" value={clientPrice} onChange={e => setClientPrice(e.target.value)} /></F>
              <F label="Notes"><Input data-testid="campaign-notes" value={notes} onChange={e => setNotes(e.target.value)} /></F>
            </div>
          </div>

          <div className="imh-card p-6" data-testid="campaign-summary">
            <div className="imh-eyebrow">Commercial summary</div>
            <dl className="mt-4 divide-y divide-[#E4E4E1]">
              <Row label="Countries selected" value={<span className="font-mono-imh">{selected.size}</span>} />
              <Row label="Total impressions" value={<span className="font-mono-imh">{Number((impressions || 0) * selected.size).toLocaleString()}</span>} />
              <Row label="Your internal cost" value={<span className="font-mono-imh">{usd(totalInternal)}</span>} />
              <Row label="Client price" value={<span className="font-mono-imh">{usd(priceNum)}</span>} />
              <Row label="Your margin" value={<span className="font-mono-imh" style={{ color: margin >= 0 ? "#166534" : "#991B1B" }}>{usd(margin)} ({marginPct}%)</span>} />
            </dl>
            <Button onClick={submit} disabled={busy} data-testid="submit-campaign"
              className="mt-6 w-full h-11 rounded-none bg-[#0033A0] hover:bg-[#002277] text-white">
              {busy ? "Confirming…" : "Confirm campaign"} <ArrowRight size={16} className="ml-2" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

const F = ({ label, children }) => <div><Label className="text-[11px] uppercase tracking-widest text-[#52525B]">{label}</Label><div className="mt-2">{children}</div></div>;
const Row = ({ label, value }) => <div className="flex items-center justify-between py-2.5 text-sm"><span className="text-[#52525B]">{label}</span><span>{value}</span></div>;
