import { useParams, Link } from "react-router-dom";
import PageHeader from "@/components/PageHeader";
import ProjectEditor from "@/components/project/ProjectEditor";
import { ChevronLeft } from "lucide-react";

/**
 * Admin editor host — a form-based edit surface. Reserved for the deep
 * edit workflow (add fields, replace assets, update copy). The admin's
 * read-first review + moderation lives on `/admin/tv-projects/{id}`
 * (see AdminProjectView.jsx).
 */
export default function TVProjectEdit() {
  const { id } = useParams();
  return (
    <div>
      <PageHeader eyebrow="Project editor"
                   title={id ? "Edit project" : "New project"}
                   description="The same modular editor used by country partners. Update any section, replace assets, adjust technical specifications or brand guidelines. Moderation decisions live on the project's public page."
                   actions={id ? (
                     <Link to={`/admin/tv-projects/${id}`}
                            className="h-10 px-3 border border-[#E4E4E1] hover:border-[#0A0A0A] text-[11px] uppercase tracking-widest inline-flex items-center gap-1"
                            data-testid="editor-back-to-view">
                        <ChevronLeft size={12} /> Back to project page
                      </Link>
                   ) : null} />
      <ProjectEditor projectId={id} mode={id ? "edit" : "create-admin"} hideModerationStrip />
    </div>
  );
}
