import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import api from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import { ArrowLeft, CalendarDays, Users } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";

const STATE_STYLE = {
  available: { bg: "#E6F2EA", color: "#166534", label: "Available" },
  reserved:  { bg: "#FBEBEB", color: "#991B1B", label: "Reserved" },
  active:    { bg: "#EEF2FF", color: "#0033A0", label: "Active" },
  expired:   { bg: "#EFEEEA", color: "#52525B", label: "Expired" },
};

const fmt = (n) => n == null ? "—" : `$${Number(n).toLocaleString()}`;

export default function InventoryDetail() {
  const { id } = useParams();
  const { user } = useAuth();
  const isAdmin = user && (user.role === "admin" || user.role === "owner");
  const [detail, setDetail] = useState(null);
  const [calendar, setCalendar] = useState(null);

  useEffect(() => {
    api.get(`/inventory/${id}`).then(r => setDetail(r.data));
    api.get(`/inventory/${id}/availability`).then(r => setCalendar(r.data));
  }, [id]);

  if (!detail) return <div className="p-10 text-[#52525B] font-mono-imh text-xs" data-testid="inventory-loading">Loading…</div>;
  const inv = detail.inventory;
  const st = STATE_STYLE[detail.status] || STATE_STYLE.available;

  const backLink = isAdmin ? "/admin/inventory" : "/rep/tv"; // reps enter from a different place but keep back-nav sane

  return (
    <div>
      <PageHeader
        eyebrow={`${inv.network_name} · Inventory`}
        title={`${inv.network_name} · ${inv.position_name}`}
        description={inv.position_description || "Standardized network product across the Independent Media Network."}
        actions={
          <Link to={isAdmin ? "/admin/inventory" : "/rep/banners"} data-testid="inventory-back"
                className="h-9 px-3 border border-[#E4E4E1] hover:border-[#0A0A0A] text-[11px] uppercase tracking-widest inline-flex items-center gap-1"
                style={{ transition: "border-color 120ms" }}>
            <ArrowLeft size={12} /> {isAdmin ? "Inventory catalog" : "Your proposals"}
          </Link>
        }
      />
      <div className="px-10 py-10 space-y-6" data-testid="inventory-detail">
        {/* Overall status */}
        <div className="imh-card p-6 flex items-center justify-between flex-wrap gap-4">
          <div>
            <div className="imh-eyebrow">Current inventory status</div>
            <div className="mt-2 flex items-center gap-3">
              <span className="px-3 py-1 text-[11px] uppercase tracking-widest font-mono-imh"
                    style={{ background: st.bg, color: st.color }} data-testid="inventory-status">{st.label}</span>
              {!isAdmin && detail.status !== "available" && (
                <span className="text-xs text-[#52525B]">
                  This inventory is currently unavailable for a new proposal. See the calendar below to plan around it.
                </span>
              )}
            </div>
          </div>
          {!isAdmin && detail.status === "available" && (
            <Link to="/rep/banners/new" data-testid="submit-offer-cta"
                  className="h-10 px-4 bg-[#0033A0] hover:bg-[#002277] text-white text-[12px] uppercase tracking-widest inline-flex items-center"
                  style={{ transition: "background 120ms" }}>
              Prepare an offer
            </Link>
          )}
        </div>

        {/* Calendar */}
        <div className="imh-card p-6">
          <div className="flex items-baseline justify-between mb-4">
            <div>
              <div className="imh-eyebrow flex items-center gap-2"><CalendarDays size={11} strokeWidth={1.6} /> Availability</div>
              <h3 className="font-editorial text-xl mt-1">Next 12 months</h3>
            </div>
            <div className="flex items-center gap-3 text-[10px] uppercase tracking-widest font-mono-imh">
              <span className="inline-flex items-center gap-1.5"><i className="w-3 h-3 bg-[#E6F2EA] border border-[#166534]" /> Available</span>
              <span className="inline-flex items-center gap-1.5"><i className="w-3 h-3 bg-[#FBEBEB] border border-[#991B1B]" /> Reserved</span>
              <span className="inline-flex items-center gap-1.5"><i className="w-3 h-3 bg-[#EEF2FF] border border-[#0033A0]" /> Active</span>
            </div>
          </div>
          {calendar ? (
            <div className="grid grid-cols-4 lg:grid-cols-6 gap-2" data-testid="calendar-grid">
              {calendar.months.map(m => {
                const s = STATE_STYLE[m.state] || STATE_STYLE.available;
                return (
                  <div key={`${m.year}-${m.month}`}
                       className="p-3 border"
                       style={{ background: s.bg, borderColor: s.color, color: s.color }}
                       data-testid={`month-${m.year}-${m.month}`}>
                    <div className="text-[11px] uppercase tracking-widest font-mono-imh">{m.label}</div>
                    <div className="mt-2 text-[10px] font-mono-imh">{s.label}</div>
                    {m.reserved_by && <div className="mt-1 text-[9px] truncate" title={m.reserved_by}>{m.reserved_by}</div>}
                  </div>
                );
              })}
            </div>
          ) : <div className="text-xs font-mono-imh text-[#A1A1AA]">Loading calendar…</div>}
        </div>

        {/* Reservations + Offers */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="imh-card">
            <div className="px-6 py-4 border-b border-[#E4E4E1]">
              <div className="imh-eyebrow flex items-center gap-2"><Users size={11} strokeWidth={1.6} /> Reservations</div>
              <h3 className="font-editorial text-xl mt-1">Approved flights</h3>
            </div>
            <div className="divide-y divide-[#E4E4E1]" data-testid="reservations-list">
              {detail.reservations.length === 0 && <div className="px-6 py-8 text-[#52525B] text-sm text-center">No reservations yet.</div>}
              {detail.reservations.map(r => (
                <div key={r.id} className="px-6 py-3 flex items-center justify-between text-sm">
                  <div>
                    <div className="font-editorial">{r.agency_name || (r.is_yours ? "You" : "External agency")}</div>
                    <div className="font-mono-imh text-[11px] text-[#52525B]">{r.start_date} → {r.end_date}</div>
                  </div>
                  <span className="px-2 py-0.5 text-[10px] uppercase tracking-widest font-mono-imh"
                        style={{ background: STATE_STYLE[r.lifecycle]?.bg || "#EFEEEA",
                                 color: STATE_STYLE[r.lifecycle]?.color || "#52525B" }}>
                    {STATE_STYLE[r.lifecycle]?.label || "—"}
                  </span>
                </div>
              ))}
            </div>
          </div>

          <div className="imh-card">
            <div className="px-6 py-4 border-b border-[#E4E4E1] flex items-baseline justify-between">
              <div>
                <div className="imh-eyebrow">{isAdmin ? "All offers" : "Your offers"}</div>
                <h3 className="font-editorial text-xl mt-1">Proposal history for this product</h3>
              </div>
              {isAdmin && <span className="text-[11px] font-mono-imh text-[#52525B]">{detail.offers_count} offer(s)</span>}
            </div>
            <div className="divide-y divide-[#E4E4E1]" data-testid="offers-list">
              {detail.offers.length === 0 && <div className="px-6 py-8 text-[#52525B] text-sm text-center">No offers yet.</div>}
              {detail.offers.map(o => (
                <div key={o.id} className="px-6 py-3 text-sm">
                  <div className="flex items-center justify-between">
                    <div className="font-editorial truncate">{o.campaign_name || "—"}</div>
                    <div className="font-mono-imh text-xs">{fmt(o.offer_amount_usd)}</div>
                  </div>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="px-2 py-0.5 text-[9px] uppercase tracking-widest font-mono-imh"
                          style={{ background: "#F5F0E1", color: "#B45309" }}>{o.status?.replace("_"," ")}</span>
                    {isAdmin && <span className="text-[10px] text-[#52525B]">{o.agency_name}</span>}
                    <span className="ml-auto text-[10px] font-mono-imh text-[#A1A1AA]">{o.start_date} → {o.end_date}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
