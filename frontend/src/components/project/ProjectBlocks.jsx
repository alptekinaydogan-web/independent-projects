/**
 * Modular Project Template — reusable content blocks for the Project Library.
 *
 * Every project page is composed of small building blocks that can be reused
 * or omitted per category. TV Formats today, but Events / Podcasts /
 * Documentaries / Research Projects / Co-Productions will reuse the same
 * blocks without any structural change:
 *
 *   <ProjectHero />
 *   <ProjectOverview />
 *   <ProjectAudience />
 *   <ProjectFormat />
 *   <ProjectSponsorship />
 *   <ProjectTechnicalSpecs />
 *   <ProjectBrandGuidelines />
 *   <ProjectDownloadCenter />
 *   <ProjectApplyToProduce />
 *
 * Any block can be safely removed or reordered — the page adapts.
 */
import { Link } from "react-router-dom";
import { ChevronLeft, PlayCircle, Download, Send, Layers, Users, Clapperboard, Palette, Sparkles, Trophy } from "lucide-react";
import { toast } from "sonner";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from "@/components/ui/dialog";
import api, { formatApiError } from "@/lib/api";

// ---------- Layout primitives ----------
export const Chip = ({ children, color }) => (
  <span className="inline-block px-2 py-1 uppercase tracking-widest text-[10px]" style={{ background: color, color: "#fff" }}>
    {children}
  </span>
);

export const Section = ({ icon: Icon, eyebrow, title, children, testId }) => (
  <section data-testid={testId}>
    <div className="imh-eyebrow flex items-center gap-2"><Icon size={11} strokeWidth={1.6} /> {eyebrow}</div>
    <h2 className="font-editorial text-3xl mt-2 mb-6">{title}</h2>
    {children}
  </section>
);

export const Para = ({ children, muted }) => (
  <p className={`text-[15px] leading-relaxed max-w-3xl ${muted ? "text-[#52525B]" : "text-[#0A0A0A]"}`}>{children}</p>
);

export const Facet = ({ label, value }) => (
  <div>
    <div className="text-[10px] uppercase tracking-widest text-[#52525B]">{label}</div>
    <div className="mt-2 text-[15px] text-[#0A0A0A]">{value}</div>
  </div>
);

export const Blockquote = ({ children, label }) => (
  <blockquote className="mt-6 border-l-2 border-[#0033A0] bg-[#F9F9F6] p-5 max-w-3xl">
    <div className="imh-eyebrow" style={{ color: "#0033A0" }}>{label}</div>
    <div className="mt-2 text-[15px] italic text-[#0A0A0A]">{children}</div>
  </blockquote>
);

// ---------- Blocks ----------

export function ProjectHero({ project, category, applicationStatus, onApplyClick, backTo = "/rep/tv", backLabel = "Project Library" }) {
  const [showVideo, setShowVideo] = useState(false);
  const badge = APPLICATION_BADGE[applicationStatus];
  return (
    <div className="relative bg-[#0A1128] text-white" data-testid="project-hero">
      <div className="absolute inset-0 opacity-40" style={{
        backgroundImage: project.hero_image_url ? `url(${project.hero_image_url})` : "linear-gradient(135deg, #0A1128, #1E293B)",
        backgroundSize: "cover", backgroundPosition: "center",
      }} />
      <div className="relative px-10 py-16">
        <Link to={backTo} className="text-[11px] uppercase tracking-widest text-[#B8C1DA] inline-flex items-center gap-1 hover:text-white" data-testid="hero-back">
          <ChevronLeft size={12} /> {backLabel}
        </Link>
        <div className="mt-8 flex items-center gap-3 flex-wrap text-[11px] font-mono-imh">
          <Chip color="#B45309">{category?.name || (project.category_slug || project.category || "tv_formats").replace(/_/g, " ")}</Chip>
          <Chip color="#166534">{project.status}</Chip>
          {project.duration_minutes && <Chip color="#0033A0">{project.duration_minutes} min</Chip>}
          {project.difficulty && <Chip color="#52525B">{project.difficulty}</Chip>}
        </div>
        <h1 className="font-editorial text-5xl xl:text-6xl mt-4 max-w-4xl">{project.title}</h1>
        {project.tagline && <div className="mt-3 text-lg italic text-[#C9D1E4] max-w-3xl">{project.tagline}</div>}
        <div className="mt-8 flex items-center gap-3 flex-wrap">
          {project.demo_video_url && (
            <button onClick={() => setShowVideo(true)} data-testid="watch-trailer"
                    className="inline-flex items-center gap-2 h-11 px-5 bg-white text-[#0A1128] text-[12px] uppercase tracking-widest hover:bg-[#F9F9F6]"
                    style={{ transition: "background 120ms" }}>
              <PlayCircle size={16} /> Watch trailer
            </button>
          )}
          {badge ? (
            <span className="inline-flex items-center gap-2 h-11 px-5 text-white text-[12px] uppercase tracking-widest"
                  style={{ background: badge.color }}
                  data-testid={`application-badge-${applicationStatus}`}>
              <Send size={14} /> {badge.label}
            </span>
          ) : onApplyClick && (
            <Button onClick={onApplyClick} data-testid="apply-btn"
                    className="rounded-none h-11 px-5 bg-[#0033A0] hover:bg-[#002277] text-white">
              <Send size={14} className="mr-2" /> Apply to produce
            </Button>
          )}
        </div>
      </div>

      {showVideo && project.demo_video_url && (
        <div className="fixed inset-0 z-50 bg-black/85 flex items-center justify-center p-6"
             onClick={() => setShowVideo(false)} data-testid="video-overlay">
          <div className="w-full max-w-4xl aspect-video bg-black" onClick={e => e.stopPropagation()}>
            <iframe src={project.demo_video_url} title="Trailer" className="w-full h-full" allowFullScreen frameBorder="0" />
          </div>
        </div>
      )}
    </div>
  );
}

