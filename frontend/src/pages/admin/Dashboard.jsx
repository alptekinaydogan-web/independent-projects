import { useEffect, useState } from "react";
import api from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import { usd, num } from "@/lib/constants";
import { useAuth } from "@/contexts/AuthContext";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { ArrowUpRight } from "lucide-react";
import { Link } from "react-router-dom";
import ActionableStrip from "@/components/ActionableStrip";

function Metric({ label, value, sub, testId }) {
  return (
    <div className="imh-card p-6" data-testid={testId}>
      <div className="imh-eyebrow">{label}</div>
      <div className="imh-metric-number text-3xl mt-3 text-[#0A0A0A]">{value}</div>
      {sub && <div className="mt-2 text-xs text-[#52525B]">{sub}</div>}
    </div>
  );
}

export default function AdminDashboard() {
  const { user } = useAuth();
  const [d, setD] = useState(null);

  useEffect(() => {
    api.get("/reports/overview").then(r => setD(r.data));
  }, []);

  return (
    <div>
      <PageHeader
        eyebrow="Administrator Overview"
        title={`Good day, ${user?.name?.split(" ")[0] || "Admin"}.`}
        description="Commercial activity across the entire Independent Media Network — banner campaigns and Independent TV sponsorships booked by our representatives."
      />
      <div className="px-10 py-10 grid grid-cols-12 gap-6">
        <div className="col-span-12">
          <ActionableStrip base="/admin" />
        </div>
        <div className="col-span-12 grid grid-cols-2 lg:grid-cols-4 gap-4">
          <Metric label="Client Revenue · Banners" value={d ? usd(d.campaigns_client_revenue_usd) : "—"} sub={d ? `${num(d.campaign_count)} campaigns` : ""} testId="metric-banner-rev" />
          <Metric label="Client Revenue · TV" value={d ? usd(d.tv_client_revenue_usd) : "—"} sub={d ? `${num(d.sponsorship_count)} sponsorships` : ""} testId="metric-tv-rev" />
          <Metric label="Active Representatives" value={d ? num(d.total_reps_active) : "—"} sub="Licensed agencies" testId="metric-reps" />
          <Metric label="Proposals Pending" value={d ? num(d.proposals_pending) : "—"} sub="Awaiting decision" testId="metric-proposals" />
        </div>

        <div className="col-span-12 lg:col-span-8 imh-card p-6">
          <div className="flex items-center justify-between">
            <div>
              <div className="imh-eyebrow">Revenue Timeline</div>
              <h3 className="font-editorial text-xl mt-1">Monthly client revenue (USD)</h3>
            </div>
            <div className="text-[11px] text-[#52525B] font-mono-imh">LAST 6 MONTHS</div>
          </div>
          <div className="h-[280px] mt-6">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={d?.monthly_series || []}>
                <CartesianGrid stroke="#E4E4E1" vertical={false} />
                <XAxis dataKey="month" stroke="#52525B" fontSize={11} tickLine={false} axisLine={{ stroke: "#E4E4E1" }} />
                <YAxis stroke="#52525B" fontSize={11} tickLine={false} axisLine={{ stroke: "#E4E4E1" }} />
                <Tooltip contentStyle={{ borderRadius: 0, borderColor: "#0A0A0A" }} />
                <Bar dataKey="campaigns_usd" fill="#0033A0" name="Banners" />
                <Bar dataKey="tv_usd" fill="#0A0A0A" name="TV" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="col-span-12 lg:col-span-4 imh-card p-6">
          <div className="imh-eyebrow">Geographic reach</div>
          <h3 className="font-editorial text-xl mt-1">Top countries</h3>
          <div className="mt-6 divide-y divide-[#E4E4E1]">
            {(d?.top_countries || []).slice(0, 8).map((c, i) => (
              <div key={c.country} className="flex items-center justify-between py-3">
                <div className="flex items-center gap-3">
                  <span className="font-mono-imh text-xs text-[#A1A1AA] w-6">{String(i+1).padStart(2, "0")}</span>
                  <span className="text-sm">{c.country}</span>
                </div>
                <span className="font-mono-imh text-sm">{usd(c.internal_usd)}</span>
              </div>
            ))}
            {(!d?.top_countries || d.top_countries.length === 0) && (
              <div className="py-6 text-sm text-[#52525B]">No campaigns booked yet.</div>
            )}
          </div>
        </div>

        <div className="col-span-12 grid grid-cols-1 md:grid-cols-3 gap-4">
          <QuickLink to="/admin/tv-projects" title="Publish a TV project" desc="Add a new documentary or interview series to the sponsorship catalog." />
          <QuickLink to="/admin/proposals" title="Review proposals" desc="Approve promising ideas submitted by representatives worldwide." />
          <QuickLink to="/admin/banner-inventory" title="Adjust inventory" desc="Update CPM pricing per country across the whole network." />
        </div>
      </div>
    </div>
  );
}

function QuickLink({ to, title, desc }) {
  return (
    <Link to={to} data-testid={`quick-${to.split("/").pop()}`}
      className="imh-card p-6 group hover:border-[#0A0A0A] transition-colors">
      <div className="flex items-start justify-between">
        <h4 className="font-editorial text-xl">{title}</h4>
        <ArrowUpRight size={18} className="text-[#0033A0] group-hover:-translate-y-0.5 group-hover:translate-x-0.5" style={{ transition: "transform 160ms ease" }} />
      </div>
      <p className="mt-3 text-sm text-[#52525B]">{desc}</p>
    </Link>
  );
}
