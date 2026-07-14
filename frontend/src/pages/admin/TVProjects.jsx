import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api, { formatApiError } from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from "@/components/ui/dialog";
import { toast } from "sonner";
import { Plus, ArrowUpRight, ImageIcon, Video, Loader2 } from "lucide-react";
import { usd } from "@/lib/constants";
import { API } from "@/lib/api";

export default function TVProjects() {
  const [projects, setProjects] = useState([]);
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    title: "", tagline: "", synopsis: "", hero_image_url: "", demo_video_url: "",
    target_audience: "", distribution: "", languages: "English",
    total_episodes: 10, price_per_episode_usd: 500, sponsorship_rights: "",
  });

  const load = () => api.get("/tv-projects").then(r => setProjects(r.data));
  useEffect(() => { load(); }, []);

  const uploadFile = async (file, kind) => {
    const fd = new FormData();
    fd.append("file", file); fd.append("kind", kind);
    const { data } = await api.post("/admin/upload", fd, { headers: { "Content-Type": "multipart/form-data" } });
    // return absolute URL via backend
    return `${API}/files/${data.storage_path}`;
  };

  const save = async () => {
    setSaving(true);
    try {
      const payload = {
        ...form,
        languages: form.languages.split(",").map(s => s.trim()).filter(Boolean),
        total_episodes: Number(form.total_episodes),
        price_per_episode_usd: Number(form.price_per_episode_usd),
      };
      await api.post("/admin/tv-projects", payload);
      toast.success("TV project published");
      setOpen(false);
      setForm({ title: "", tagline: "", synopsis: "", hero_image_url: "", demo_video_url: "",
        target_audience: "", distribution: "", languages: "English",
        total_episodes: 10, price_per_episode_usd: 500, sponsorship_rights: "" });
      await load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
    finally { setSaving(false); }
  };

  return (
    <div>
      <PageHeader
        eyebrow="Commercial · Independent TV"
        title="TV Projects"
        description="Original productions available for sponsorship. Every project has its own investment-grade presentation page."
        actions={
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
                <F label="Internal price / episode (USD)"><Input data-testid="tv-price" type="number" value={form.price_per_episode_usd} onChange={e => setForm({ ...form, price_per_episode_usd: e.target.value })} /></F>
                <F label="Sponsorship rights" full><Textarea data-testid="tv-rights" rows={3} className="rounded-none" value={form.sponsorship_rights} onChange={e => setForm({ ...form, sponsorship_rights: e.target.value })} /></F>
              </div>
              <DialogFooter>
                <Button data-testid="tv-save" onClick={save} disabled={saving} className="rounded-none bg-[#0033A0] hover:bg-[#002277]">
                  {saving && <Loader2 size={14} className="animate-spin mr-2" />} Publish project
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        }
      />
      <div className="px-10 py-10 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {projects.map(p => (
          <Link key={p.id} to={`/admin/tv-projects/${p.id}`} className="imh-card group overflow-hidden hover:border-[#0A0A0A]" data-testid={`tv-card-${p.id}`} style={{ transition: "border-color 160ms ease" }}>
            <div className="aspect-[16/10] bg-[#0A1128] overflow-hidden">
              {p.hero_image_url ? <img src={p.hero_image_url} alt="" className="w-full h-full object-cover group-hover:scale-[1.02]" style={{ transition: "transform 400ms ease" }} /> : null}
            </div>
            <div className="p-5">
              <div className="imh-eyebrow">{p.total_episodes} episodes · {usd(p.price_per_episode_usd)}/ep</div>
              <h3 className="font-editorial text-2xl mt-2 leading-tight">{p.title}</h3>
              <p className="text-sm text-[#52525B] mt-2 line-clamp-2">{p.tagline}</p>
              <div className="mt-4 flex items-center justify-between text-xs text-[#52525B]">
                <span>{(p.sponsored_episodes?.length || 0)} / {p.total_episodes} sponsored</span>
                <ArrowUpRight size={14} className="text-[#0033A0]" />
              </div>
            </div>
          </Link>
        ))}
        {projects.length === 0 && <div className="col-span-full text-center py-16 text-[#52525B]">No TV projects yet. Publish your first production above.</div>}
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
    try {
      const url = await uploader(f, kind);
      onUploaded(url);
      toast.success("Uploaded");
    } catch (err) { toast.error("Upload failed"); }
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