const APPLICATION_BADGE = {
  submitted:          { label: "Application submitted", color: "#B45309" },
  revision_requested: { label: "Revision requested",    color: "#0033A0" },
  approved:           { label: "Production approved",   color: "#166534" },
  rejected:           { label: "Application declined",  color: "#991B1B" },
};

export function ProjectOverview({ project }) {
  const kslPoints = project.key_selling_points || [];
  return (
    <Section icon={Layers} eyebrow="01 · Executive summary" title="Overview & purpose" testId="section-overview">
      {(project.overview || project.synopsis) && <Para>{project.overview || project.synopsis}</Para>}
      {project.purpose && <div className="mt-4"><Para muted>{project.purpose}</Para></div>}
      {project.why_exists && <Blockquote label="Why this project exists">{project.why_exists}</Blockquote>}
      {kslPoints.length > 0 && (
        <div className="mt-6" data-testid="key-selling-points">
          <div className="imh-eyebrow" style={{ color: "#B45309" }}>Key selling points</div>
          <ul className="mt-3 space-y-2 text-[15px] max-w-3xl list-disc pl-5">
            {kslPoints.map((k, i) => <li key={i}>{k}</li>)}
          </ul>
        </div>
      )}
    </Section>
  );
}

export function ProjectConcept({ project }) {
  if (!project.concept && !project.narrative && !project.episode_structure && !project.tone) return null;
  return (
    <Section icon={Layers} eyebrow="02 · Story & concept" title="Concept, narrative, tone" testId="section-concept">
      {project.concept && <Para>{project.concept}</Para>}
      <div className="mt-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
        {project.narrative && <Facet label="Narrative" value={project.narrative} />}
        {project.episode_structure && <Facet label="Episode structure" value={project.episode_structure} />}
        {project.tone && <Facet label="Tone" value={project.tone} />}
      </div>
    </Section>
  );
}

export function ProjectObjectives({ project }) {
  const items = [
    ["Entertainment", project.objective_entertainment],
    ["Education",     project.objective_education],
    ["Awareness",     project.objective_awareness],
    ["Commercial",    project.objective_commercial],
  ].filter(([, v]) => v);
  if (items.length === 0) return null;
  return (
    <Section icon={Trophy} eyebrow="03 · Objectives" title="What this project achieves" testId="section-objectives">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {items.map(([label, value]) => <Facet key={label} label={label} value={value} />)}
      </div>
    </Section>
  );
}

export function ProjectAudience({ project }) {
  return (
    <Section icon={Users} eyebrow="04 · Audience" title="Target audience" testId="section-audience">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Facet label="Demographics" value={project.audience_demographics || project.target_audience || "—"} />
        <Facet label="Interests" value={project.audience_interests || "—"} />
        {project.audience_geography && <Facet label="Geography" value={project.audience_geography} />}
        {project.audience_viewing_habits && <Facet label="Viewing habits" value={project.audience_viewing_habits} />}
      </div>
    </Section>
  );
}

