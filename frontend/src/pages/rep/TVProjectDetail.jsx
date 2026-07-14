import { useEffect, useMemo, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import api, { formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { usd } from "@/lib/constants";
import { ChevronLeft, PlayCircle } from "lucide-react";

export default function TVProjectDetail() {
  const { id } = useParams();
  const nav = useNavigate();
  const [p, setP] = useState(null);
  const [selected, setSelected] = useState(new Set());
  const [clientName, setClientName] = useState("");
  const [clientPrice, setClientPrice] = useState("");
  const [busy, setBusy] = useState(false);
  const [showVideo, setShowVideo] = useState(false);

  const load = () => api.get(`/tv-projects/${id}`).then(r => setP(r.data));
  useEffect(() => { load(); }, [id]);

  const taken = useMemo(() => new Set((p?.sponsored_episodes || []).map(e => e.episode)), [p]);
  const internal = (selected.size) * (p?.price_per_episode_usd || 0);
  const priceNum = Number(clientPrice) || 0;
  const margin = Math.round((priceNum - internal) * 100) / 100;

  if (!p) return <div className="p-10 imh-eyebrow">Loading…</div>;

  const toggleEp = (n) => {
    if (taken.has(n)) return;
    const s = new Set(selected);
    s.has(n) ? s.delete(n) : s.add(n);
    setSelected(s);
  };

  const submit = async () => {
    if (!clientName || selected.size === 0 || !priceNum) { toast.error("Complete the sponsorship form"); return; }
    setBusy(true);
    try {
      await api.post("/sponsorships", {
        tv_project_id: p.id, client_name: clientName,
        episode_numbers: Array.from(selected), client_total_price: priceNum,
      });
      toast.success("Sponsorship confirmed");
      nav("/rep/sponsorships");
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
    finally { setBusy(false); }
  };

  return (
    <div className="min-h-screen">
      {/* Hero */}
      <div className="relative w-full h-[560px] bg-[#050A18]">
        {p.hero_image_url && <img src={p.hero_image_url} alt="" className="absolute inset-0 w-full h-full object-cover opacity-70" />}
        <div className="absolute inset-0" style={{ background: "linear-gradient(180deg, rgba(5,10,24,0.35) 0%, rgba(5,10,24,0.95) 100%)" }} />
        <div className="relative z-10 h-full max-w-6xl mx-auto px-10 pt-8 pb-14 flex flex-col text-white">
          <Link to="/rep/tv" className="inline-flex items-center gap-1 text-xs uppercase tracking-widest text-[#C7CBD9] hover:text-white" data-testid="back-catalog"><ChevronLeft size={14} /> Sponsorship catalog</Link>
          <div className="mt-auto">
            <div className="imh-eyebrow" style={{ color: "#C7CBD9" }}>Independent TV — Original production</div>
            <h1 className="font-editorial text-6xl leading-[1.02] mt-4 max-w-3xl">{p.title}</h1>
            <p className="mt-6 text-[17px] text-[#D6DAE7] max-w-2xl leading-relaxed">{p.tagline}</p>
            {p.demo_video_url && (
              <button onClick={() => setShowVideo(true)} className="mt-8 inline-flex items-center gap-2 text-sm border border-white/40 px-4 py-2 hover:bg-white hover:text-black" style={{ transition: "background 160ms, color 160ms" }} data-testid="watch-demo">
                <PlayCircle size={18} /> Watch demo
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Body */}
      <div className="max-w-6xl mx-auto px-10 py-16 grid grid-cols-1 lg:grid-cols-12 gap-14">
        <article className="lg:col-span-8">
          <section>
            <div className="imh-eyebrow">Synopsis</div>
            <p className="font-editorial text-2xl leading-relaxed mt-4 text-[#0A0A0A]">{p.synopsis}</p>
          </section>

          <section className="mt-14 grid grid-cols-2 gap-8 border-t border-[#E4E4E1] pt-10">
            <Facts label="Target audience" value={p.target_audience || "—"} />
            <Facts label="Distribution" value={p.distribution || "—"} />
            <Facts label="Languages" value={(p.languages || []).join(", ") || "—"} />
            <Facts label="Episodes" value={p.total_episodes} />
            <Facts label="Internal cost / episode" value={usd(p.price_per_episode_usd)} />
            <Facts label="Currently sponsored" value={`${p.sponsored_episodes?.length || 0} / ${p.total_episodes}`} />
          </section>

          {p.sponsorship_rights && (
            <section className="mt-14 border-t border-[#E4E4E1] pt-10">
              <div className="imh-eyebrow">Sponsorship rights</div>
              <p className="mt-4 text-[15px] leading-relaxed text-[#0A0A0A]">{p.sponsorship_rights}</p>
            </section>
          )}

          <section className="mt-14 border-t border-[#E4E4E1] pt-10">
            <div className="imh-eyebrow">Episode Availability</div>
            <h3 className="font-editorial text-2xl mt-2">Select the episodes you want to sponsor</h3>
            <div className="mt-6 grid grid-cols-6 md:grid-cols-10 gap-2" data-testid="episode-grid">
              {Array.from({ length: p.total_episodes }, (_, i) => i + 1).map(n => {
                const isTaken = taken.has(n);
                const isSel = selected.has(n);
                return (
                  <button key={n} onClick={() => toggleEp(n)} disabled={isTaken}
                    data-testid={`ep-${n}`}
                    className={`h-10 text-xs font-mono-imh border ${isTaken ? "bg-[#F5F0E1] border-[#E4E4E1] text-[#A1A1AA] cursor-not-allowed line-through" : isSel ? "bg-[#0033A0] text-white border-[#0033A0]" : "bg-white border-[#E4E4E1] hover:border-[#0A0A0A]"}`}
                    style={{ transition: "background 120ms" }}>
                    {String(n).padStart(3, "0")}
                  </button>
                );
              })}
            </div>
            <div className="mt-3 flex gap-4 text-[11px] text-[#52525B]">
              <span><span className="inline-block w-3 h-3 border border-[#E4E4E1] bg-white align-middle mr-1"></span>Available</span>
              <span><span className="inline-block w-3 h-3 bg-[#0033A0] align-middle mr-1"></span>Your selection</span>
              <span><span className="inline-block w-3 h-3 bg-[#F5F0E1] align-middle mr-1"></span>Already sponsored</span>
            </div>
          </section>
        </article>

        <aside className="lg:col-span-4">
          <div className="imh-card p-6 sticky top-6" data-testid="sponsorship-checkout">
            <div className="imh-eyebrow">Sponsorship checkout</div>
            <h3 className="font-editorial text-2xl mt-2">Confirm your commitment</h3>

            <div className="mt-6 space-y-4">
              <F label="Your client name"><Input data-testid="sp-client" value={clientName} onChange={e => setClientName(e.target.value)} /></F>
              <F label="Client total price (USD)"><Input data-testid="sp-price" type="number" value={clientPrice} onChange={e => setClientPrice(e.target.value)} /></F>
            </div>

            <dl className="mt-6 divide-y divide-[#E4E4E1]">
              <Row label="Episodes selected" value={<span className="font-mono-imh">{selected.size}</span>} />
              <Row label="Internal cost" value={<span className="font-mono-imh">{usd(internal)}</span>} />
              <Row label="Client price" value={<span className="font-mono-imh">{usd(priceNum)}</span>} />
              <Row label="Your margin" value={<span className="font-mono-imh" style={{ color: margin >= 0 ? "#166534" : "#991B1B" }}>{usd(margin)}</span>} />
            </dl>
            <Button onClick={submit} disabled={busy} data-testid="sp-submit" className="mt-6 w-full h-11 rounded-none bg-[#0033A0] hover:bg-[#002277] text-white">
              {busy ? "Confirming…" : "Confirm sponsorship"}
            </Button>
            <p className="mt-3 text-[11px] text-[#52525B]">Internal cost is your platform cost. Your client will only see the client price you set.</p>
          </div>
        </aside>
      </div>

      {showVideo && p.demo_video_url && (
        <div className="fixed inset-0 z-50 bg-black/90 flex items-center justify-center p-6" onClick={() => setShowVideo(false)}>
          <div className="w-full max-w-5xl" onClick={e => e.stopPropagation()}>
            <video src={p.demo_video_url} controls autoPlay className="w-full h-auto" />
          </div>
        </div>
      )}
    </div>
  );
}

const F = ({ label, children }) => <div><Label className="text-[11px] uppercase tracking-widest text-[#52525B]">{label}</Label><div className="mt-2">{children}</div></div>;
const Row = ({ label, value }) => <div className="flex items-center justify-between py-2.5 text-sm"><span className="text-[#52525B]">{label}</span><span>{value}</span></div>;
const Facts = ({ label, value }) => (
  <div>
    <div className="imh-eyebrow">{label}</div>
    <div className="mt-2 text-[16px] font-editorial">{value}</div>
  </div>
);
