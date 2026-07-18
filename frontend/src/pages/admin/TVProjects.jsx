import { useEffect, useState, useMemo } from "react";
import { Link } from "react-router-dom";
import api, { formatApiError } from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from "@/components/ui/dialog";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { toast } from "sonner";
import { Plus, ImageIcon, Video, Loader2, MoreHorizontal } from "lucide-react";
import { API } from "@/lib/api";

const STATUSES = [
  { value: "all", label: "All statuses" },
  { value: "active", label: "Active" },
  { value: "draft", label: "Draft" },
  { value: "closed", label: "Closed" },
];

const STATUS_STYLE = {
  active: { bg: "#E6F2EA", color: "#166534", label: "Active" },
  draft: { bg: "#F5F0E1", color: "#B45309", label: "Draft" },
  closed: { bg: "#EBEBE6", color: "#52525B", label: "Closed" },
};

export default function TVProjects() {
  const [projects, setProjects] = useState([]);
  const [status, setStatus] = useState("all");
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    title: "", tagline: "", synopsis: "", hero_image_url: "", demo_video_url: "",
    target_audience: "", distribution: "", languages: "English",
    total_episodes: 10, sponsorship_rights: "",
    status: "active",
  });

  const load = () => {
    const url = status === "all" ? "/tv-projects" : `/tv-projects?status=${status}`;
    return api.get(url).then(r => setProjects(r.data));
  };
  useEffect(() => { load(); }, [status]);

  const uploadFile = async (file, kind) => {
    const fd = new FormData();
    fd.append("file", file); fd.append("kind", kind);
    const { data } = await api.post("/admin/upload", fd, { headers: { "Content-Type": "multipart/form-data" } });
    return `${API}/files/${data.storage_path}`;
  };

  const save = async () => {
    setSaving(true);
    try {
      const payload = {
        ...form,
        languages: form.languages.split(",").map(s => s.trim()).filter(Boolean),
        total_episodes: Number(form.total_episodes),
      };
      await api.post("/admin/tv-projects", payload);
      toast.success("TV project published");
      setOpen(false);
      setForm({ title: "", tagline: "", synopsis: "", hero_image_url: "", demo_video_url: "",
        target_audience: "", distribution: "", languages: "English",
        total_episodes: 10, sponsorship_rights: "", status: "active" });
      await load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
    finally { setSaving(false); }
  };

  const changeStatus = async (id, newStatus) => {
    try {
      await api.patch(`/admin/tv-projects/${id}/status`, { status: newStatus });
      toast.success(`Moved to ${newStatus}`);
      await load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };

  return (
    <div>
      <PageHeader
        eyebrow="Project Library"
        title="Projects"
        description="Modular project packages ready for country partner production. Each project ships with a production bible, brand guidelines and download center."
        actions={
          <div className="flex gap-2 items-center">
            <div className="flex gap-1 border border-[#E4E4E1] bg-white" data-testid="tv-status-filter">
              {STATUSES.map(s => (
                <button key={s.value} onClick={() => setStatus(s.value)}
                  className={`px-3 py-2 text-[11px] uppercase tracking-widest ${status === s.value ? "bg-[#0A0A0A] text-white" : "text-[#0A0A0A] hover:bg-[#F9F9F6]"}`}
                  data-testid={`status-${s.value}`}>{s.label}</button>
              ))}
            </div>
            <Dialog open={open} onOpenChange={setOpen}>
              <DialogTrigger asChild>
                <Button data-testid="new-tv-button" className="rounded-none h-10 bg-[#0033A0] hover:bg-[#002277] text-white">
                  <Plus size={16} className="mr-2" /> New TV project
                </Button>
              </DialogTrigger>
              <DialogContent className="max-w-2xl rounded-none border-[#0A0A0A]">
                <DialogHeader><DialogTitle className="font-editorial text-2xl">Publish TV project</DialogTitle></DialogHeader>
                <div className="grid grid-cols-2 gap-4 mt-4 max-h-[65vh] overflow-y-auto pr-2">
                  <F label="Title" full><Input data-testid="tv-title" value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} /></F>
                  <F label="Tagline" full><Input data-testid="tv-tagline" value={form.tagline} onChange={e => setForm({ ...form, tagline: e.target.value })} /></F>
                  <F label="Synopsis" full><Textarea data-testid="tv-synopsis" rows={4} className="rounded-none" value={form.synopsis} onChange={e => setForm({ ...form, synopsis: e.target.value })} /></F>
                  <F label="Hero image">
                    <UploadRow accept="image/*" testId="tv-hero-upload" icon={ImageIcon}
                      onUploaded={(url) => setForm({ ...form, hero_image_url: url })}
                      uploader={uploadFile} kind="image"
                      currentUrl={form.hero_image_url}
                    />
                  </F>
                  <F label="Demo video">
                    <UploadRow accept="video/mp4,video/webm" testId="tv-video-upload" icon={Video}
                      onUploaded={(url) => setForm({ ...form, demo_video_url: url })}
                      uploader={uploadFile} kind="video"
                      currentUrl={form.demo_video_url}
                    />
                  </F>
                  <F label="Target audience"><Input data-testid="tv-audience" value={form.target_audience} onChange={e => setForm({ ...form, target_audience: e.target.value })} /></F>
                  <F label="Distribution"><Input data-testid="tv-distribution" value={form.distribution} onChange={e => setForm({ ...form, distribution: e.target.value })} /></F>
                  <F label="Languages (comma-separated)" full><Input data-testid="tv-languages" value={form.languages} onChange={e => setForm({ ...form, languages: e.target.value })} /></F>
                  <F label="Total episodes"><Input data-testid="tv-episodes" type="number" value={form.total_episodes} onChange={e => setForm({ ...form, total_episodes: e.target.value })} /></F>
                  <F label="Sponsorship rights" full><Textarea data-testid="tv-rights" rows={3} className="rounded-none" value={form.sponsorship_rights} onChange={e => setForm({ ...form, sponsorship_rights: e.target.value })} /></F>
                  <F label="Initial status">
                    <select className="w-full h-10 border border-[#D4D4D0] px-3 text-sm rounded-none" data-testid="tv-status"
                      value={form.status} onChange={e => setForm({ ...form, status: e.target.value })}>
                      <option value="active">Active</option>
                      <option value="draft">Draft</option>
                      <option value="closed">Closed</option>
                    </select>
                  </F>
                </div>
                <DialogFooter>
                  <Button data-testid="tv-save" onClick={save} disabled={saving} className="rounded-none bg-[#0033A0] hover:bg-[#002277]">
                    {saving && <Loader2 size={14} className="animate-spin mr-2" />} Publish project
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>
        }
      />
      <div className="px-10 py-10 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {projects.map(p => {
          const s = STATUS_STYLE[p.status] || STATUS_STYLE.draft;
          return (
            <div key={p.id} className="imh-card group overflow-hidden hover:border-[#0A0A0A]" style={{ transition: "border-color 160ms ease" }} data-testid={`tv-card-${p.id}`}>
              <Link to={`/admin/tv-projects/${p.id}`} className="block">
                <div className="aspect-[16/10] bg-[#0A1128] overflow-hidden">
                  {p.hero_image_url ? <img src={p.hero_image_url} alt="" className="w-full h-full object-cover group-hover:scale-[1.02]" style={{ transition: "transform 400ms ease" }} /> : null}
                </div>
              </Link>
              <div className="p-5">
                <div className="flex items-center justify-between">
                  <div className="imh-eyebrow">{p.total_episodes} episodes</div>
                  <span className="px-2 py-0.5 text-[10px] uppercase tracking-widest font-mono-imh" style={{ background: s.bg, color: s.color }}>{s.label}</span>
                </div>
                <Link to={`/admin/tv-projects/${p.id}`}><h3 className="font-editorial text-2xl mt-2 leading-tight">{p.title}</h3></Link>
                <p className="text-sm text-[#52525B] mt-2 line-clamp-2">{p.tagline}</p>
                <div className="mt-4 flex items-center justify-between text-xs text-[#52525B]">
                  <span>{p.approved_applications_count || 0} approved · {p.pending_applications_count || 0} pending</span>
                  <DropdownMenu>
                    <DropdownMenuTrigger data-testid={`tv-menu-${p.id}`} className="text-[#52525B] hover:text-[#0A0A0A]">
                      <MoreHorizontal size={16} />
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end" className="rounded-none">
                      {p.status !== "active" && <DropdownMenuItem onClick={() => changeStatus(p.id, "active")} data-testid={`tv-set-active-${p.id}`}>Set active</DropdownMenuItem>}
                      {p.status !== "draft" && <DropdownMenuItem onClick={() => changeStatus(p.id, "draft")} data-testid={`tv-set-draft-${p.id}`}>Move to draft</DropdownMenuItem>}
                      {p.status !== "closed" && <DropdownMenuItem onClick={() => changeStatus(p.id, "closed")} data-testid={`tv-set-closed-${p.id}`}>Close (freeze)</DropdownMenuItem>}
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>
              </div>
            </div>
          );
        })}
        {projects.length === 0 && <div className="col-span-full text-center py-16 text-[#52525B]">No TV projects match the current filter.</div>}
      </div>
    </div>
  );
}

