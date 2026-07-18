import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import api, { formatApiError } from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { Trash2 } from "lucide-react";

export default function TVProjectEdit() {
  const { id } = useParams();
  const nav = useNavigate();
  const [p, setP] = useState(null);

  useEffect(() => { api.get(`/tv-projects/${id}`).then(r => setP({ ...r.data, languages: (r.data.languages || []).join(", ") })); }, [id]);

  if (!p) return <div className="p-10 imh-eyebrow">Loading…</div>;

  const save = async () => {
    try {
      const payload = { ...p, languages: p.languages.split(",").map(s => s.trim()).filter(Boolean),
        total_episodes: Number(p.total_episodes) };
      delete payload.my_application;
      delete payload.pending_applications_count;
      delete payload.approved_applications_count;
      await api.patch(`/admin/tv-projects/${id}`, payload);
      toast.success("Project updated");
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };

  const remove = async () => {
    if (!confirm("Delete this TV project?")) return;
    try { await api.delete(`/admin/tv-projects/${id}`); toast.success("Deleted"); nav("/admin/tv-projects"); }
    catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };

  return (
    <div>
      <PageHeader eyebrow="Editing TV Project" title={p.title}
        actions={
          <div className="flex gap-2">
            <Button variant="outline" onClick={remove} className="rounded-none border-[#991B1B] text-[#991B1B]" data-testid="tv-delete"><Trash2 size={14} className="mr-2" />Delete</Button>
            <Button onClick={save} data-testid="tv-update-save" className="rounded-none bg-[#0033A0] hover:bg-[#002277]">Save changes</Button>
          </div>
        } />
      <div className="px-10 py-10 grid grid-cols-2 gap-6 max-w-4xl">
        <F label="Title" full><Input value={p.title} onChange={e => setP({ ...p, title: e.target.value })} /></F>
        <F label="Tagline" full><Input value={p.tagline || ""} onChange={e => setP({ ...p, tagline: e.target.value })} /></F>
        <F label="Synopsis" full><Textarea rows={5} className="rounded-none" value={p.synopsis || ""} onChange={e => setP({ ...p, synopsis: e.target.value })} /></F>
        <F label="Hero image URL" full><Input value={p.hero_image_url || ""} onChange={e => setP({ ...p, hero_image_url: e.target.value })} /></F>
        <F label="Demo video URL" full><Input value={p.demo_video_url || ""} onChange={e => setP({ ...p, demo_video_url: e.target.value })} /></F>
        <F label="Target audience"><Input value={p.target_audience || ""} onChange={e => setP({ ...p, target_audience: e.target.value })} /></F>
        <F label="Distribution"><Input value={p.distribution || ""} onChange={e => setP({ ...p, distribution: e.target.value })} /></F>
        <F label="Languages (comma-separated)" full><Input value={p.languages} onChange={e => setP({ ...p, languages: e.target.value })} /></F>
        <F label="Total episodes"><Input type="number" value={p.total_episodes} onChange={e => setP({ ...p, total_episodes: e.target.value })} /></F>
        <F label="Sponsorship rights" full><Textarea rows={3} className="rounded-none" value={p.sponsorship_rights || ""} onChange={e => setP({ ...p, sponsorship_rights: e.target.value })} /></F>
        <div className="col-span-2 imh-card p-5">
          <div className="imh-eyebrow">Production applications</div>
          <div className="mt-3 grid grid-cols-3 gap-4">
            <div><div className="text-[10px] uppercase tracking-widest text-[#A1A1AA]">Submitted</div><div className="font-mono-imh text-2xl mt-1">{p.pending_applications_count ?? 0}</div></div>
            <div><div className="text-[10px] uppercase tracking-widest text-[#A1A1AA]">Approved</div><div className="font-mono-imh text-2xl mt-1 text-[#166534]">{p.approved_applications_count ?? 0}</div></div>
            <div><div className="text-[10px] uppercase tracking-widest text-[#A1A1AA]">Category</div><div className="font-mono-imh text-sm mt-1">{(p.category_slug || p.category || "tv_formats").replace(/_/g, " ")}</div></div>
          </div>
          <div className="mt-4 text-xs text-[#52525B]">
            Country partners can apply to produce this project in their territory via the rep console.
          </div>
        </div>
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
