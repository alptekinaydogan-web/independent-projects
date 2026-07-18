import { useParams } from "react-router-dom";
import PageHeader from "@/components/PageHeader";
import ProjectEditor from "@/components/project/ProjectEditor";

/**
 * Rep project host — same ProjectEditor as admins use. The editor
 * automatically hides moderation controls for non-admin users and locks
 * the form once the project has been submitted for review (until an
 * admin requests revisions).
 */
export default function ProjectDraft() {
  const { id } = useParams();
  return (
    <div>
      <PageHeader eyebrow="Country Partner Editor" title={id ? "Edit your project" : "New project submission"}
                   description="The exact same editor Independent Media Network administrators use to publish official projects. Save your work as a draft and submit it for review when it is ready." />
      <ProjectEditor projectId={id} mode={id ? "edit" : "create-partner"} />
    </div>
  );
}