function F({ label, children, full }) {
  return <div className={full ? "col-span-2" : "col-span-1"}>
    <Label className="text-[11px] uppercase tracking-widest text-[#52525B]">{label}</Label>
    <div className="mt-2">{children}</div>
  </div>;
}

function UploadRow({ accept, testId, icon: Icon, onUploaded, uploader, kind, currentUrl }) {
  const [busy, setBusy] = useState(false);
  const onChange = async (e) => {
    const f = e.target.files?.[0]; if (!f) return;
    setBusy(true);
    try { const url = await uploader(f, kind); onUploaded(url); toast.success("Uploaded"); }
    catch (err) { toast.error("Upload failed"); }
    finally { setBusy(false); }
  };
  return (
    <div>
      <label className="flex items-center gap-2 h-10 px-3 border border-[#D4D4D0] cursor-pointer hover:bg-[#F9F9F6]" data-testid={testId}>
        {busy ? <Loader2 size={14} className="animate-spin" /> : <Icon size={14} />}
        <span className="text-xs text-[#52525B]">{currentUrl ? "Replace file" : "Choose file"}</span>
        <input type="file" accept={accept} className="hidden" onChange={onChange} />
      </label>
      {currentUrl && <div className="text-[11px] font-mono-imh text-[#A1A1AA] mt-1 truncate">{currentUrl}</div>}
    </div>
  );
}
