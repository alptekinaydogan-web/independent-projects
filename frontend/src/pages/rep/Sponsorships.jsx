import { useEffect, useState } from "react";
import api from "@/lib/api";
import PageHeader from "@/components/PageHeader";

const STATUS_STYLE = {
  pending_review:     { bg: "#F5F0E1", color: "#B45309", label: "Pending review" },
  approved:           { bg: "#E6F2EA", color: "#166534", label: "Approved" },
  rejected:           { bg: "#FBEBEB", color: "#991B1B", label: "Rejected" },
  revision_requested: { bg: "#EEF2FF", color: "#0033A0", label: "Revision requested" },
};

export default function Sponsorships() {
  const [items, setItems] = useState([]);
  useEffect(() => { api.get("/sponsorships").then(r => setItems(r.data)); }, []);
  return (
    <div>
      <PageHeader eyebrow="Independent TV" title="Your sponsorship proposals" description="Every TV sponsorship proposal you have submitted." />
      <div className="px-10 py-10">
        <div className="imh-card overflow-hidden">
          <table className="w-full text-sm" data-testid="sponsorships-table">
            <thead>
              <tr className="text-left border-b border-[#E4E4E1] bg-[#F9F9F6]">
                <Th>Project</Th><Th>Client ref</Th><Th className="text-right">Episodes</Th><Th>Status</Th>
              </tr>
            </thead>
            <tbody>
              {items.map(s => {
                const st = STATUS_STYLE[s.status] || STATUS_STYLE.pending_review;
                return (
                  <tr key={s.id} className="border-b border-[#E4E4E1] last:border-b-0" data-testid={`sp-${s.id}`}>
                    <Td className="font-editorial">{s.tv_project_title}</Td>
                    <Td>{s.client_reference || s.client_name || "—"}</Td>
                    <Td className="text-right font-mono-imh">{s.episode_count}</Td>
                    <Td>
                      <span className="inline-block px-2 py-0.5 text-[10px] uppercase tracking-widest font-mono-imh"
                            style={{ background: st.bg, color: st.color }} data-testid={`sp-status-${s.id}`}>{st.label}</span>
                      {s.admin_notes && <div className="text-xs text-[#52525B] italic mt-1 max-w-md">Admin: {s.admin_notes}</div>}
                    </Td>
                  </tr>
                );
              })}
              {items.length === 0 && <tr><Td colSpan={4} className="text-center py-16 text-[#52525B]">No sponsorship proposals yet.</Td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
const Th = ({ children, className = "" }) => <th className={`px-6 py-4 text-[11px] uppercase tracking-widest text-[#52525B] font-medium ${className}`}>{children}</th>;
const Td = ({ children, className = "", colSpan }) => <td colSpan={colSpan} className={`px-6 py-4 text-[#0A0A0A] ${className}`}>{children}</td>;
