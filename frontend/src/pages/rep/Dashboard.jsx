import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import { usd, num } from "@/lib/constants";
import { useAuth } from "@/contexts/AuthContext";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { ArrowUpRight, Radio, FilmIcon, Send } from "lucide-react";
import ActionableStrip from "@/components/ActionableStrip";

function Metric({ label, value, sub, testId }) {
  return (
    <div className="imh-card p-6" data-testid={testId}>
      <div className="imh-eyebrow">{label}</div>
      <div className="imh-metric-number text-3xl mt-3">{value}</div>
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

  return (
    <div>
      <PageHeader
        eyebrow={`${user?.agency_name || "Independent Media Hub"} · Representative`}
        title={`Welcome back, ${user?.name?.split(" ")[0] || ""}.`}
        description="Two commercial modules. One platform. Sell across the Independent Media Network from a single workspace."
      />
      <div className="px-10 py-10 space-y-10">
        <ActionableStrip base="/rep" />
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <Metric label="Your Banner Revenue" value={d ? usd(d.campaigns_client_revenue_usd) : "—"} sub={d ? `${num(d.campaign_count)} campaigns` : ""} testId="rep-metric-banner" />
          <Metric label="Your TV Revenue" value={d ? usd(d.tv_client_revenue_usd) : "—"} sub={d ? `${num(d.sponsorship_count)} sponsorships` : ""} testId="rep-metric-tv" />
          <Metric label="Margin · Banners" value={d ? usd(d.campaigns_margin_usd) : "—"} sub="Revenue minus internal cost" testId="rep-metric-banner-margin" />
          <Metric label="Margin · TV" value={d ? usd(d.tv_margin_usd) : "—"} sub="Revenue minus internal cost" testId="rep-metric-tv-margin" />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <ActionCard to="/rep/banners/new" icon={Radio} title="Build a banner campaign" desc="Target one country or the entire network. Configure impressions, set your selling price." />
          <ActionCard to="/rep/tv" icon={FilmIcon} title="Browse TV sponsorships" desc="Read the investment pages of our original productions and sponsor episodes." />
          <ActionCard to="/rep/proposals/new" icon={Send} title="Submit a project idea" desc="Have a great documentary or interview format? Pitch it to Independent TV." />
        </div>

        <div className="imh-card p-6">
          <div className="flex items-center justify-between">
            <div>
              <div className="imh-eyebrow">Your commercial timeline</div>
              <h3 className="font-editorial text-xl mt-1">Monthly client revenue</h3>
            </div>
          </div>
          <div className="h-[240px] mt-4">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={d?.monthly_series || []}>
                <CartesianGrid stroke="#E4E4E1" vertical={false} />
                <XAxis dataKey="month" stroke="#52525B" fontSize={11} tickLine={false} axisLine={{ stroke: "#E4E4E1" }} />
                <YAxis stroke="#52525B" fontSize={11} tickLine={false} axisLine={{ stroke: "#E4E4E1" }} />
                <Tooltip contentStyle={{ borderRadius: 0, borderColor: "#0A0A0A" }} />
                <Line dataKey="campaigns_usd" name="Banners" stroke="#0033A0" strokeWidth={2} dot={{ r: 3 }} />
                <Line dataKey="tv_usd" name="TV" stroke="#0A0A0A" strokeWidth={2} dot={{ r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div>
          <div className="flex items-baseline justify-between mb-4">
            <div>
              <div className="imh-eyebrow">Now sponsoring</div>
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
                  <div className="imh-eyebrow">{p.total_episodes} EP · {usd(p.price_per_episode_usd)}/ep</div>
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
