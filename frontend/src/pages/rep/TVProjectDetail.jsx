import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import api, { formatApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from "@/components/ui/dialog";
import { toast } from "sonner";
import { ChevronLeft, PlayCircle, Download, Send, Layers, Users, Clapperboard, Palette, Sparkles, Trophy } from "lucide-react";

const SECTION_META = [
  { key: "overview",     icon: Layers,       eyebrow: "01 · Overview",     title: "Concept & purpose" },
  { key: "audience",     icon: Users,        eyebrow: "02 · Audience",     title: "Target audience" },
  { key: "format",       icon: Clapperboard, eyebrow: "03 · Format",       title: "Production format" },
  { key: "sponsorship",  icon: Trophy,       eyebrow: "04 · Sponsorship",  title: "Sponsorship opportunities" },
  { key: "specs",        icon: Sparkles,     eyebrow: "05 · Standards",    title: "Technical specifications" },
  { key: "brand",        icon: Palette,      eyebrow: "06 · Brand",        title: "Brand guidelines" },
  { key: "downloads",    icon: Download,     eyebrow: "07 · Assets",       title: "Download center" },
];

const DEFAULT_SPONSORSHIP = ["Title Sponsor", "Episode Sponsor", "Product Placement", "Local Brand Activation"];
const DEFAULT_DOWNLOADS = [
  { label: "Editable Sponsor Presentation (Word)", filetype: "docx" },
  { label: "Production Bible (PDF)",               filetype: "pdf"  },
  { label: "Brand Guidelines (PDF)",               filetype: "pdf"  },
  { label: "Graphics Package (ZIP)",               filetype: "zip"  },
  { label: "Intro & Outro (MP4)",                  filetype: "mp4"  },
  { label: "Thumbnail Templates (PSD)",            filetype: "psd"  },
  { label: "Submission Checklist (PDF)",           filetype: "pdf"  },
];

export default function TVProjectDetail() {
  const { id } = useParams();
  const [p, setP] = useState(null);
  const [showVideo, setShowVideo] = useState(false);
  const [applyOpen, setApplyOpen] = useState(false);
  const [applied, setApplied] = useState(false);

  useEffect(() => { api.get(`/tv-projects/${id}`).then(r => setP(r.data)); }, [id]);
  useEffect(() => {
    api.get("/my-productions")
       .then(r => setApplied(r.data.some(a => a.tv_project_id === id)))
       .catch(() => {});
  }, [id]);

  if (!p) return <div className="p-10 imh-eyebrow" data-testid="project-loading">Loading…</div>;

  const specs = p.technical_specs || {};
  const brand = p.brand_guidelines || {};
  const opportunities = (p.sponsorship_opportunities?.length ? p.sponsorship_opportunities : DEFAULT_SPONSORSHIP);
  const downloads = (p.download_assets?.length ? p.download_assets : DEFAULT_DOWNLOADS);
  const languages = (p.languages || []).join(" · ");

  return (
    <div>
      {/* Hero */}
      <div className="relative bg-[#0A1128] text-white" data-testid="project-hero">
        <div className="absolute inset-0 opacity-40" style={{
          backgroundImage: p.hero_image_url ? `url(${p.hero_image_url})` : "linear-gradient(135deg, #0A1128, #1E293B)",
          backgroundSize: "cover", backgroundPosition: "center",
        }} />
        <div className="relative px-10 py-16">
          <Link to="/rep/tv" className="text-[11px] uppercase tracking-widest text-[#B8C1DA] inline-flex items-center gap-1 hover:text-white" data-testid="hero-back">
            <ChevronLeft size={12} /> Project Library
          </Link>
          <div className="mt-8 flex items-center gap-3 flex-wrap text-[11px] font-mono-imh">
            <Chip color="#B45309">{(p.category || "tv_formats").replace("_", " ")}</Chip>
            <Chip color="#166534">{p.status}</Chip>
            {p.duration_minutes && <Chip color="#0033A0">{p.duration_minutes} min</Chip>}
            {p.difficulty && <Chip color="#52525B">{p.difficulty}</Chip>}
          </div>
          <h1 className="font-editorial text-5xl xl:text-6xl mt-4 max-w-4xl">{p.title}</h1>
          {p.tagline && <div className="mt-3 text-lg italic text-[#C9D1E4] max-w-3xl">{p.tagline}</div>}
          <div className="mt-8 flex items-center gap-3 flex-wrap">
            {p.demo_video_url && (
              <button onClick={() => setShowVideo(true)} data-testid="watch-trailer"
                      className="inline-flex items-center gap-2 h-11 px-5 bg-white text-[#0A1128] text-[12px] uppercase tracking-widest hover:bg-[#F9F9F6]"
                      style={{ transition: "background 120ms" }}>
                <PlayCircle size={16} /> Watch trailer
              </button>
            )}
            {applied ? (
              <span className="inline-flex items-center gap-2 h-11 px-5 bg-[#166534] text-white text-[12px] uppercase tracking-widest" data-testid="applied-badge">
                <Send size={14} /> Application submitted
              </span>
            ) : (
              <Button onClick={() => setApplyOpen(true)} data-testid="apply-btn"
                      className="rounded-none h-11 px-5 bg-[#0033A0] hover:bg-[#002277] text-white">
                <Send size={14} className="mr-2" /> Apply to produce
              </Button>
            )}
          </div>
        </div>
      </div>

      <div className="px-10 py-14 space-y-14 max-w-6xl">
        {/* Overview */}
        <Section {...SECTION_META[0]}>
          {p.concept && <Para>{p.concept}</Para>}
          {p.synopsis && <Para muted>{p.synopsis}</Para>}
          {p.purpose && <Blockquote label="Why this project exists">{p.purpose}</Blockquote>}
        </Section>

        {/* Audience */}
        <Section {...SECTION_META[1]}>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Facet label="Demographics" value={p.audience_demographics || p.target_audience || "—"} />
            <Facet label="Interests" value={p.audience_interests || "—"} />
          </div>
        </Section>

        {/* Format */}
        <Section {...SECTION_META[2]}>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-6">
            <Facet label="Season length"   value={p.total_episodes ? `${p.total_episodes} episodes` : "—"} />
            <Facet label="Running time"    value={p.duration_minutes ? `${p.duration_minutes} minutes` : "—"} />
            <Facet label="Distribution"    value={p.distribution || "Independent TV network"} />
            <Facet label="Languages"       value={languages || "—"} />
          </div>
          {p.production_format && <Para muted>{p.production_format}</Para>}
        </Section>

        {/* Sponsorship — informational only */}
        <Section {...SECTION_META[3]}>
          <Para muted>
            Country Partners negotiate sponsorship independently in their own market. The suggestions below are informational and reflect
            common sponsorship tiers used across the Independent Media Network. <b>No pricing is provided.</b>
          </Para>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mt-4" data-testid="sponsorship-opportunities">
            {opportunities.map((o, i) => (
              <div key={i} className="imh-card p-4">
                <div className="imh-eyebrow" style={{ color: "#B45309" }}>Tier · {i + 1}</div>
                <div className="mt-2 font-editorial text-lg">{o}</div>
              </div>
            ))}
          </div>
        </Section>

        {/* Technical specs */}
        <Section {...SECTION_META[4]}>
          <div className="grid grid-cols-2 lg:grid-cols-3 gap-6" data-testid="tech-specs">
            <Facet label="Cameras"       value={specs.cameras       || "Broadcast-grade cinema cameras"} />
            <Facet label="Resolution"    value={specs.resolution    || "3840×2160 UHD · minimum 1920×1080 HD"} />
            <Facet label="Frame rate"    value={specs.frame_rate    || "25 fps (PAL) or 29.97 fps (NTSC)"} />
            <Facet label="Audio"         value={specs.audio         || "48 kHz · 24-bit · stereo master"} />
            <Facet label="Graphics"      value={specs.graphics      || "Provided graphics package · lower thirds included"} />
            <Facet label="Delivery"      value={specs.delivery      || "ProRes 422 HQ · MP4 H.264 web master"} />
            <Facet label="Subtitles"     value={specs.subtitles     || "SRT · burned-in localized track"} />
            <Facet label="Thumbnails"    value={specs.thumbnails    || "16:9 · 1920×1080 · JPG/PNG"} />
          </div>
        </Section>

        {/* Brand guidelines */}
        <Section {...SECTION_META[5]}>
          <div className="grid grid-cols-2 lg:grid-cols-3 gap-6" data-testid="brand-guidelines">
            <Facet label="Logo usage"        value={brand.logo         || "Independent Projects wordmark · clear space enforced"} />
            <Facet label="Intro sequence"    value={brand.intro        || "5-second animated logo sting"} />
            <Facet label="Outro sequence"    value={brand.outro        || "10-second credits + IP wordmark"} />
            <Facet label="Music"             value={brand.music        || "Signature score · provided cue package"} />
            <Facet label="Fonts"             value={brand.fonts        || "Playfair Display · IBM Plex Sans · IBM Plex Mono"} />
            <Facet label="Motion graphics"   value={brand.motion       || "Provided After Effects package"} />
          </div>
          <Para muted>Productions from different countries must feel like they belong to one international brand.</Para>
        </Section>

        {/* Downloads */}
        <Section {...SECTION_META[6]}>
          <Para muted>
            Every download is designed for Country Partners to customize locally. The Sponsor Presentation is editable — add your own
            logo, contact details and local sponsorship information before presenting it to potential sponsors.
          </Para>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 mt-4" data-testid="downloads-list">
            {downloads.map((d, i) => (
              <a key={i} href={d.url || "#"} download data-testid={`download-${i}`}
                 onClick={e => { if (!d.url) { e.preventDefault(); toast.info("This asset will be available once the project is officially published."); } }}
                 className="flex items-center justify-between p-4 border border-[#E4E4E1] hover:border-[#0033A0] hover:bg-[#F9F9F6]"
                 style={{ transition: "background 120ms, border-color 120ms" }}>
                <div>
                  <div className="font-editorial text-base">{d.label}</div>
                  {d.filetype && <div className="text-[10px] font-mono-imh uppercase tracking-widest text-[#52525B] mt-1">{d.filetype}</div>}
                </div>
                <Download size={16} className="text-[#0033A0]" />
              </a>
            ))}
          </div>
        </Section>
      </div>

      <ApplyDialog open={applyOpen} onOpenChange={setApplyOpen} project={p} onDone={() => setApplied(true)} />

      {showVideo && p.demo_video_url && (
        <div className="fixed inset-0 z-50 bg-black/85 flex items-center justify-center p-6" onClick={() => setShowVideo(false)} data-testid="video-overlay">
          <div className="w-full max-w-4xl aspect-video bg-black" onClick={e => e.stopPropagation()}>
            <iframe src={p.demo_video_url} title="Trailer" className="w-full h-full" allowFullScreen frameBorder="0" />
          </div>
        </div>
      )}
    </div>
  );
}

function ApplyDialog({ open, onOpenChange, project, onDone }) {
  const [message, setMessage] = useState("");
  const [target, setTarget] = useState("");
  const [busy, setBusy] = useState(false);
  const submit = async () => {
    setBusy(true);
    try {
      await api.post(`/tv-projects/${project.id}/apply`, { tv_project_id: project.id, message, target_launch_date: target });
      onOpenChange(false);
      setTimeout(() => { toast.success("Your application to produce has been submitted."); onDone && onDone(); }, 0);
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
    finally { setBusy(false); }
  };
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="rounded-none border border-[#0A0A0A] max-w-lg" data-testid="apply-dialog">
        <DialogHeader>
          <DialogTitle className="font-editorial text-2xl">Apply to produce · {project.title}</DialogTitle>
          <DialogDescription className="text-xs text-[#52525B]">
            Register your intention to produce this project in your territory. The Independent Media Network team will review your application and reach out to co-ordinate next steps.
          </DialogDescription>
        </DialogHeader>
        <div className="grid grid-cols-1 gap-3 mt-2">
          <div>
            <Label className="imh-eyebrow">Message to the network</Label>
            <Textarea rows={4} className="rounded-none mt-2" value={message} onChange={e => setMessage(e.target.value)} data-testid="apply-message"
                       placeholder="Share your local production plan, preferred timing, and any sponsors already in conversation." />
          </div>
          <div>
            <Label className="imh-eyebrow">Target launch date (optional)</Label>
            <Input type="date" className="rounded-none mt-2" value={target} onChange={e => setTarget(e.target.value)} data-testid="apply-target" />
          </div>
        </div>
        <DialogFooter className="mt-4">
          <Button onClick={submit} disabled={busy} data-testid="apply-submit" className="rounded-none bg-[#0033A0] hover:bg-[#002277]">
            {busy ? "Submitting…" : "Submit application"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

const Chip = ({ children, color }) => (
  <span className="inline-block px-2 py-1 uppercase tracking-widest text-[10px]" style={{ background: color, color: "#fff" }}>{children}</span>
);
const Section = ({ icon: Icon, eyebrow, title, children }) => (
  <section>
    <div className="imh-eyebrow flex items-center gap-2"><Icon size={11} strokeWidth={1.6} /> {eyebrow}</div>
    <h2 className="font-editorial text-3xl mt-2 mb-6">{title}</h2>
    {children}
  </section>
);
const Para = ({ children, muted }) => <p className={`text-[15px] leading-relaxed max-w-3xl ${muted ? "text-[#52525B]" : "text-[#0A0A0A]"}`}>{children}</p>;
const Facet = ({ label, value }) => (
  <div>
    <div className="text-[10px] uppercase tracking-widest text-[#52525B]">{label}</div>
    <div className="mt-2 text-[15px] text-[#0A0A0A]">{value}</div>
  </div>
);
const Blockquote = ({ children, label }) => (
  <blockquote className="mt-6 border-l-2 border-[#0033A0] bg-[#F9F9F6] p-5 max-w-3xl">
    <div className="imh-eyebrow" style={{ color: "#0033A0" }}>{label}</div>
    <div className="mt-2 text-[15px] italic text-[#0A0A0A]">{children}</div>
  </blockquote>
);
