/**
 * ProjectEditor — the ONE editor for both Admins and Country Partners.
 *
 * Every admin-created Official Project and every partner submission goes
 * through this exact editor. The only differences between the two
 * experiences are:
 *
 *   - Moderation controls (Approve / Reject / Revision / Publish /
 *     Feature / Archive) are rendered only when `mode` includes
 *     "moderation" and the current user is an admin.
 *   - Reps can only edit their own drafts / revision-requested projects
 *     (the caller decides that and passes `editable={true|false}`).
 *
 * The editor is a big, scrollable, section-based form using shadcn
 * Accordion for organization. All fields land in the unified TVProject
 * model on the backend.
 */
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import api, { formatApiError, API } from "@/lib/api";
import { toast } from "sonner";
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Accordion, AccordionItem, AccordionTrigger, AccordionContent } from "@/components/ui/accordion";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { AlertTriangle, Upload, ImageIcon, Video, Loader2, Plus, Trash2, Sparkles,
          Send, Check, X, Rewind, Eye, EyeOff, Archive, Star, StarOff, Save } from "lucide-react";

// ---- Defaults ----
const EMPTY = {
  title: "", subtitle: "", tagline: "",
  category_slug: "tv_formats",
  status: "draft",
  hero_image_url: "", demo_video_url: "",
  gallery: [],
  overview: "", purpose: "", why_exists: "",
  key_selling_points: [],
  concept: "", narrative: "", episode_structure: "", tone: "",
  objective_entertainment: "", objective_education: "",
  objective_awareness: "", objective_commercial: "",
  target_audience: "",
  audience_demographics: "", audience_interests: "",
  audience_geography: "", audience_viewing_habits: "",
  total_episodes: 0, episode_duration: 30,
  production_workflow: "", required_crew: "",
  locations: "", equipment: "",
  distribution: "", languages: [], production_format: "",
  sponsorship_opportunities: [],
  sponsorship_rights: "",
  technical_specs: {},
  brand_guidelines: {},
  download_assets: [],
};

const MODERATION_STYLE = {
  draft:              { color: "#52525B", label: "Draft" },
  submitted:          { color: "#B45309", label: "Submitted for review" },
  revision_requested: { color: "#0033A0", label: "Revision requested" },
  approved:           { color: "#166534", label: "Approved" },
  rejected:           { color: "#991B1B", label: "Rejected" },
};

// ---------- Helper primitives ----------
const F = ({ label, hint, children, full = true }) => (
  <div className={full ? "col-span-2" : "col-span-1"}>
    <Label className="text-[11px] uppercase tracking-widest text-[#52525B]">{label}</Label>
    <div className="mt-2">{children}</div>
    {hint && <div className="text-[11px] text-[#A1A1AA] mt-1">{hint}</div>}
  </div>
);

const Section = ({ value, title, subtitle, children, testId }) => (
  <AccordionItem value={value} data-testid={testId} className="border border-[#E4E4E1] bg-white mb-3">
    <AccordionTrigger className="px-5 py-3 hover:no-underline">
      <div className="flex-1 text-left">
        <div className="font-editorial text-lg">{title}</div>
        {subtitle && <div className="text-xs text-[#52525B] mt-1">{subtitle}</div>}
      </div>
    </AccordionTrigger>
    <AccordionContent className="px-5 pb-6 pt-2">
      <div className="grid grid-cols-2 gap-4">{children}</div>
    </AccordionContent>
  </AccordionItem>
);

