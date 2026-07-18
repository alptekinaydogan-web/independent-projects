import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import api from "@/lib/api";
import {
  ProjectHero,
  ProjectOverview,
  ProjectAudience,
  ProjectFormat,
  ProjectSponsorship,
  ProjectTechnicalSpecs,
  ProjectBrandGuidelines,
  ProjectDownloadCenter,
  ProjectApplyToProduce,
} from "@/components/project/ProjectBlocks";

/**
 * TVProjectDetail — modular project page for the "TV Formats" category.
 *
 * The page is composed entirely of reusable blocks from
 * `components/project/ProjectBlocks.jsx`. Future categories (Events,
 * Podcasts, Documentaries, Research Projects, Co-Productions) reuse the
 * same blocks and add or omit category-specific sections as needed.
 */
export default function TVProjectDetail() {
  const { id } = useParams();
  const [project, setProject] = useState(null);
  const [category, setCategory] = useState(null);
  const [applyOpen, setApplyOpen] = useState(false);
  const [applicationStatus, setApplicationStatus] = useState(null);

  const reload = () => {
    api.get(`/tv-projects/${id}`).then(r => {
      setProject(r.data);
      const slug = r.data.category_slug || r.data.category;
      if (slug) api.get(`/categories/${slug}`).then(c => setCategory(c.data)).catch(() => {});
      setApplicationStatus(r.data.my_application?.status || null);
    });
  };

  useEffect(() => { reload(); /* eslint-disable-next-line */ }, [id]);

  if (!project) return <div className="p-10 imh-eyebrow" data-testid="project-loading">Loading…</div>;

  return (
    <div>
      <ProjectHero project={project} category={category}
                    applicationStatus={applicationStatus}
                    onApplyClick={() => setApplyOpen(true)} />

      <div className="px-10 py-14 space-y-14 max-w-6xl">
        <ProjectOverview project={project} />
        <ProjectAudience project={project} />
        <ProjectFormat project={project} />
        <ProjectSponsorship project={project} />
        <ProjectTechnicalSpecs project={project} />
        <ProjectBrandGuidelines project={project} />
        <ProjectDownloadCenter project={project} />
      </div>

      <ProjectApplyToProduce open={applyOpen} onOpenChange={setApplyOpen}
                              project={project}
                              onSubmitted={reload} />
    </div>
  );
}
