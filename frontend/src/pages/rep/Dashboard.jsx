import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import { useAuth } from "@/contexts/AuthContext";
import ActionableStrip from "@/components/ActionableStrip";
import { ArrowUpRight, Radio, FilmIcon, Send } from "lucide-react";

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
  const [tv, setTv] = useState([]);
  useEffect(() => {
    api.get("/reports/overview").then(r => setD(r.data));
    api.get("/tv-projects").then(r => setTv(r.data.slice(0, 3)));
  }, []);

  const bp = d?.banner_proposals || {};
  const tp = d?.tv_proposals || {};

  return (
    <div>
      <PageHeader
        eyebrow={`${user?.agency_name || "Independent Media Hub"} · Representative`}
        title={`Welcome back, ${user?.name?.split(" ")[0] || ""}.`}
        description="Browse premium media inventory, submit confidential commercial proposals, and track their review across the network."
      />
      <div className="px-10 py-10 space-y-10">
        <ActionableStrip base="/rep" />

        <div>
          <div className="imh-eyebrow mb-3">Your commercial proposals</div>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <Metric testId="metric-banner-pending" label="Banner · Pending review" value={bp.pending_review ?? "—"} sub="Awaiting decision" tone={bp.pending_review > 0 ? "warning" : undefined} />
            <Metric testId="metric-banner-approved" label="Banner · Approved" value={bp.approved ?? "—"} sub="Live or scheduled" tone="positive" />
            <Metric testId="metric-tv-pending" label="TV · Pending review" value={tp.pending_review ?? "—"} sub="Awaiting decision" tone={tp.pending_review > 0 ? "warning" : undefined} />
            <Metric testId="metric-tv-approved" label="TV · Approved" value={tp.approved ?? "—"} sub="Confirmed sponsorships" tone="positive" />
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <ActionCard to="/rep/banners/new" icon={Radio} title="Submit a banner proposal" desc="Browse inventory across the Global and thematic networks. Propose an offer to Independent Media Network." />
          <ActionCard to="/rep/tv" icon={FilmIcon} title="Browse TV sponsorships" desc="Read the investment page of original productions and submit a sponsorship proposal." />
          <ActionCard to="/rep/proposals/new" icon={Send} title="Pitch a new production" desc="Have a great documentary or interview format? Submit it to Independent TV." />
        </div>

        <div>
          <div className="flex items-baseline justify-between mb-4">
            <div>
              <div className="imh-eyebrow">Now available</div>
              <h3 className="font-editorial text-2xl mt-1">Featured Independent TV productions</h3>
            </div>
            <Link to="/rep/tv" className="text-sm text-[#0033A0] hover:underline">See all →</Link>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {tv.map(p => (
              <Link key={p.id} to={`/rep/tv/${p.id}`} className="imh-card group overflow-hidden hover:border-[#0A0A0A]" style={{ transition: "border-color 160ms ease" }}>
                <div className="aspect-[16/10] bg-[#0A1128] overflow-hidden">
                  {p.hero_image_url && <img src={p.hero_image_url} alt="" className="w-full h-full object-cover group-hover:scale-[1.02]" style={{ transition: "transform 400ms ease" }} />}
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
    <Link to={to} className="imh-card p-6 group hover:border-[#0A0A0A]" style={{ transition: "border-color 160ms ease" }} data-testid={`rep-action-${to.split('/').pop()}`}>
      <div className="flex items-start justify-between">
        <div className="w-10 h-10 border border-[#0A0A0A] flex items-center justify-center"><Icon size={18} strokeWidth={1.5} /></div>
        <ArrowUpRight size={18} className="text-[#0033A0]" />
      </div>
      <h4 className="font-editorial text-xl mt-4">{title}</h4>
      <p className="text-sm text-[#52525B] mt-2">{desc}</p>
    </Link>
  );
}
