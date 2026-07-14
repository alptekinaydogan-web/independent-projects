import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { usd } from "@/lib/constants";
import { Plus } from "lucide-react";

export default function Campaigns() {
  const [items, setItems] = useState([]);
  useEffect(() => { api.get("/campaigns").then(r => setItems(r.data)); }, []);
  return (
    <div>
      <PageHeader eyebrow="Banners" title="Your campaigns" description="Every banner campaign you've booked across the Independent Media Network."
        actions={
          <Link to="/rep/banners/new">
            <Button data-testid="new-campaign-btn" className="rounded-none h-10 bg-[#0033A0] hover:bg-[#002277]"><Plus size={16} className="mr-2" />New campaign</Button>
          </Link>
        } />
      <div className="px-10 py-10">
        <div className="imh-card overflow-hidden">
          <table className="w-full text-sm" data-testid="campaigns-table">
            <thead>
              <tr className="text-left border-b border-[#E4E4E1] bg-[#F9F9F6]">
                <Th>Campaign</Th><Th>Client</Th><Th>Countries</Th><Th className="text-right">Impressions</Th>
                <Th className="text-right">Internal</Th><Th className="text-right">Client price</Th><Th className="text-right">Margin</Th>
              </tr>
            </thead>
            <tbody>
              {items.map(c => (
                <tr key={c.id} className="border-b border-[#E4E4E1] last:border-b-0" data-testid={`campaign-${c.id}`}>
                  <Td className="font-editorial">{c.campaign_name}</Td>
                  <Td>{c.client_name}</Td>
                  <Td className="font-mono-imh text-xs">{c.country_codes?.length} · {c.country_codes?.slice(0, 4).join(", ")}{c.country_codes?.length > 4 ? "…" : ""}</Td>
                  <Td className="text-right font-mono-imh">{Number(c.impressions * (c.country_codes?.length || 1)).toLocaleString()}</Td>
                  <Td className="text-right font-mono-imh">{usd(c.internal_cost_usd)}</Td>
                  <Td className="text-right font-mono-imh">{usd(c.client_total_price_usd)}</Td>
                  <Td className="text-right font-mono-imh" style={{ color: c.margin_usd >= 0 ? "#166534" : "#991B1B" }}>{usd(c.margin_usd)}</Td>
                </tr>
              ))}
              {items.length === 0 && (
                <tr><Td colSpan={7} className="text-center py-16 text-[#52525B]">No campaigns yet. <Link to="/rep/banners/new" className="text-[#0033A0] underline">Create your first</Link>.</Td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
const Th = ({ children, className = "" }) => <th className={`px-6 py-4 text-[11px] uppercase tracking-widest text-[#52525B] font-medium ${className}`}>{children}</th>;
const Td = ({ children, className = "", colSpan, style }) => <td colSpan={colSpan} style={style} className={`px-6 py-4 text-[#0A0A0A] ${className}`}>{children}</td>;
