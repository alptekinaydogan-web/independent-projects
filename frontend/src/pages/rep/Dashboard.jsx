import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import { useAuth } from "@/contexts/AuthContext";
import ActionableStrip from "@/components/ActionableStrip";
import { ArrowUpRight, FilmIcon, Send, Sparkles } from "lucide-react";

function Metric({ label, value, sub, testId, tone }) {
  const color = tone === "warning" ? "#B45309" : tone === "positive" ? "#166534" : tone === "danger" ? "#991B1B" : "#0A0A0A";
  return (
    <div className="imh-card p-6" data-testid={testId}>
      <div className="imh-eyebrow">{label}</div>
      <div className="imh-metric-number text-3xl mt-3" style={{ color }}>{value}</div>
      {sub && <div className="mt-2 text-xs text-[#52525B]">{sub}</div>}
    </div>
  );
}

export default function RepDashboard() {
  const { user } = useAuth();
  const [d, setD] = useState(null);
  const [featured, setFeatured] = useState([]);
  useEffect(() => {
    api.get("/reports/overview").then(r => setD(r.data));
    api.get("/tv-projects").then(r => setFeatured(r.data.slice(0, 3)));
  }, []);

  const apps = d?.applications || {};
  const partners = d?.partner_submissions || {};

  return (
    <div>
      <PageHeader
        eyebrow={`${user?.agency_name || "Independent Projects"} · Country Partner`}
        title={`Welcome back, ${user?.name?.split(" ")[0] || ""}.`}
        description="Explore the global Project Library, apply to produce in your territory, and submit new project ideas to Independent Media Network."
      />
      <div className="px-10 py-10 space-y-10">
        <ActionableStrip base="/rep" />

        <div>
          <div className="imh-eyebrow mb-3">Your activity</div>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <Metric testId="metric-apps-submitted" label="Applications · Submitted" value={apps.submitted ?? "—"}
                     sub="Awaiting review" tone={apps.submitted > 0 ? "warning" : undefined} />
            <Metric testId="metric-apps-approved" label="Productions · Approved" value={apps.approved ?? "—"}
                     sub="Green-lit in your territory" tone="positive" />
            <Metric testId="metric-partner-review" label="Partner ideas · In review" value={partners.in_review ?? "—"}
                     sub="Concepts pitched to the network" tone={partners.in_review > 0 ? "warning" : undefined} />
            <Metric testId="metric-partner-approved" label="Partner ideas · Approved" value={partners.approved ?? "—"}
                     sub="Adopted by the network" tone="positive" />
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <ActionCard to="/rep/tv" icon={FilmIcon} title="Browse the Project Library"
                       desc="Read the modular package of every official project and apply to produce the ones you can bring to market." />
          <ActionCard to="/rep/proposals/new" icon={Send} title="Submit a project idea"
                       desc="Pitch a documentary, interview series or format your country is ready to produce." />
          <ActionCard to="/rep/reports" icon={Sparkles} title="Track your activity"
                       desc="See where your applications stand, and what has been approved for production in your territory." />
        </div>

        <div>
          <div className="flex items-baseline justify-between mb-4">
            <div>
              <div className="imh-eyebrow">Now available</div>
              <h3 className="font-editorial text-2xl mt-1">Featured projects in the library</h3>
            </div>
            <Link to="/rep/tv" className="text-sm text-[#0033A0] hover:underline">See all →</Link>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {featured.map(p => (
              <Link key={p.id} to={`/rep/tv/${p.id}`} className="imh-card group overflow-hidden hover:border-[#0A0A0A]"
                    style={{ transition: "border-color 160ms ease" }}
                    data-testid={`featured-project-${p.id}`}>
                <div className="aspect-[16/10] bg-[#0A1128] overflow-hidden">
                  {p.hero_image_url && <img src={p.hero_image_url} alt="" className="w-full h-full object-cover group-hover:scale-[1.02]"
                                              style={{ transition: "transform 400ms ease" }} />}
                </div>
                <div className="p-5">
                  <div className="imh-eyebrow">{p.total_episodes} EPISODES</div>
                  <h4 className="font-editorial text-xl mt-2">{p.title}</h4>
                  <p className="text-sm text-[#52525B] line-clamp-2 mt-2">{p.tagline}</p>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function ActionCard({ to, icon: Icon, title, desc }) {
  return (
    <Link to={to} className="imh-card p-6 group hover:border-[#0A0A0A]"
          style={{ transition: "border-color 160ms ease" }}
          data-testid={`rep-action-${to.split('/').pop()}`}>
      <div className="flex items-start justify-between">
        <div className="w-10 h-10 border border-[#0A0A0A] flex items-center justify-center"><Icon size={18} strokeWidth={1.5} /></div>
        <ArrowUpRight size={18} className="text-[#0033A0]" />
      </div>
      <h4 className="font-editorial text-xl mt-4">{title}</h4>
      <p className="text-sm text-[#52525B] mt-2">{desc}</p>
    </Link>
  );
}
