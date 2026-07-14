import { useEffect, useState } from "react";
import api from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import { usd } from "@/lib/constants";

export default function Sponsorships() {
  const [items, setItems] = useState([]);
  useEffect(() => { api.get("/sponsorships").then(r => setItems(r.data)); }, []);
  return (
    <div>
      <PageHeader eyebrow="Independent TV" title="Your sponsorships" description="Every TV sponsorship you've booked for your clients." />
      <div className="px-10 py-10">
        <div className="imh-card overflow-hidden">
          <table className="w-full text-sm" data-testid="sponsorships-table">
            <thead>
              <tr className="text-left border-b border-[#E4E4E1] bg-[#F9F9F6]">
                <Th>Project</Th><Th>Client</Th><Th className="text-right">Episodes</Th>
                <Th className="text-right">Internal</Th><Th className="text-right">Client price</Th><Th className="text-right">Margin</Th>
              </tr>
            </thead>
            <tbody>
              {items.map(s => (
                <tr key={s.id} className="border-b border-[#E4E4E1] last:border-b-0" data-testid={`sp-${s.id}`}>
                  <Td className="font-editorial">{s.tv_project_title}</Td>
                  <Td>{s.client_name}</Td>
                  <Td className="text-right font-mono-imh">{s.episode_count}</Td>
                  <Td className="text-right font-mono-imh">{usd(s.internal_cost_usd)}</Td>
                  <Td className="text-right font-mono-imh">{usd(s.client_total_price_usd)}</Td>
                  <Td className="text-right font-mono-imh" style={{ color: s.margin_usd >= 0 ? "#166534" : "#991B1B" }}>{usd(s.margin_usd)}</Td>
                </tr>
              ))}
              {items.length === 0 && <tr><Td colSpan={6} className="text-center py-16 text-[#52525B]">No sponsorships yet.</Td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
const Th = ({ children, className = "" }) => <th className={`px-6 py-4 text-[11px] uppercase tracking-widest text-[#52525B] font-medium ${className}`}>{children}</th>;
const Td = ({ children, className = "", colSpan, style }) => <td colSpan={colSpan} style={style} className={`px-6 py-4 text-[#0A0A0A] ${className}`}>{children}</td>;
