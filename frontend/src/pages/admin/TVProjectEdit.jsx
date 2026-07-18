import { useParams } from "react-router-dom";
import PageHeader from "@/components/PageHeader";
import ProjectEditor from "@/components/project/ProjectEditor";

/**
 * Admin project host — the SAME ProjectEditor used by Country Partners.
 * The editor renders admin-only moderation controls (Approve / Reject /
 * Revise / Publish / Feature / Archive) based on the current user's role.
 */
export default function TVProjectEdit() {
  const { id } = useParams();
  return (
    <div>
      <PageHeader eyebrow="Project Library" title={id ? "Edit project" : "New project"}
                   description="One editor for the whole platform. Reps use it to draft submissions, admins use it to publish official projects, and reviewers use it to moderate partner submissions in place." />
      <ProjectEditor projectId={id} mode={id ? "edit" : "create-admin"} />
    </div>
  );
}
