import { useEffect, useState } from "react";
import api from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import { usd, num } from "@/lib/constants";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend } from "recharts";

export default function RepReports() {
  const [d, setD] = useState(null);
  useEffect(() => { api.get("/reports/overview").then(r => setD(r.data)); }, []);
  return (
    <div>
      <PageHeader eyebrow="Analytics" title="Your reports" description="A commercial pulse of your activity on Independent Media Hub." />
      <div className="px-10 py-10 space-y-6">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <Metric label="Banner revenue" value={d ? usd(d.campaigns_client_revenue_usd) : "—"} sub={`${num(d?.campaign_count || 0)} campaigns`} />
          <Metric label="Banner margin" value={d ? usd(d.campaigns_margin_usd) : "—"} sub="Client price − internal" />
          <Metric label="TV revenue" value={d ? usd(d.tv_client_revenue_usd) : "—"} sub={`${num(d?.sponsorship_count || 0)} sponsorships`} />
          <Metric label="TV margin" value={d ? usd(d.tv_margin_usd) : "—"} sub="Client price − internal" />
        </div>
        <div className="imh-card p-6">
          <div className="imh-eyebrow">Monthly performance</div>
          <div className="h-[320px] mt-4">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={d?.monthly_series || []}>
                <CartesianGrid stroke="#E4E4E1" vertical={false} />
                <XAxis dataKey="month" stroke="#52525B" fontSize={11} axisLine={{ stroke: "#E4E4E1" }} tickLine={false} />
                <YAxis stroke="#52525B" fontSize={11} axisLine={{ stroke: "#E4E4E1" }} tickLine={false} />
                <Tooltip contentStyle={{ borderRadius: 0, borderColor: "#0A0A0A" }} />
                <Legend />
                <Line dataKey="campaigns_usd" name="Banners" stroke="#0033A0" strokeWidth={2} />
                <Line dataKey="tv_usd" name="TV" stroke="#0A0A0A" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}
function Metric({ label, value, sub }) {
  return (
    <div className="imh-card p-6">
      <div className="imh-eyebrow">{label}</div>
      <div className="imh-metric-number text-3xl mt-3">{value}</div>
      <div className="mt-2 text-xs text-[#52525B]">{sub}</div>
    </div>
  );
}
