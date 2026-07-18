import { useEffect, useState } from "react";
import api from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend } from "recharts";

export default function RepReports() {
  const [d, setD] = useState(null);
  useEffect(() => { api.get("/reports/overview").then(r => setD(r.data)); }, []);
  const apps = d?.applications || {};
  const partners = d?.partner_submissions || {};

  return (
    <div>
      <PageHeader eyebrow="Analytics" title="Your Project Library activity"
                   description="Operational overview of your applications and project pitches. No revenue metrics — commercial dealings with your customer stay confidential." />
      <div className="px-10 py-10 space-y-6">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <Metric label="Applications · Submitted" value={apps.total ?? "—"} />
          <Metric label="Applications · Approved" value={apps.approved ?? "—"} sub={`${apps.submitted ?? 0} pending`} />
          <Metric label="Partner ideas · Submitted" value={partners.total ?? "—"} />
          <Metric label="Partner ideas · Approved" value={partners.approved ?? "—"} sub={`${partners.in_review ?? 0} in review`} />
        </div>

        <div className="imh-card p-6">
          <div className="imh-eyebrow">Monthly activity</div>
          <div className="h-[320px] mt-4">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={d?.monthly_series || []}>
                <CartesianGrid stroke="#E4E4E1" vertical={false} />
                <XAxis dataKey="month" stroke="#52525B" fontSize={11} axisLine={{ stroke: "#E4E4E1" }} tickLine={false} />
                <YAxis stroke="#52525B" fontSize={11} axisLine={{ stroke: "#E4E4E1" }} tickLine={false} />
                <Tooltip contentStyle={{ borderRadius: 0, borderColor: "#0A0A0A" }} />
                <Legend />
                <Bar dataKey="applications"          name="Applications submitted" fill="#0033A0" />
                <Bar dataKey="approved_applications" name="Applications approved"  fill="#166534" />
                <Bar dataKey="partner_submissions"   name="Partner ideas · in"     fill="#0A0A0A" />
                <Bar dataKey="partner_approved"      name="Partner ideas · approved" fill="#B45309" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="imh-card">
          <div className="px-6 py-4 border-b border-[#E4E4E1]">
            <div className="imh-eyebrow">Most-produced projects</div>
            <h3 className="font-editorial text-xl mt-1">Where the network is producing</h3>
          </div>
          <div className="divide-y divide-[#E4E4E1]">
            {(d?.top_projects || []).map((n, i) => (
              <div key={n.project} className="px-6 py-3 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="font-mono-imh text-xs text-[#A1A1AA] w-6">{String(i+1).padStart(2, "0")}</span>
                  <span className="text-sm">{n.project}</span>
                </div>
                <span className="font-mono-imh text-sm">{n.productions} approved</span>
              </div>
            ))}
            {(!d?.top_projects || d.top_projects.length === 0) && <div className="px-6 py-10 text-center text-[#52525B]">No approved productions yet.</div>}
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
      {sub && <div className="mt-2 text-xs text-[#52525B]">{sub}</div>}
    </div>
  );
}
