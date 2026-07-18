import { useEffect, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import api, { formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import {
  ProjectHero, ProjectOverview, ProjectConcept, ProjectObjectives,
  ProjectAudience, ProjectFormat, ProjectSponsorship,
  ProjectTechnicalSpecs, ProjectBrandGuidelines,
  ProjectDownloadCenter,
} from "@/components/project/ProjectBlocks";
import {
  Edit3, Check, Rewind, X, Eye, EyeOff, Star, StarOff, Archive,
  ClipboardList, Clock, ShieldCheck, ExternalLink,
} from "lucide-react";

/**
 * AdminProjectView — the single admin landing surface for BOTH partner
 * submissions and Official Projects.
 *
 * The admin reads the SAME public Project Page a country partner would
 * read (Hero + every modular block), so the review is done on the
 * complete project. A sticky moderation sidebar exposes every admin
 * decision: Approve · Request revision · Reject · Publish · Feature ·
 * Archive · Internal notes · Submission & revision history · Edit
 * project.
 */
const MODERATION_STYLE = {
  draft:              { color: "#52525B", label: "Draft" },
  submitted:          { color: "#B45309", label: "Submitted for review" },
  revision_requested: { color: "#0033A0", label: "Revision requested" },
  approved:           { color: "#166534", label: "Approved" },
  rejected:           { color: "#991B1B", label: "Rejected" },
};

export default function AdminProjectView() {
  const { id } = useParams();
  const { user } = useAuth();
  const nav = useNavigate();
  const isAdmin = user?.role === "admin" || user?.role === "owner";

  const [project, setProject] = useState(null);
  const [category, setCategory] = useState(null);
  const [applications, setApplications] = useState([]);
  const [modOpen, setModOpen] = useState(false);
  const [modDecision, setModDecision] = useState("approved");
  const [modFeedback, setModFeedback] = useState("");
  const [modInternal, setModInternal] = useState("");
  const [internalNote, setInternalNote] = useState("");

  const load = () => {
    api.get(`/tv-projects/${id}`).then(r => {
      setProject(r.data);
      const slug = r.data.category_slug || r.data.category;
      if (slug) api.get(`/categories/${slug}`).then(c => setCategory(c.data)).catch(() => {});
      setInternalNote(r.data.internal_notes || "");
    });
    if (isAdmin) {
      api.get(`/tv-projects/${id}/applications`).then(r => setApplications(r.data)).catch(() => {});
    }
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [id]);

  const moderate = async () => {
    try {
      await api.patch(`/admin/projects/${id}/moderate`, {
        decision: modDecision, admin_feedback: modFeedback, internal_notes: modInternal,
      });
      setModOpen(false);
      toast.success(`Marked ${modDecision.replace("_", " ")}`);
      load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };
  const openMod = (d) => { setModDecision(d); setModFeedback(project?.admin_feedback || ""); setModInternal(project?.internal_notes || ""); setModOpen(true); };
  const toggle = async (endpoint, key) => {
    try {
      await api.patch(`/admin/projects/${id}/${endpoint}`, { [key]: !project[key] });
      toast.success("Updated");
      load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };
  const saveInternalOnly = async () => {
    try {
      await api.patch(`/admin/projects/${id}/moderate`, {
        decision: project.moderation_status,   // no state change
        admin_feedback: project.admin_feedback || "",
        internal_notes: internalNote,
      });
      toast.success("Internal note saved");
      load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };

  if (!project) return <div className="p-10 imh-eyebrow" data-testid="admin-view-loading">Loading…</div>;

  const modStyle = MODERATION_STYLE[project.moderation_status] || MODERATION_STYLE.approved;
  const isPartner = project.source === "partner";
  const pending = project.moderation_status === "submitted" || project.moderation_status === "revision_requested";

  return (
    <div className="flex flex-col lg:flex-row bg-[#F9F9F6]" data-testid="admin-project-view">
      {/* ---- Main column: complete public Project Page ---- */}
      <div className="flex-1 min-w-0" data-testid="admin-project-read-view">
        <ProjectHero project={project} category={category}
                      backTo={isPartner ? "/admin/proposals" : "/admin/tv-projects"}
                      backLabel={isPartner ? "Partner submissions" : "Project Library"} />

        <div className="px-10 py-14 space-y-14 max-w-6xl">
          <ProjectOverview project={project} />
          <ProjectConcept project={project} />
          <ProjectObjectives project={project} />
          <ProjectAudience project={project} />
          <ProjectFormat project={project} />
          <ProjectSponsorship project={project} />
          <ProjectTechnicalSpecs project={project} />
          <ProjectBrandGuidelines project={project} />
          <ProjectDownloadCenter project={project} />

          {/* Production applications received (Official projects) */}
          {applications.length > 0 && (
            <section data-testid="admin-view-applications">
              <div className="imh-eyebrow flex items-center gap-2"><ClipboardList size={11} /> 10 · Applications</div>
              <h2 className="font-editorial text-3xl mt-2 mb-6">Country partner applications</h2>
              <div className="imh-card divide-y divide-[#E4E4E1]">
                {applications.map(a => (
                  <div key={a.id} className="px-6 py-3 flex items-center justify-between text-sm">
                    <div>
                      <div className="font-editorial">{a.agency_name || a.rep_name}</div>
                      <div className="text-xs text-[#52525B]">{a.rep_name} · {a.country}</div>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className={`text-[10px] uppercase tracking-widest font-mono-imh px-2 py-1
                        ${a.status === "approved" ? "bg-[#E6F2EA] text-[#166534]" :
                          a.status === "rejected" ? "bg-[#FBEBEB] text-[#991B1B]" :
                          a.status === "revision_requested" ? "bg-[#EEF2FF] text-[#0033A0]" :
                          "bg-[#F5F0E1] text-[#B45309]"}`}>
                        {a.status.replace("_", " ")}
                      </span>
                      <Link to="/admin/proposals-review" className="text-[11px] uppercase tracking-widest text-[#0033A0] hover:text-[#002277] inline-flex items-center gap-1">
                        Review <ExternalLink size={11} />
                      </Link>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Revision history — always visible to admins */}
          {project.revision_history?.length > 0 && (
            <section data-testid="admin-view-history">
              <div className="imh-eyebrow flex items-center gap-2"><Clock size={11} /> Revision history</div>
              <h2 className="font-editorial text-3xl mt-2 mb-6">All decisions on this project</h2>
              <div className="imh-card divide-y divide-[#E4E4E1]">
                {[...project.revision_history].reverse().map((h, i) => (
                  <div key={i} className="px-6 py-3 text-sm">
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] uppercase tracking-widest font-mono-imh px-2 py-1"
                             style={{ background: (MODERATION_STYLE[h.decision]?.color || "#0A0A0A") + "20",
                                       color: MODERATION_STYLE[h.decision]?.color || "#0A0A0A" }}>
                        {h.decision?.replace("_", " ")}
                      </span>
                      <span className="text-[11px] text-[#52525B]">{(h.at || "").slice(0, 16).replace("T", " ")} · {h.by_name}</span>
                    </div>
                    {h.admin_feedback && <div className="mt-1 italic text-[#0A0A0A] pl-1">"{h.admin_feedback}"</div>}
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>
      </div>

      {/* ---- Sticky moderation sidebar (Admins only) ---- */}
      {isAdmin && (
        <aside className="lg:w-[380px] shrink-0 lg:sticky lg:top-0 lg:h-screen overflow-y-auto p-6 border-l border-[#E4E4E1] bg-white"
                data-testid="moderation-panel">
          <div className="imh-eyebrow flex items-center gap-2"><ShieldCheck size={11} /> Moderation panel</div>
          <div className="mt-3 flex flex-wrap gap-2 items-center">
            <span className="text-[10px] uppercase tracking-widest font-mono-imh px-2 py-1"
                   style={{ background: modStyle.color, color: "#fff" }}
                   data-testid="mod-panel-status">
              {modStyle.label}
            </span>
            <span className="text-[10px] uppercase tracking-widest text-[#52525B]">
              {isPartner ? "Country partner" : "Official"}
            </span>
          </div>
          {isPartner && (
            <div className="mt-3 text-sm">
              <div className="text-[10px] uppercase tracking-widest text-[#A1A1AA]">Submitted by</div>
              <div className="mt-1">{project.submitted_by_agency || project.submitted_by_rep_name}</div>
              <div className="text-xs text-[#52525B]">{project.submitted_by_country || "—"}</div>
            </div>
          )}

          <div className="mt-6 grid grid-cols-1 gap-2">
            <Button onClick={() => openMod("approved")} data-testid="mod-approve"
                     className="rounded-none bg-[#166534] hover:bg-[#0f4a25] text-white justify-start">
              <Check size={14} className="mr-2" /> Approve project
            </Button>
            <Button onClick={() => openMod("revision_requested")} data-testid="mod-revise"
                     className="rounded-none bg-[#0033A0] hover:bg-[#002277] text-white justify-start">
              <Rewind size={14} className="mr-2" /> Request revision
            </Button>
            <Button onClick={() => openMod("rejected")} data-testid="mod-reject" variant="outline"
                     className="rounded-none border-[#991B1B] text-[#991B1B] hover:bg-[#FBEBEB] justify-start">
              <X size={14} className="mr-2" /> Reject project
            </Button>
          </div>

          <div className="mt-6 grid grid-cols-2 gap-2 border-t border-[#E4E4E1] pt-6">
            <Button onClick={() => toggle("publish", "published")} data-testid="mod-publish"
                     variant="outline" className="rounded-none">
              {project.published ? <><EyeOff size={13} className="mr-1" /> Unpublish</> : <><Eye size={13} className="mr-1" /> Publish</>}
            </Button>
            <Button onClick={() => toggle("feature", "featured")} data-testid="mod-feature"
                     variant="outline" className="rounded-none">
              {project.featured ? <><StarOff size={13} className="mr-1" /> Unfeature</> : <><Star size={13} className="mr-1" /> Feature</>}
            </Button>
            <Button onClick={() => toggle("archive", "archived")} data-testid="mod-archive"
                     variant="outline" className="rounded-none col-span-2">
              <Archive size={13} className="mr-2" /> {project.archived ? "Unarchive" : "Archive"} project
            </Button>
          </div>

          <div className="mt-6 border-t border-[#E4E4E1] pt-6">
            <Label className="imh-eyebrow">Internal notes (admin only)</Label>
            <Textarea rows={4} value={internalNote} onChange={e => setInternalNote(e.target.value)}
                       placeholder="Confidential. Never visible to partners."
                       className="rounded-none mt-2 bg-[#FFFAF3]" data-testid="mod-internal-notes" />
            <Button onClick={saveInternalOnly} size="sm" data-testid="mod-save-internal"
                     className="rounded-none bg-[#0A0A0A] text-white mt-2 w-full">
              Save note
            </Button>
          </div>

          {project.admin_feedback && (
            <div className="mt-6 border-t border-[#E4E4E1] pt-6">
              <div className="imh-eyebrow">Last feedback shared</div>
              <div className="mt-2 text-sm italic">"{project.admin_feedback}"</div>
              {project.decided_at && <div className="mt-1 text-[10px] font-mono-imh text-[#A1A1AA]">on {project.decided_at.slice(0, 10)}</div>}
            </div>
          )}

          <div className="mt-6 border-t border-[#E4E4E1] pt-6 grid grid-cols-1 gap-2">
            <Button onClick={() => nav(`/admin/tv-projects/${id}/edit`)} data-testid="mod-edit"
                     className="rounded-none bg-[#0033A0] hover:bg-[#002277] text-white justify-start">
              <Edit3 size={14} className="mr-2" /> Edit project
            </Button>
            <a href={`/rep/tv/${id}`} target="_blank" rel="noreferrer" data-testid="mod-preview"
                className="rounded-none h-10 border border-[#E4E4E1] hover:border-[#0A0A0A] px-3 inline-flex items-center gap-2 text-sm">
              <Eye size={14} /> Preview as partner
            </a>
          </div>

          {/* Submission metadata */}
          <div className="mt-6 border-t border-[#E4E4E1] pt-6 text-[11px] font-mono-imh text-[#52525B] space-y-1">
            <div>Created · {project.created_at?.slice(0, 10)}</div>
            {project.submitted_at && <div>Submitted · {project.submitted_at.slice(0, 10)}</div>}
            {project.decided_at && <div>Decided · {project.decided_at.slice(0, 10)}</div>}
            <div>Applications · {project.pending_applications_count || 0} pending / {project.approved_applications_count || 0} approved</div>
          </div>
        </aside>
      )}

      {/* ---- Moderation dialog ---- */}
      <Dialog open={modOpen} onOpenChange={setModOpen}>
        <DialogContent className="rounded-none border-[#0A0A0A]" data-testid="mod-dialog">
          <DialogHeader>
            <DialogTitle className="font-editorial text-2xl capitalize">{modDecision.replace("_", " ")} project</DialogTitle>
          </DialogHeader>
          <div className="grid grid-cols-1 gap-3 mt-2">
            <div>
              <Label className="imh-eyebrow">Feedback to partner (shared)</Label>
              <Textarea rows={3} value={modFeedback} onChange={e => setModFeedback(e.target.value)}
                         className="rounded-none mt-2" data-testid="mod-dialog-feedback" />
            </div>
            <div>
              <Label className="imh-eyebrow">Internal notes (admin only)</Label>
              <Textarea rows={2} value={modInternal} onChange={e => setModInternal(e.target.value)}
                         className="rounded-none mt-2 bg-[#FFFAF3]" data-testid="mod-dialog-internal" />
            </div>
          </div>
          <DialogFooter>
            <Button onClick={moderate} data-testid="mod-dialog-confirm"
                     className="rounded-none bg-[#0033A0] hover:bg-[#002277]">
              Confirm decision
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
