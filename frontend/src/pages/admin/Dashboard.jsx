import { useEffect, useState } from "react";
import api from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import { useAuth } from "@/contexts/AuthContext";
import ActionableStrip from "@/components/ActionableStrip";
import { Link } from "react-router-dom";
import { ArrowUpRight } from "lucide-react";

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

export default function AdminDashboard() {
  const { user } = useAuth();
  const [d, setD] = useState(null);

  useEffect(() => { api.get("/reports/overview").then(r => setD(r.data)); }, []);

  const bp = d?.banner_proposals || {};
  const tp = d?.tv_proposals || {};

  return (
    <div>
      <PageHeader
        eyebrow="Administrator Overview"
        title={`Good day, ${user?.name?.split(" ")[0] || "Admin"}.`}
        description="Commercial activity across Independent Media Network. Review commercial proposals from representatives, monitor approved inventory, and manage editorial concepts."
      />
      <div className="px-10 py-10 space-y-8">
        <ActionableStrip base="/admin" />

        <div>
          <div className="imh-eyebrow mb-3">Proposals awaiting your decision</div>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <Metric testId="metric-all-pending" label="All pending review" value={d?.all_pending_review ?? "—"} sub="Banner + TV proposals" tone={d?.all_pending_review > 0 ? "warning" : undefined} />
            <Metric testId="metric-banner-pending" label="Banner pending" value={bp.pending_review ?? "—"} sub="Confidential offers" tone={bp.pending_review > 0 ? "warning" : undefined} />
            <Metric testId="metric-tv-pending" label="TV pending" value={tp.pending_review ?? "—"} sub="Sponsorship offers" tone={tp.pending_review > 0 ? "warning" : undefined} />
            <Metric testId="metric-reps-active" label="Active representatives" value={d?.total_reps_active ?? "—"} sub="Licensed agencies" />
          </div>
        </div>

        <div>
          <div className="imh-eyebrow mb-3">Approved commercial activity</div>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <Metric testId="metric-banner-approved" label="Approved banner proposals" value={bp.approved ?? "—"} tone="positive" />
            <Metric testId="metric-tv-approved" label="Approved sponsorships" value={tp.approved ?? "—"} tone="positive" />
            <Metric testId="metric-banner-total" label="Total banner proposals" value={bp.total ?? "—"} sub="All statuses" />
            <Metric testId="metric-tv-total" label="Total TV proposals" value={tp.total ?? "—"} sub="All statuses" />
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <QuickLink to="/admin/proposals-review" title="Review pending proposals" desc="Approve, request revision, or reject commercial proposals waiting for your decision." />
          <QuickLink to="/admin/tv-projects" title="Publish a TV project" desc="Add or freeze productions in the sponsorship catalog." />
          <QuickLink to="/admin/inventory" title="Inspect inventory catalog" desc="See the network×position products currently offered to representatives." />
        </div>
      </div>
    </div>
  );
}

function QuickLink({ to, title, desc }) {
  return (
    <Link to={to} className="imh-card p-6 group hover:border-[#0A0A0A]" style={{ transition: "border-color 160ms ease" }}>
      <div className="flex items-start justify-between">
        <h4 className="font-editorial text-xl">{title}</h4>
        <ArrowUpRight size={18} className="text-[#0033A0] group-hover:-translate-y-0.5 group-hover:translate-x-0.5" style={{ transition: "transform 160ms ease" }} />
      </div>
      <p className="mt-3 text-sm text-[#52525B]">{desc}</p>
    </Link>
  );
}
