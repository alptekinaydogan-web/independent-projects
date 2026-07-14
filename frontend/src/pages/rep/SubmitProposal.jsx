import { useEffect, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import api, { formatApiError } from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";

const FORMATS = [
  { value: "documentary", label: "Documentary" },
  { value: "interview_series", label: "Interview series" },
  { value: "travel", label: "Travel series" },
  { value: "investigation", label: "Special investigation" },
  { value: "other", label: "Other" },
];

export default function SubmitProposal() {
  const nav = useNavigate();
  const [countries, setCountries] = useState([]);
  const [items, setItems] = useState([]);
  const [form, setForm] = useState({ title: "", format: "documentary", country: "", description: "", estimated_episodes: 10, budget_hint_usd: 0 });
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.get("/countries").then(r => setCountries(r.data));
    api.get("/proposals").then(r => setItems(r.data));
  }, []);

  const submit = async () => {
    if (!form.title || !form.description || !form.country) { toast.error("Fill required fields"); return; }
    setBusy(true);
    try {
      await api.post("/proposals", { ...form, estimated_episodes: Number(form.estimated_episodes), budget_hint_usd: Number(form.budget_hint_usd) });
      toast.success("Proposal submitted");
      const r = await api.get("/proposals"); setItems(r.data);
      setForm({ title: "", format: "documentary", country: "", description: "", estimated_episodes: 10, budget_hint_usd: 0 });
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
    finally { setBusy(false); }
  };

  return (
    <div>
      <PageHeader eyebrow="Independent TV" title="Pitch a new production"
        description="Have a story worth telling? Submit your idea to Independent TV. Only administrators decide which proposals become official productions." />
      <div className="px-10 py-10 grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-7 imh-card p-6">
          <div className="grid grid-cols-2 gap-4">
            <F label="Working title" full><Input data-testid="proposal-title" value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} /></F>
            <F label="Format">
              <Select value={form.format} onValueChange={v => setForm({ ...form, format: v })}>
                <SelectTrigger data-testid="proposal-format" className="rounded-none h-10"><SelectValue /></SelectTrigger>
                <SelectContent>{FORMATS.map(f => <SelectItem key={f.value} value={f.value}>{f.label}</SelectItem>)}</SelectContent>
              </Select>
            </F>
            <F label="Country">
              <Select value={form.country} onValueChange={v => setForm({ ...form, country: v })}>
                <SelectTrigger data-testid="proposal-country" className="rounded-none h-10"><SelectValue placeholder="Select country" /></SelectTrigger>
                <SelectContent>{countries.map(c => <SelectItem key={c.code} value={c.code}>{c.name}</SelectItem>)}</SelectContent>
              </Select>
            </F>
            <F label="Estimated episodes"><Input data-testid="proposal-episodes" type="number" value={form.estimated_episodes} onChange={e => setForm({ ...form, estimated_episodes: e.target.value })} /></F>
            <F label="Budget hint (USD)"><Input data-testid="proposal-budget" type="number" value={form.budget_hint_usd} onChange={e => setForm({ ...form, budget_hint_usd: e.target.value })} /></F>
            <F label="Concept & synopsis" full><Textarea data-testid="proposal-description" rows={6} className="rounded-none" value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} /></F>
          </div>
          <Button onClick={submit} disabled={busy} data-testid="proposal-submit" className="mt-6 h-11 rounded-none bg-[#0033A0] hover:bg-[#002277]">
            {busy ? "Submitting…" : "Submit proposal"}
          </Button>
        </div>

        <div className="lg:col-span-5">
          <div className="imh-eyebrow">Your submissions</div>
          <div className="mt-3 space-y-3">
            {items.length === 0 && <div className="imh-card p-6 text-sm text-[#52525B]">No proposals submitted yet.</div>}
            {items.map(p => (
              <div key={p.id} className="imh-card p-5" data-testid={`my-proposal-${p.id}`}>
                <div className="flex items-center justify-between">
                  <span className="imh-eyebrow">{p.format} · {p.country}</span>
                  <span className="text-[10px] uppercase tracking-widest px-2 py-0.5"
                    style={{
                      background: p.status === "approved" ? "#E6F2EA" : p.status === "rejected" ? "#FBEBEB" : "#F5F0E1",
                      color: p.status === "approved" ? "#166534" : p.status === "rejected" ? "#991B1B" : "#B45309"
                    }}>
                    {p.status === "in_review" ? "In review" : p.status}
                  </span>
                </div>
                <h4 className="font-editorial text-xl mt-2">{p.title}</h4>
                <p className="text-sm text-[#52525B] mt-2 line-clamp-3">{p.description}</p>
                {p.admin_notes && <div className="text-xs text-[#52525B] italic mt-3">Feedback: {p.admin_notes}</div>}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
const F = ({ label, children, full }) => <div className={full ? "col-span-2" : "col-span-1"}><Label className="text-[11px] uppercase tracking-widest text-[#52525B]">{label}</Label><div className="mt-2">{children}</div></div>;
