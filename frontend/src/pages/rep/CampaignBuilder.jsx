import { useEffect, useMemo, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import api, { formatApiError } from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";
import { Send } from "lucide-react";

export default function BannerProposalBuilder() {
  const nav = useNavigate();
  const [catalog, setCatalog] = useState({ networks: [], positions: [], items: [] });
  const [selectedInv, setSelectedInv] = useState(null);
  const [form, setForm] = useState({
    proposal_name: "", client_reference: "",
    impressions: "",
    start_date: new Date().toISOString().slice(0, 10),
    end_date: (() => { const d = new Date(); d.setDate(d.getDate() + 30); return d.toISOString().slice(0, 10); })(),
    offer_amount_usd: "",
    notes: "",
  });
  const [busy, setBusy] = useState(false);

  useEffect(() => { api.get("/inventory").then(r => setCatalog(r.data)); }, []);

  const grouped = useMemo(() => {
    const g = new Map();
    for (const it of catalog.items) {
      if (!g.has(it.network_key)) g.set(it.network_key, { network_key: it.network_key, network_name: it.network_name, network_tagline: it.network_tagline, items: [] });
      g.get(it.network_key).items.push(it);
    }
    return Array.from(g.values());
  }, [catalog]);

  const submit = async () => {
    if (!selectedInv) return toast.error("Choose an inventory product first");
    if (!form.proposal_name || !form.client_reference || !form.offer_amount_usd)
      return toast.error("Fill proposal name, client reference and offer amount");
    if (Number(form.offer_amount_usd) <= 0) return toast.error("Offer amount must be positive");
    setBusy(true);
    try {
      await api.post("/campaigns", {
        proposal_name: form.proposal_name,
        client_reference: form.client_reference,
        inventory_id: selectedInv.id,
        impressions: form.impressions ? Number(form.impressions) : null,
        start_date: form.start_date || undefined,
        end_date: form.end_date || undefined,
        offer_amount_usd: Number(form.offer_amount_usd),
        notes: form.notes,
      });
      toast.success("Commercial proposal submitted");
      nav("/rep/banners");
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
    finally { setBusy(false); }
  };

  return (
    <div>
      <PageHeader
        eyebrow="Banner Inventory · Commercial Proposal"
        title="Submit a proposal"
        description="Browse the network inventory, choose one product, and submit a confidential commercial proposal to Independent Media Network. Your customer relationship stays private — the platform never sees it."
        actions={<Link to="/rep/banners" className="text-sm text-[#52525B] hover:text-[#0A0A0A]" data-testid="back-proposals">← All proposals</Link>}
      />
      <div className="px-10 py-10 grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: catalog */}
        <div className="lg:col-span-8 space-y-6">
          {grouped.map(g => (
            <section key={g.network_key} className="imh-card overflow-hidden" data-testid={`network-${g.network_key}`}>
              <div className="px-6 py-4 border-b border-[#E4E4E1] flex items-baseline justify-between">
                <div>
                  <div className="imh-eyebrow">{g.network_key.replace("_", " ").toUpperCase()}</div>
                  <h3 className="font-editorial text-xl mt-1">{g.network_name}</h3>
                  <p className="text-xs text-[#52525B] mt-1">{g.network_tagline}</p>
                </div>
                <span className="text-[11px] font-mono-imh text-[#52525B]">{g.items.length} products</span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2">
                {g.items.map(it => {
                  const isSel = selectedInv?.id === it.id;
                  return (
                    <button key={it.id} onClick={() => setSelectedInv(it)}
                      data-testid={`inv-${it.id}`}
                      className={`text-left p-5 border-b border-r border-[#E4E4E1] last:border-r-0 ${isSel ? "bg-[#0A1128] text-white" : "bg-white hover:bg-[#F9F9F6]"}`}
                      style={{ transition: "background 120ms" }}>
                      <div className={`imh-eyebrow ${isSel ? "!text-[#B8C1DA]" : ""}`}>{it.position_key.replace("_", " ")}</div>
                      <div className="font-editorial text-lg mt-1">{it.position_name}</div>
                      <div className={`text-xs mt-2 ${isSel ? "text-[#B8C1DA]" : "text-[#52525B]"}`}>{it.position_description}</div>
                    </button>
                  );
                })}
              </div>
            </section>
          ))}
        </div>

        {/* Right: proposal form */}
        <div className="lg:col-span-4">
          <div className="imh-card p-6 sticky top-6" data-testid="proposal-form">
            <div className="imh-eyebrow">Commercial proposal</div>
            {selectedInv ? (
              <div className="mt-2 mb-4 border-l-2 border-[#0033A0] pl-3">
                <div className="text-[11px] uppercase tracking-widest text-[#52525B]">{selectedInv.network_name}</div>
                <div className="font-editorial text-xl">{selectedInv.position_name}</div>
              </div>
            ) : (
              <div className="mt-2 mb-4 text-sm text-[#52525B] italic">Select an inventory product from the catalog on the left.</div>
            )}

            <div className="space-y-4">
              <F label="Proposal name"><Input data-testid="proposal-name" value={form.proposal_name} onChange={e => setForm({ ...form, proposal_name: e.target.value })} /></F>
              <F label="Client reference (private label)"><Input data-testid="proposal-client-ref" value={form.client_reference} onChange={e => setForm({ ...form, client_reference: e.target.value })} /></F>
              <F label="Requested impressions (optional)"><Input data-testid="proposal-impressions" type="number" placeholder="Negotiable" value={form.impressions} onChange={e => setForm({ ...form, impressions: e.target.value })} /></F>
              <div className="grid grid-cols-2 gap-3">
                <F label="Start date"><Input data-testid="proposal-start" type="date" value={form.start_date} onChange={e => setForm({ ...form, start_date: e.target.value })} /></F>
                <F label="End date"><Input data-testid="proposal-end" type="date" value={form.end_date} onChange={e => setForm({ ...form, end_date: e.target.value })} /></F>
              </div>
              <F label="Your offer to Independent Media Network (USD)"><Input data-testid="proposal-offer" type="number" placeholder="Confidential" value={form.offer_amount_usd} onChange={e => setForm({ ...form, offer_amount_usd: e.target.value })} /></F>
              <F label="Notes"><Textarea data-testid="proposal-notes" rows={3} className="rounded-none" value={form.notes} onChange={e => setForm({ ...form, notes: e.target.value })} /></F>
            </div>

            <Button onClick={submit} disabled={busy || !selectedInv} data-testid="submit-proposal"
              className="mt-6 w-full h-11 rounded-none bg-[#0033A0] hover:bg-[#002277] text-white">
              {busy ? "Submitting…" : "Submit for review"} <Send size={14} className="ml-2" />
            </Button>
            <p className="mt-3 text-[11px] text-[#52525B]">Your proposal is confidential. Independent Media Network administrators will approve, reject, or request a revision.</p>
          </div>
        </div>
      </div>
    </div>
  );
}

const F = ({ label, children }) => (
  <div><Label className="text-[11px] uppercase tracking-widest text-[#52525B]">{label}</Label><div className="mt-2">{children}</div></div>
);
