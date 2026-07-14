import { useEffect, useState } from "react";
import api from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend } from "recharts";

export default function Reports() {
  const [d, setD] = useState(null);
  useEffect(() => { api.get("/reports/overview").then(r => setD(r.data)); }, []);
  const bp = d?.banner_proposals || {}; const tp = d?.tv_proposals || {};

  return (
    <div>
      <PageHeader eyebrow="Analytics" title="Global commercial activity" description="Operational reporting across the Independent Media Network — proposal volume, status, and network activity. Customer commercials remain confidential to representatives." />
      <div className="px-10 py-10 space-y-6">
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
          <Metric label="Pending review" value={d?.all_pending_review ?? "—"} tone="warning" />
          <Metric label="Banner approved" value={bp.approved ?? "—"} tone="positive" />
          <Metric label="TV approved" value={tp.approved ?? "—"} tone="positive" />
          <Metric label="Active reps" value={d?.total_reps_active ?? "—"} />
          <Metric label="Inventory products" value={d?.inventory_products_count ?? "—"} />
        </div>

        <div className="imh-card p-6">
          <div className="imh-eyebrow">Monthly activity</div>
          <div className="h-[340px] mt-4">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={d?.monthly_series || []}>
                <CartesianGrid stroke="#E4E4E1" vertical={false} />
                <XAxis dataKey="month" stroke="#52525B" fontSize={11} axisLine={{ stroke: "#E4E4E1" }} tickLine={false} />
                <YAxis stroke="#52525B" fontSize={11} axisLine={{ stroke: "#E4E4E1" }} tickLine={false} />
                <Tooltip contentStyle={{ borderRadius: 0, borderColor: "#0A0A0A" }} />
                <Legend />
                <Bar dataKey="banner_submitted" name="Banner submitted" fill="#0033A0" />
                <Bar dataKey="banner_approved"  name="Banner approved"  fill="#166534" />
                <Bar dataKey="tv_submitted"     name="TV submitted"     fill="#0A0A0A" />
                <Bar dataKey="tv_approved"      name="TV approved"      fill="#B45309" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="imh-card">
          <div className="px-6 py-4 border-b border-[#E4E4E1]">
            <div className="imh-eyebrow">Networks</div>
            <h3 className="font-editorial text-xl mt-1">Most-purchased networks (approved)</h3>
          </div>
          <div className="divide-y divide-[#E4E4E1]">
            {(d?.top_networks || []).map((n, i) => (
              <div key={n.network} className="px-6 py-3 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="font-mono-imh text-xs text-[#A1A1AA] w-6">{String(i+1).padStart(2, "0")}</span>
                  <span className="text-sm">{n.network}</span>
                </div>
                <span className="font-mono-imh text-sm">{n.approved} approved</span>
              </div>
            ))}
            {(!d?.top_networks || d.top_networks.length === 0) && <div className="px-6 py-10 text-center text-[#52525B]">No approved network activity yet.</div>}
          </div>
        </div>
      </div>
    </div>
  );
}

function Metric({ label, value, tone }) {
  const color = tone === "warning" ? "#B45309" : tone === "positive" ? "#166534" : "#0A0A0A";
  return (
    <div className="imh-card p-6">
      <div className="imh-eyebrow">{label}</div>
      <div className="imh-metric-number text-3xl mt-3" style={{ color }}>{value}</div>
    </div>
  );
}
