import { useEffect, useState } from "react";
import api from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import { usd, num } from "@/lib/constants";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend } from "recharts";

export default function Reports() {
  const [d, setD] = useState(null);
  const [reps, setReps] = useState([]);
  const [campaigns, setCampaigns] = useState([]);
  const [sp, setSp] = useState([]);

  useEffect(() => {
    api.get("/reports/overview").then(r => setD(r.data));
    api.get("/admin/representatives").then(r => setReps(r.data));
    api.get("/campaigns").then(r => setCampaigns(r.data));
    api.get("/sponsorships").then(r => setSp(r.data));
  }, []);

  const byRep = {};
  for (const c of campaigns) { (byRep[c.rep_id] ||= { name: c.rep_name, agency: c.agency_name, campaigns: 0, banner_rev: 0, tv_rev: 0 }).campaigns += 1; byRep[c.rep_id].banner_rev += c.client_total_price_usd || 0; }
  for (const s of sp) { (byRep[s.rep_id] ||= { name: s.rep_name, agency: s.agency_name, campaigns: 0, banner_rev: 0, tv_rev: 0 }).tv_rev += s.client_total_price_usd || 0; }
  const rows = Object.values(byRep).sort((a, b) => (b.banner_rev + b.tv_rev) - (a.banner_rev + a.tv_rev));

  return (
    <div>
      <PageHeader eyebrow="Analytics" title="Global Reports" description="A single view of Independent Media Hub's commercial activity across the network." />
      <div className="px-10 py-10 space-y-6">
        <div className="imh-card p-6">
          <div className="imh-eyebrow">Revenue trajectory</div>
          <h3 className="font-editorial text-xl mt-1">Monthly performance (client USD)</h3>
          <div className="h-[320px] mt-6">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={d?.monthly_series || []}>
                <CartesianGrid stroke="#E4E4E1" vertical={false} />
                <XAxis dataKey="month" stroke="#52525B" fontSize={11} tickLine={false} axisLine={{ stroke: "#E4E4E1" }} />
                <YAxis stroke="#52525B" fontSize={11} tickLine={false} axisLine={{ stroke: "#E4E4E1" }} />
                <Tooltip contentStyle={{ borderRadius: 0, borderColor: "#0A0A0A" }} />
                <Legend />
                <Line dataKey="campaigns_usd" name="Banners" stroke="#0033A0" strokeWidth={2} dot={{ r: 3 }} />
                <Line dataKey="tv_usd" name="TV" stroke="#0A0A0A" strokeWidth={2} dot={{ r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="imh-card">
          <div className="px-6 py-4 border-b border-[#E4E4E1]">
            <div className="imh-eyebrow">Network</div>
            <h3 className="font-editorial text-xl mt-1">Performance by representative</h3>
          </div>
          <table className="w-full text-sm" data-testid="reps-performance-table">
            <thead>
              <tr className="text-left border-b border-[#E4E4E1] bg-[#F9F9F6]">
                <Th>Agency</Th><Th>Representative</Th><Th className="text-right">Campaigns</Th>
                <Th className="text-right">Banner revenue</Th><Th className="text-right">TV revenue</Th><Th className="text-right">Total</Th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={i} className="border-b border-[#E4E4E1] last:border-b-0">
                  <Td className="font-editorial text-base">{r.agency}</Td>
                  <Td>{r.name}</Td>
                  <Td className="text-right font-mono-imh">{num(r.campaigns)}</Td>
                  <Td className="text-right font-mono-imh">{usd(r.banner_rev)}</Td>
                  <Td className="text-right font-mono-imh">{usd(r.tv_rev)}</Td>
                  <Td className="text-right font-mono-imh font-medium">{usd(r.banner_rev + r.tv_rev)}</Td>
                </tr>
              ))}
              {rows.length === 0 && <tr><Td colSpan={6} className="text-center py-10 text-[#52525B]">No commercial activity yet.</Td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
const Th = ({ children, className = "" }) => <th className={`px-6 py-4 text-[11px] uppercase tracking-widest text-[#52525B] font-medium ${className}`}>{children}</th>;
const Td = ({ children, className = "", colSpan }) => <td colSpan={colSpan} className={`px-6 py-4 text-[#0A0A0A] ${className}`}>{children}</td>;
