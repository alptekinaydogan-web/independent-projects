import { useEffect, useMemo, useState } from "react";
import api from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend } from "recharts";
import { Download, Archive } from "lucide-react";

const currentYm = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
};

export default function Reports() {
  const [d, setD] = useState(null);
  const [month, setMonth] = useState(currentYm());
  const [kind, setKind] = useState("all");
  const [includeArchived, setIncludeArchived] = useState(true);
  const [downloading, setDownloading] = useState(false);

  useEffect(() => { api.get("/reports/overview").then(r => setD(r.data)); }, []);
  const bp = d?.banner_proposals || {}; const tp = d?.tv_proposals || {};

  const monthLabel = useMemo(() => {
    if (!month) return "All time";
    const [y, m] = month.split("-");
    return new Date(Number(y), Number(m) - 1, 1).toLocaleString(undefined, { month: "long", year: "numeric" });
  }, [month]);

  const downloadCsv = async () => {
    setDownloading(true);
    try {
      const params = new URLSearchParams();
      if (month) params.set("month", month);
      params.set("kind", kind);
      params.set("include_archived", includeArchived ? "true" : "false");
      const r = await api.get(`/reports/proposals/export.csv?${params.toString()}`, {
        responseType: "blob",
      });
      const blob = new Blob([r.data], { type: "text/csv" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `imh-proposals-${kind}-${month || "all"}.csv`;
      document.body.appendChild(a); a.click(); a.remove();
      URL.revokeObjectURL(url);
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div>
      <PageHeader eyebrow="Analytics" title="Global commercial activity"
                   description="Operational reporting across the Independent Media Network — proposal volume, status, lifecycle, and network activity. Customer commercials remain confidential to representatives." />
      <div className="px-10 py-10 space-y-6">
        <div className="grid grid-cols-2 lg:grid-cols-6 gap-4">
          <Metric label="Pending review" value={d?.all_pending_review ?? "—"} tone="warning" />
          <Metric label="Banner approved" value={bp.approved ?? "—"} tone="positive" />
          <Metric label="TV approved" value={tp.approved ?? "—"} tone="positive" />
          <Metric label="Revised (open)" value={(bp.revised ?? 0) + (tp.revised ?? 0)} />
          <Metric label="Active reps" value={d?.total_reps_active ?? "—"} />
          <Metric label="Archived" value={d?.archived_proposals_count ?? "—"} tone="muted" icon={Archive} />
        </div>

        <div className="imh-card p-6" data-testid="csv-export-panel">
          <div className="flex items-baseline justify-between gap-4 flex-wrap">
            <div>
              <div className="imh-eyebrow">Monthly export</div>
              <h3 className="font-editorial text-xl mt-1">CSV — {monthLabel}</h3>
              <p className="text-xs text-[#52525B] mt-1 max-w-lg">Extended reporting: every proposal in scope with lifecycle status, offer amount, representative feedback, internal notes, parent proposal (revision chain) and decision actor.</p>
            </div>
            <div className="flex items-end gap-3 flex-wrap">
              <label className="flex flex-col text-[10px] uppercase tracking-widest text-[#52525B]">
                Month
                <input type="month" value={month} onChange={e => setMonth(e.target.value)} data-testid="csv-month"
                       className="mt-1 h-10 border border-[#E4E4E1] rounded-none px-3 text-sm text-[#0A0A0A]" />
              </label>
              <label className="flex flex-col text-[10px] uppercase tracking-widest text-[#52525B]">
                Kind
                <select value={kind} onChange={e => setKind(e.target.value)} data-testid="csv-kind"
                        className="mt-1 h-10 border border-[#E4E4E1] rounded-none px-3 text-sm text-[#0A0A0A] bg-white">
                  <option value="all">All (Banner + TV)</option>
                  <option value="banner">Banner only</option>
                  <option value="tv">TV sponsorships only</option>
                </select>
              </label>
              <label className="flex items-center gap-2 text-[11px] uppercase tracking-widest text-[#52525B] mt-1" data-testid="csv-archived">
                <input type="checkbox" checked={includeArchived}
                       onChange={e => setIncludeArchived(e.target.checked)} />
                Include archived
              </label>
              <button onClick={() => setMonth("")} className="h-10 px-3 border border-[#E4E4E1] hover:border-[#0A0A0A] text-[11px] uppercase tracking-widest text-[#52525B]"
                      style={{ transition: "border-color 120ms" }} data-testid="csv-alltime">All time</button>
              <Button onClick={downloadCsv} disabled={downloading} data-testid="csv-download"
                      className="rounded-none h-10 bg-[#0033A0] hover:bg-[#002277] text-white">
                <Download size={14} className="mr-2" /> {downloading ? "Preparing…" : "Download CSV"}
              </Button>
            </div>
          </div>
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

function Metric({ label, value, tone, icon: Icon }) {
  const color = tone === "warning" ? "#B45309" : tone === "positive" ? "#166534" : tone === "muted" ? "#52525B" : "#0A0A0A";
  return (
    <div className="imh-card p-6">
      <div className="imh-eyebrow flex items-center gap-1">{Icon && <Icon size={11} strokeWidth={1.5} />} {label}</div>
      <div className="imh-metric-number text-3xl mt-3" style={{ color }}>{value}</div>
    </div>
  );
}