// A simple string-list editor
function ListEditor({ items = [], onChange, placeholder = "Add item", testId }) {
  const [draft, setDraft] = useState("");
  const list = items || [];
  const add = () => {
    const v = draft.trim();
    if (!v) return;
    onChange([...list, v]);
    setDraft("");
  };
  return (
    <div data-testid={testId}>
      <div className="flex gap-2">
        <Input value={draft} onChange={e => setDraft(e.target.value)}
                onKeyDown={e => { if (e.key === "Enter") { e.preventDefault(); add(); } }}
                placeholder={placeholder} className="rounded-none" />
        <Button type="button" onClick={add} variant="outline" className="rounded-none border-[#E4E4E1]">
          <Plus size={14} />
        </Button>
      </div>
      {list.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-2">
          {list.map((v, i) => (
            <span key={`${v}-${i}`} className="inline-flex items-center gap-1 px-2 py-1 border border-[#E4E4E1] text-xs">
              {v}
              <button onClick={() => onChange(list.filter((_, j) => j !== i))} className="ml-1 text-[#52525B] hover:text-[#991B1B]">
                <X size={11} />
              </button>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

// A single-file uploader → returns a URL served via /api/files/{path}
function AssetUploader({ accept, kind, currentUrl, onUploaded, icon: Icon, testId }) {
  const [busy, setBusy] = useState(false);
  const handle = async e => {
    const f = e.target.files?.[0]; if (!f) return;
    const fd = new FormData();
    fd.append("file", f); fd.append("kind", kind);
    setBusy(true);
    try {
      const { data } = await api.post("/admin/upload", fd, { headers: { "Content-Type": "multipart/form-data" } });
      const url = `${API}/files/${data.storage_path}`;
      onUploaded(url, data);
      toast.success("Uploaded");
    } catch (err) { toast.error(formatApiError(err.response?.data?.detail) || "Upload failed"); }
    finally { setBusy(false); }
  };
  return (
    <label className="inline-flex items-center gap-2 h-10 px-3 border border-[#D4D4D0] cursor-pointer hover:bg-[#F9F9F6] text-xs text-[#52525B]" data-testid={testId}>
      {busy ? <Loader2 size={13} className="animate-spin" /> : <Icon size={13} />}
      {currentUrl ? "Replace file" : "Choose file"}
      <input type="file" accept={accept} className="hidden" onChange={handle} />
    </label>
  );
}

// ---------- Main editor ----------
export default function ProjectEditor({ projectId, mode, onSaved }) {
  // mode: "create-admin" | "create-partner" | "edit"
  const { user } = useAuth();
  const isAdmin = user?.role === "admin" || user?.role === "owner";
  const nav = useNavigate();
  const [project, setProject] = useState(null);   // remote copy
  const [form, setForm] = useState(EMPTY);
  const [saving, setSaving] = useState(false);
  const [asset, setAsset] = useState({ label: "", url: "", filetype: "", storage_path: "", original_filename: "" });
  const [moderateOpen, setModerateOpen] = useState(false);
  const [moderateDecision, setModerateDecision] = useState("approved");
  const [moderateFeedback, setModerateFeedback] = useState("");
  const [moderateInternal, setModerateInternal] = useState("");

  const editable = useMemo(() => {
    if (!project) return true;
    if (isAdmin) return true;
    return project.submitted_by_rep_id === user?.id
        && (project.moderation_status === "draft" || project.moderation_status === "revision_requested");
  }, [project, isAdmin, user]);

  const load = () => {
    if (!projectId) return;
    api.get(`/tv-projects/${projectId}`).then(r => {
      setProject(r.data);
      setForm({ ...EMPTY, ...r.data,
        languages: r.data.languages || [],
        key_selling_points: r.data.key_selling_points || [],
        sponsorship_opportunities: r.data.sponsorship_opportunities || [],
        gallery: r.data.gallery || [],
        technical_specs: r.data.technical_specs || {},
        brand_guidelines: r.data.brand_guidelines || {},
        download_assets: r.data.download_assets || [],
      });
    });
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [projectId]);

  const set = (patch) => setForm(f => ({ ...f, ...patch }));
  const setNested = (key, subKey, value) => setForm(f => ({ ...f, [key]: { ...(f[key] || {}), [subKey]: value } }));

  const buildPayload = () => {
    const p = { ...form };
    p.total_episodes = Number(p.total_episodes) || 0;
    p.episode_duration = Number(p.episode_duration) || 0;
    if (typeof p.languages === "string") p.languages = p.languages.split(",").map(s => s.trim()).filter(Boolean);
    // Strip read-only fields
    ["id","_id","source","moderation_status","published","featured","archived","admin_feedback",
     "internal_notes","revision_history","submitted_at","decided_at","created_at","updated_at",
     "my_application","my_application_status","pending_applications_count","approved_applications_count",
     "submitted_by_rep_id","submitted_by_rep_name","submitted_by_agency","submitted_by_country",
    ].forEach(k => delete p[k]);
    return p;
  };

  const save = async () => {
    setSaving(true);
    try {
      if (!projectId) {
        const { data } = await api.post("/projects", buildPayload());
        toast.success(isAdmin ? "Project created" : "Draft saved");
        onSaved && onSaved(data);
        if (data?.id) nav(isAdmin ? `/admin/tv-projects/${data.id}` : `/rep/projects/${data.id}`);
      } else {
        const { data } = await api.patch(`/projects/${projectId}`, buildPayload());
        toast.success("Saved");
        setProject(data);
        onSaved && onSaved(data);
      }
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
    finally { setSaving(false); }
  };

  const submitForReview = async () => {
    if (!projectId) { toast.error("Save your draft first."); return; }
    try {
      await api.post(`/projects/${projectId}/submit`);
      toast.success("Submitted for administrator review.");
      load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };

  const moderate = async () => {
    try {
      await api.patch(`/admin/projects/${projectId}/moderate`, {
        decision: moderateDecision,
        admin_feedback: moderateFeedback,
        internal_notes: moderateInternal,
      });
      setModerateOpen(false);
      toast.success(`Marked ${moderateDecision.replace("_", " ")}`);
      load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };

  const togglePublish = async () => {
    try {
      await api.patch(`/admin/projects/${projectId}/publish`, { published: !project.published });
      toast.success(project.published ? "Unpublished" : "Published");
      load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };
  const toggleFeature = async () => {
    try {
      await api.patch(`/admin/projects/${projectId}/feature`, { featured: !project.featured });
      toast.success(project.featured ? "Removed from featured" : "Featured");
      load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };
  const toggleArchive = async () => {
    if (!project.archived && !window.confirm("Archive this project? It will be hidden from the Library.")) return;
    try {
      await api.patch(`/admin/projects/${projectId}/archive`, { archived: !project.archived });
      toast.success(project.archived ? "Unarchived" : "Archived");
      load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };

  const addAsset = async () => {
    if (!asset.label || !asset.url) { toast.error("Label and URL are required."); return; }
    try {
      await api.post(`/projects/${projectId}/assets`, asset);
      toast.success("Asset added");
      setAsset({ label: "", url: "", filetype: "", storage_path: "", original_filename: "" });
      load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };
  const removeAsset = async (assetId) => {
    if (!window.confirm("Remove this asset from the Download Center?")) return;
    try {
      await api.delete(`/projects/${projectId}/assets/${assetId}`);
      toast.success("Asset removed");
      load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };

  const modStyle = MODERATION_STYLE[project?.moderation_status] || MODERATION_STYLE.draft;
  const canSubmit = !isAdmin && project && (project.moderation_status === "draft" || project.moderation_status === "revision_requested");

  return (
    <div className="px-10 py-8">
      {/* --- Metadata strip --- */}
      {project && (
        <div className="mb-6 flex flex-wrap items-center gap-3" data-testid="editor-meta-strip">
          <span className="text-[10px] uppercase tracking-widest font-mono-imh px-2 py-1"
                 style={{ background: modStyle.color, color: "#fff" }}>
            {modStyle.label}
          </span>
          <span className="text-[10px] uppercase tracking-widest text-[#52525B]">
            Source · {project.source === "partner" ? "Country partner" : "Official"}
          </span>
          {project.source === "partner" && (
            <span className="text-[10px] uppercase tracking-widest text-[#52525B]">
              By {project.submitted_by_agency || project.submitted_by_rep_name} · {project.submitted_by_country}
            </span>
          )}
          <span className={`text-[10px] uppercase tracking-widest font-mono-imh px-2 py-1 border ${project.published ? "border-[#166534] text-[#166534]" : "border-[#E4E4E1] text-[#52525B]"}`}>
            {project.published ? "Published" : "Unpublished"}
          </span>
          {project.featured && <span className="text-[10px] uppercase tracking-widest text-[#B45309]">★ Featured</span>}
          {project.archived && <span className="text-[10px] uppercase tracking-widest text-[#991B1B]">Archived</span>}
        </div>
      )}

      {/* --- Admin moderation strip (only for partner submissions in review) --- */}
      {isAdmin && project?.source === "partner" && (
        <div className="imh-card p-4 mb-6 bg-[#FFFAF3] border-[#B45309]" data-testid="moderation-strip">
          <div className="flex items-center gap-3 flex-wrap">
            <AlertTriangle size={14} className="text-[#B45309]" />
            <div className="flex-1 min-w-[240px]">
              <div className="imh-eyebrow" style={{ color: "#B45309" }}>Partner submission review</div>
              <div className="text-sm mt-1">
                Read every section carefully before making a decision. Approving this project will publish it in the global Library.
              </div>
              {project.admin_feedback && (
                <div className="mt-2 text-xs text-[#52525B]">Previous feedback: <span className="italic">"{project.admin_feedback}"</span></div>
              )}
            </div>
            <div className="flex gap-2">
              <Button size="sm" onClick={() => { setModerateDecision("approved"); setModerateOpen(true); }}
                       data-testid="moderate-approve"
                       className="rounded-none bg-[#166534] hover:bg-[#0f4a25]">
                <Check size={13} className="mr-1" /> Approve
              </Button>
              <Button size="sm" onClick={() => { setModerateDecision("revision_requested"); setModerateOpen(true); }}
                       data-testid="moderate-revise"
                       className="rounded-none bg-[#0033A0] hover:bg-[#002277]">
                <Rewind size={13} className="mr-1" /> Request revision
              </Button>
              <Button size="sm" onClick={() => { setModerateDecision("rejected"); setModerateOpen(true); }}
                       data-testid="moderate-reject"
                       variant="outline" className="rounded-none border-[#991B1B] text-[#991B1B]">
                <X size={13} className="mr-1" /> Reject
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* --- Rep feedback strip --- */}
      {!isAdmin && project?.moderation_status === "revision_requested" && project?.admin_feedback && (
        <div className="imh-card p-4 mb-6 border-[#0033A0]" data-testid="revision-feedback">
          <div className="imh-eyebrow" style={{ color: "#0033A0" }}>Feedback from the network</div>
          <div className="text-sm mt-2 italic">"{project.admin_feedback}"</div>
        </div>
      )}

      {/* --- Top actions --- */}
      <div className="flex items-center justify-between mb-4">
        <div className="imh-eyebrow">
          {projectId ? "Editing project" : (isAdmin ? "New official project" : "New project submission")}
        </div>
        <div className="flex gap-2">
          {editable && (
            <Button onClick={save} disabled={saving} data-testid="editor-save"
                     className="rounded-none bg-[#0033A0] hover:bg-[#002277]">
              {saving ? <Loader2 size={14} className="animate-spin mr-2" /> : <Save size={14} className="mr-2" />}
              {projectId ? "Save changes" : (isAdmin ? "Create project" : "Save draft")}
            </Button>
          )}
          {canSubmit && (
            <Button onClick={submitForReview} data-testid="editor-submit"
                     variant="outline" className="rounded-none border-[#0033A0] text-[#0033A0]">
              <Send size={14} className="mr-2" /> Submit for review
            </Button>
          )}
          {isAdmin && project && (
            <>
              <Button size="sm" onClick={togglePublish} data-testid="editor-publish" variant="outline" className="rounded-none">
                {project.published ? <><EyeOff size={13} className="mr-1" /> Unpublish</> : <><Eye size={13} className="mr-1" /> Publish</>}
              </Button>
              <Button size="sm" onClick={toggleFeature} data-testid="editor-feature" variant="outline" className="rounded-none">
                {project.featured ? <><StarOff size={13} className="mr-1" /> Unfeature</> : <><Star size={13} className="mr-1" /> Feature</>}
              </Button>
              <Button size="sm" onClick={toggleArchive} data-testid="editor-archive" variant="outline" className="rounded-none">
                <Archive size={13} className="mr-1" /> {project.archived ? "Unarchive" : "Archive"}
              </Button>
            </>
          )}
        </div>
      </div>

      {/* --- Editor form --- */}
      <fieldset disabled={!editable} className={editable ? "" : "opacity-70"}>
      <Accordion type="multiple" defaultValue={["basic", "summary"]} className="w-full">

        <Section value="basic" title="Basic information" subtitle="Title, subtitle, cover, category & status" testId="section-basic">
          <F label="Title" full><Input value={form.title} onChange={e => set({ title: e.target.value })} data-testid="field-title" /></F>
          <F label="Subtitle"><Input value={form.subtitle} onChange={e => set({ subtitle: e.target.value })} data-testid="field-subtitle" /></F>
          <F label="Tagline"><Input value={form.tagline} onChange={e => set({ tagline: e.target.value })} data-testid="field-tagline" /></F>
          <F label="Cover image (URL)">
            <div className="flex gap-2 items-center">
              <Input value={form.hero_image_url} onChange={e => set({ hero_image_url: e.target.value })} placeholder="https://…" data-testid="field-hero" />
              {isAdmin && <AssetUploader accept="image/*" kind="image" icon={ImageIcon} currentUrl={form.hero_image_url}
                                          onUploaded={url => set({ hero_image_url: url })} testId="upload-hero" />}
            </div>
            {form.hero_image_url && <img src={form.hero_image_url} alt="" className="mt-2 h-24 object-cover" />}
          </F>
          <F label="Cover video (URL)">
            <div className="flex gap-2 items-center">
              <Input value={form.demo_video_url} onChange={e => set({ demo_video_url: e.target.value })} placeholder="https://…" data-testid="field-video" />
              {isAdmin && <AssetUploader accept="video/*" kind="video" icon={Video} currentUrl={form.demo_video_url}
                                          onUploaded={url => set({ demo_video_url: url })} testId="upload-video" />}
            </div>
          </F>
          <F label="Gallery (image URLs)" full>
            <ListEditor items={form.gallery} onChange={g => set({ gallery: g })} placeholder="https://…" testId="list-gallery" />
          </F>
          <F label="Category">
            <select className="w-full h-10 border border-[#D4D4D0] px-3 text-sm rounded-none"
                     value={form.category_slug || "tv_formats"}
                     onChange={e => set({ category_slug: e.target.value })} data-testid="field-category">
              <option value="tv_formats">TV Formats</option>
            </select>
          </F>
          {isAdmin && (
            <F label="Visibility status">
              <select className="w-full h-10 border border-[#D4D4D0] px-3 text-sm rounded-none"
                       value={form.status} onChange={e => set({ status: e.target.value })} data-testid="field-status">
                <option value="active">Active — visible in library</option>
                <option value="draft">Draft — hidden</option>
                <option value="closed">Closed — frozen</option>
              </select>
            </F>
          )}
        </Section>

        <Section value="summary" title="Executive summary" subtitle="Overview, purpose, key selling points" testId="section-summary">
          <F label="Project overview" full><Textarea rows={4} value={form.overview} onChange={e => set({ overview: e.target.value })} className="rounded-none" data-testid="field-overview" /></F>
          <F label="Purpose" full><Textarea rows={3} value={form.purpose} onChange={e => set({ purpose: e.target.value })} className="rounded-none" data-testid="field-purpose" /></F>
          <F label="Why this project exists" full><Textarea rows={3} value={form.why_exists} onChange={e => set({ why_exists: e.target.value })} className="rounded-none" data-testid="field-whyexists" /></F>
          <F label="Key selling points" full>
            <ListEditor items={form.key_selling_points} onChange={x => set({ key_selling_points: x })} placeholder="A single selling point" testId="list-selling-points" />
          </F>
        </Section>

        <Section value="story" title="Story & concept" subtitle="Full concept, narrative, episode structure, tone" testId="section-story">
          <F label="Full concept" full><Textarea rows={5} value={form.concept} onChange={e => set({ concept: e.target.value })} className="rounded-none" data-testid="field-concept" /></F>
          <F label="Narrative"><Textarea rows={3} value={form.narrative} onChange={e => set({ narrative: e.target.value })} className="rounded-none" data-testid="field-narrative" /></F>
          <F label="Episode structure"><Textarea rows={3} value={form.episode_structure} onChange={e => set({ episode_structure: e.target.value })} className="rounded-none" data-testid="field-episode-structure" /></F>
          <F label="Tone" full><Input value={form.tone} onChange={e => set({ tone: e.target.value })} placeholder="e.g. cinematic, editorial, warm, immersive" data-testid="field-tone" /></F>
        </Section>

        <Section value="objectives" title="Objectives" subtitle="Entertainment, education, awareness, commercial" testId="section-objectives">
          <F label="Entertainment objective"><Textarea rows={3} value={form.objective_entertainment} onChange={e => set({ objective_entertainment: e.target.value })} className="rounded-none" data-testid="field-obj-entertainment" /></F>
          <F label="Education objective"><Textarea rows={3} value={form.objective_education} onChange={e => set({ objective_education: e.target.value })} className="rounded-none" data-testid="field-obj-education" /></F>
          <F label="Awareness objective"><Textarea rows={3} value={form.objective_awareness} onChange={e => set({ objective_awareness: e.target.value })} className="rounded-none" data-testid="field-obj-awareness" /></F>
          <F label="Commercial objective"><Textarea rows={3} value={form.objective_commercial} onChange={e => set({ objective_commercial: e.target.value })} className="rounded-none" data-testid="field-obj-commercial" /></F>
        </Section>

        <Section value="audience" title="Target audience" subtitle="Demographics · Interests · Geography · Viewing habits" testId="section-audience-edit">
          <F label="Demographics" full><Textarea rows={2} value={form.audience_demographics} onChange={e => set({ audience_demographics: e.target.value })} className="rounded-none" data-testid="field-audience-demo" /></F>
          <F label="Interests"><Textarea rows={2} value={form.audience_interests} onChange={e => set({ audience_interests: e.target.value })} className="rounded-none" data-testid="field-audience-interests" /></F>
          <F label="Geography"><Textarea rows={2} value={form.audience_geography} onChange={e => set({ audience_geography: e.target.value })} className="rounded-none" data-testid="field-audience-geo" /></F>
          <F label="Viewing habits" full><Textarea rows={2} value={form.audience_viewing_habits} onChange={e => set({ audience_viewing_habits: e.target.value })} className="rounded-none" data-testid="field-audience-habits" /></F>
        </Section>

        <Section value="format" title="Production format" subtitle="Episode length, crew, locations, equipment" testId="section-format-edit">
          <F label="Number of episodes" full={false}><Input type="number" value={form.total_episodes} onChange={e => set({ total_episodes: e.target.value })} data-testid="field-episodes" /></F>
          <F label="Episode duration (minutes)" full={false}><Input type="number" value={form.episode_duration || 0} onChange={e => set({ episode_duration: e.target.value })} data-testid="field-duration" /></F>
          <F label="Production workflow" full><Textarea rows={3} value={form.production_workflow} onChange={e => set({ production_workflow: e.target.value })} className="rounded-none" data-testid="field-workflow" /></F>
          <F label="Required crew"><Textarea rows={3} value={form.required_crew} onChange={e => set({ required_crew: e.target.value })} className="rounded-none" data-testid="field-crew" /></F>
          <F label="Locations"><Textarea rows={3} value={form.locations} onChange={e => set({ locations: e.target.value })} className="rounded-none" data-testid="field-locations" /></F>
          <F label="Equipment"><Textarea rows={3} value={form.equipment} onChange={e => set({ equipment: e.target.value })} className="rounded-none" data-testid="field-equipment" /></F>
          <F label="Distribution"><Input value={form.distribution} onChange={e => set({ distribution: e.target.value })} data-testid="field-distribution" /></F>
          <F label="Production format tag"><Input value={form.production_format} onChange={e => set({ production_format: e.target.value })} placeholder="documentary · interview_series · travel …" data-testid="field-prod-format" /></F>
          <F label="Languages" full>
            <ListEditor items={form.languages} onChange={l => set({ languages: l })} placeholder="Add a language" testId="list-languages" />
          </F>
        </Section>

        <Section value="sponsorship" title="Sponsorship opportunities" subtitle="Informational only — no pricing" testId="section-sponsorship-edit">
          <F label="Sponsorship tiers" full>
            <ListEditor items={form.sponsorship_opportunities} onChange={s => set({ sponsorship_opportunities: s })}
                         placeholder="e.g. Title Sponsor, Episode Sponsor, Product Placement" testId="list-sponsorship" />
          </F>
          <F label="Rights & inclusions" full><Textarea rows={3} value={form.sponsorship_rights} onChange={e => set({ sponsorship_rights: e.target.value })} className="rounded-none" data-testid="field-rights" /></F>
        </Section>

        <Section value="tech" title="Technical specifications" subtitle="Video · Audio · Graphics · Delivery" testId="section-tech-edit">
          {[
            ["cameras","Cameras"],["resolution","Resolution"],["frame_rate","Frame rate"],["audio","Audio"],
            ["graphics","Graphics"],["delivery","Delivery format"],["subtitles","Subtitle rules"],["thumbnails","Thumbnail requirements"],
          ].map(([k, label]) => (
            <F key={k} label={label}>
              <Input value={form.technical_specs?.[k] || ""} onChange={e => setNested("technical_specs", k, e.target.value)} data-testid={`field-tech-${k}`} />
            </F>
          ))}
        </Section>

        <Section value="brand" title="Brand guidelines" subtitle="Logo · Intro · Outro · Typography · Motion · Music · Palette" testId="section-brand-edit">
          {[
            ["logo","Logo usage"],["intro","Intro sequence"],["outro","Outro sequence"],
            ["fonts","Typography"],["motion","Motion graphics"],["music","Music"],
            ["colors","Color palette"],
          ].map(([k, label]) => (
            <F key={k} label={label} full={k === "colors"}>
              <Input value={form.brand_guidelines?.[k] || ""} onChange={e => setNested("brand_guidelines", k, e.target.value)} data-testid={`field-brand-${k}`} />
            </F>
          ))}
        </Section>

        <Section value="downloads" title="Download center" subtitle="Sponsor Presentation, Production Bible, Brand Guidelines, Graphics…" testId="section-downloads-edit">
          <div className="col-span-2">
            <div className="imh-eyebrow">Current assets</div>
            {form.download_assets?.length ? (
              <div className="mt-2 divide-y divide-[#E4E4E1] border border-[#E4E4E1]">
                {form.download_assets.map(a => (
                  <div key={a.id || a.url} className="flex items-center justify-between px-4 py-2 text-sm" data-testid={`asset-row-${a.id || a.url}`}>
                    <div className="min-w-0">
                      <div className="font-editorial">{a.label}</div>
                      <div className="font-mono-imh text-[10px] text-[#A1A1AA] truncate max-w-md">{a.url}</div>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <span className="text-[10px] uppercase tracking-widest text-[#52525B]">{a.filetype || "file"}</span>
                      {projectId && editable && (
                        <button onClick={() => removeAsset(a.id)} className="text-[#991B1B] hover:text-[#7f1616]" data-testid={`asset-remove-${a.id}`}>
                          <Trash2 size={13} />
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : <div className="mt-2 text-sm text-[#52525B]">No assets yet.</div>}
          </div>

          {projectId && editable && (
            <div className="col-span-2 imh-card p-4 bg-[#F9F9F6]">
              <div className="imh-eyebrow">Add an asset</div>
              <div className="grid grid-cols-2 gap-3 mt-3">
                <F label="Label"><Input value={asset.label} onChange={e => setAsset(a => ({ ...a, label: e.target.value }))} placeholder="Sponsor Presentation (Word)" data-testid="asset-label" /></F>
                <F label="Filetype"><Input value={asset.filetype} onChange={e => setAsset(a => ({ ...a, filetype: e.target.value }))} placeholder="pdf · docx · zip · mp4 …" data-testid="asset-filetype" /></F>
                <F label="Upload file" full>
                  <div className="flex gap-2 items-center">
                    <Input value={asset.url} onChange={e => setAsset(a => ({ ...a, url: e.target.value }))} placeholder="URL of the file" data-testid="asset-url" />
                    {isAdmin && (
                      <AssetUploader accept="*/*" kind="file" icon={Upload} currentUrl={asset.url}
                                       onUploaded={(url, meta) => setAsset(a => ({
                                          ...a, url,
                                          storage_path: meta.storage_path,
                                          original_filename: meta.original_filename,
                                          filetype: a.filetype || (meta.original_filename || "").split(".").pop() || "",
                                          label: a.label || meta.original_filename || a.label,
                                       }))} testId="asset-upload" />
                    )}
                  </div>
                </F>
                <div className="col-span-2">
                  <Button onClick={addAsset} data-testid="asset-add" className="rounded-none bg-[#0A0A0A] hover:bg-black text-white">
                    <Plus size={14} className="mr-2" /> Add asset
                  </Button>
                </div>
              </div>
            </div>
          )}
        </Section>

        {/* Revision history — admins only */}
        {isAdmin && project?.revision_history?.length > 0 && (
          <Section value="history" title="Revision history" subtitle="Every moderation decision on this project" testId="section-history">
            <div className="col-span-2 border border-[#E4E4E1] divide-y divide-[#E4E4E1]">
              {project.revision_history.map((h, i) => (
                <div key={i} className="px-4 py-2 text-sm">
                  <span className="font-mono-imh text-[10px] uppercase tracking-widest text-[#52525B]">{h.decision}</span>
                  <span className="ml-2 text-[11px] text-[#A1A1AA]">{h.at?.slice(0, 16).replace("T", " ")} · {h.by_name}</span>
                  {h.admin_feedback && <div className="mt-1 text-[#0A0A0A] italic">"{h.admin_feedback}"</div>}
                </div>
              ))}
            </div>
          </Section>
        )}

      </Accordion>
      </fieldset>

      {/* Moderation dialog */}
      <Dialog open={moderateOpen} onOpenChange={setModerateOpen}>
        <DialogContent className="rounded-none border-[#0A0A0A]" data-testid="moderate-dialog">
          <DialogHeader>
            <DialogTitle className="font-editorial text-2xl capitalize">{moderateDecision.replace("_", " ")} project</DialogTitle>
          </DialogHeader>
          <div className="grid grid-cols-1 gap-3 mt-2">
            <F label="Feedback to partner (shared)">
              <Textarea rows={3} value={moderateFeedback} onChange={e => setModerateFeedback(e.target.value)}
                         className="rounded-none" data-testid="moderate-feedback" />
            </F>
            <F label="Internal notes (admin only)">
              <Textarea rows={2} value={moderateInternal} onChange={e => setModerateInternal(e.target.value)}
                         className="rounded-none bg-[#FFFAF3]" data-testid="moderate-internal" />
            </F>
          </div>
          <DialogFooter>
            <Button onClick={moderate} data-testid="moderate-confirm" className="rounded-none bg-[#0033A0] hover:bg-[#002277]">
              Confirm decision
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