export function ProjectFormat({ project }) {
  const languages = (project.languages || []).join(" · ");
  return (
    <Section icon={Clapperboard} eyebrow="05 · Format" title="Production format" testId="section-format">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-6">
        <Facet label="Season length" value={project.total_episodes ? `${project.total_episodes} episodes` : "—"} />
        <Facet label="Episode duration" value={project.episode_duration ? `${project.episode_duration} min` : "—"} />
        <Facet label="Distribution"  value={project.distribution || "Independent TV network"} />
        <Facet label="Languages"     value={languages || "—"} />
      </div>
      {(project.production_workflow || project.required_crew || project.locations || project.equipment) && (
        <div className="mt-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
          {project.production_workflow && <Facet label="Production workflow" value={project.production_workflow} />}
          {project.required_crew       && <Facet label="Required crew"       value={project.required_crew} />}
          {project.locations           && <Facet label="Locations"           value={project.locations} />}
          {project.equipment           && <Facet label="Equipment"           value={project.equipment} />}
        </div>
      )}
      {project.production_format && <Para muted>{project.production_format}</Para>}
    </Section>
  );
}

const DEFAULT_SPONSORSHIP = ["Title Sponsor", "Episode Sponsor", "Product Placement", "Local Brand Activation"];

export function ProjectSponsorship({ project }) {
  const opportunities = (project.sponsorship_opportunities?.length ? project.sponsorship_opportunities : DEFAULT_SPONSORSHIP);
  return (
    <Section icon={Trophy} eyebrow="06 · Sponsorship" title="Sponsorship opportunities" testId="section-sponsorship">
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
      {project.sponsorship_rights && <div className="mt-4"><Para muted>{project.sponsorship_rights}</Para></div>}
    </Section>
  );
}

export function ProjectTechnicalSpecs({ project }) {
  const specs = project.technical_specs || {};
  return (
    <Section icon={Sparkles} eyebrow="07 · Standards" title="Technical specifications" testId="section-tech-specs">
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
  );
}

export function ProjectBrandGuidelines({ project }) {
  const brand = project.brand_guidelines || {};
  return (
    <Section icon={Palette} eyebrow="08 · Brand" title="Brand guidelines" testId="section-brand">
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-6" data-testid="brand-guidelines">
        <Facet label="Logo usage"      value={brand.logo   || "Independent Projects wordmark · clear space enforced"} />
        <Facet label="Intro sequence"  value={brand.intro  || "5-second animated logo sting"} />
        <Facet label="Outro sequence"  value={brand.outro  || "10-second credits + IP wordmark"} />
        <Facet label="Music"           value={brand.music  || "Signature score · provided cue package"} />
        <Facet label="Typography"      value={brand.fonts  || "Playfair Display · IBM Plex Sans · IBM Plex Mono"} />
        <Facet label="Motion graphics" value={brand.motion || "Provided After Effects package"} />
        {brand.colors && <Facet label="Color palette" value={brand.colors} />}
      </div>
      <Para muted>Productions from different countries must feel like they belong to one international brand.</Para>
    </Section>
  );
}

const DEFAULT_DOWNLOADS = [
  { label: "Editable Sponsor Presentation (Word)", filetype: "docx" },
  { label: "Production Bible (PDF)",               filetype: "pdf"  },
  { label: "Brand Guidelines (PDF)",               filetype: "pdf"  },
  { label: "Graphics Package (ZIP)",               filetype: "zip"  },
  { label: "Intro & Outro (MP4)",                  filetype: "mp4"  },
  { label: "Thumbnail Templates (PSD)",            filetype: "psd"  },
  { label: "Submission Checklist (PDF)",           filetype: "pdf"  },
];

export function ProjectDownloadCenter({ project }) {
  const downloads = (project.download_assets?.length ? project.download_assets : DEFAULT_DOWNLOADS);
  return (
    <Section icon={Download} eyebrow="09 · Assets" title="Download center" testId="section-downloads">
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
  );
}

export function ProjectApplyToProduce({ open, onOpenChange, project, onSubmitted }) {
  const [message, setMessage] = useState("");
  const [target, setTarget] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    setBusy(true);
    try {
      await api.post(`/tv-projects/${project.id}/apply`, { tv_project_id: project.id, message, target_launch_date: target });
      onOpenChange(false);
      setTimeout(() => { toast.success("Your application to produce has been submitted."); onSubmitted && onSubmitted(); }, 0);
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
    finally { setBusy(false); }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="rounded-none border border-[#0A0A0A] max-w-lg" data-testid="apply-dialog">
        <DialogHeader>
          <DialogTitle className="font-editorial text-2xl">Apply to produce · {project?.title}</DialogTitle>
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
