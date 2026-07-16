import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import api from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import { ArrowLeft, Mail, Globe, Calendar, Radio, FilmIcon, Activity } from "lucide-react";

const STATUS_STYLE = {
  pending_review:     { bg: "#F5F0E1", color: "#B45309" },
  revised:            { bg: "#EEF2FF", color: "#0033A0" },
  approved:           { bg: "#E6F2EA", color: "#166534" },
  rejected:           { bg: "#FBEBEB", color: "#991B1B" },
  revision_requested: { bg: "#EEF2FF", color: "#0033A0" },
  archived:           { bg: "#EFEEEA", color: "#52525B" },
};

const fmt = (n) => n == null ? "—" : `$${Number(n).toLocaleString()}`;
const fmtDate = (iso) => iso ? new Date(iso).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "2-digit" }) : "—";

export default function RepresentativeProfile() {
  const { id } = useParams();
  const [profile, setProfile] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.get(`/admin/representatives/${id}/profile`)
       .then(r => setProfile(r.data))
       .catch(e => setError(e.response?.data?.detail || "Failed to load profile"));
  }, [id]);

  if (error) return <div className="p-10 text-[#991B1B]" data-testid="profile-error">{error}</div>;
  if (!profile) return <div className="p-10 text-[#52525B] font-mono-imh text-xs" data-testid="profile-loading">Loading profile…</div>;

  const { representative: r, banner_stats, tv_stats, active_campaigns, history, timeline } = profile;

  return (
    <div>
      <PageHeader
        eyebrow="Representative profile"
        title={r.name}
        description={r.agency_name}
        actions={
          <Link to="/admin/representatives" data-testid="profile-back"
                className="h-9 px-3 border border-[#E4E4E1] hover:border-[#0A0A0A] text-[11px] uppercase tracking-widest inline-flex items-center gap-1"
                style={{ transition: "border-color 120ms" }}>
            <ArrowLeft size={12} /> All representatives
          </Link>
        }
      />
      <div className="px-10 py-10 space-y-6" data-testid="rep-profile">
        {/* Identity + status */}
        <div className="imh-card p-6 grid grid-cols-2 lg:grid-cols-5 gap-6">
          <Field icon={Mail} label="Email">{r.email}</Field>
          <Field icon={Globe} label="Country">{r.country || "—"}</Field>
          <Field icon={Activity} label="Status">
            <span className={r.is_active ? "text-[#166534]" : "text-[#991B1B]"}>
              {r.is_active ? "Active" : "Suspended"}
            </span>
          </Field>
          <Field icon={Calendar} label="Registered">{fmtDate(r.created_at)}</Field>
          <Field icon={Calendar} label="Approved on">{fmtDate(r.approved_at || r.created_at)}</Field>
        </div>

        {/* Commercial stats */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <StatCard icon={Radio} kind="Banner" stats={banner_stats} testId="banner-stats" />
          <StatCard icon={FilmIcon} kind="TV" stats={tv_stats} testId="tv-stats" />
        </div>

        {/* Active campaigns */}
        <div className="imh-card">
          <div className="px-6 py-4 border-b border-[#E4E4E1] flex items-baseline justify-between">
            <div>
              <div className="imh-eyebrow">Active</div>
              <h3 className="font-editorial text-xl mt-1">Current campaigns</h3>
            </div>
            <span className="text-[11px] font-mono-imh text-[#52525B]" data-testid="active-count">{active_campaigns.length} live</span>
          </div>
          {active_campaigns.length === 0 ? (
            <div className="px-6 py-10 text-center text-[#52525B]">No active campaigns.</div>
          ) : (
            <div className="divide-y divide-[#E4E4E1]">
              {active_campaigns.map(c => (
                <div key={c.id} className="px-6 py-4 flex items-center justify-between text-sm" data-testid={`active-${c.id}`}>
                  <div>
                    <div className="font-editorial">{c.campaign_name}</div>
                    <div className="text-xs text-[#52525B]">{c.network_name} · {c.position_name}</div>
                  </div>
                  <div className="text-right">
                    <div className="font-mono-imh text-xs text-[#52525B]">{c.start_date} → {c.end_date}</div>
                    <div className="font-editorial mt-1">{fmt(c.offer_amount_usd)}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Proposal history + Timeline */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="imh-card">
            <div className="px-6 py-4 border-b border-[#E4E4E1]">
              <div className="imh-eyebrow">Proposal history</div>
              <h3 className="font-editorial text-xl mt-1">Recent submissions</h3>
            </div>
            <div className="divide-y divide-[#E4E4E1]" data-testid="history-list">
              {history.length === 0 && <div className="px-6 py-8 text-[#52525B] text-sm text-center">No proposals yet.</div>}
              {history.map(h => {
                const s = STATUS_STYLE[h.status] || STATUS_STYLE.pending_review;
                return (
                  <div key={`${h.kind}-${h.id}`} className="px-6 py-3 flex items-center justify-between text-sm">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="imh-eyebrow" style={{ color: h.kind === "banner" ? "#0033A0" : "#B45309" }}>
                          {h.kind === "banner" ? "Banner" : "TV"}
                        </span>
                        <span className="px-2 py-0.5 text-[10px] uppercase tracking-widest font-mono-imh"
                              style={{ background: s.bg, color: s.color }}>{h.status?.replace("_"," ")}</span>
                      </div>
                      <div className="mt-1 truncate">{h.title}</div>
                    </div>
                    <div className="text-right shrink-0 ml-3">
                      <div className="font-mono-imh text-[11px] text-[#52525B]">{fmtDate(h.created_at)}</div>
                      <div className="font-editorial text-sm">{fmt(h.amount)}</div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="imh-card">
            <div className="px-6 py-4 border-b border-[#E4E4E1]">
              <div className="imh-eyebrow">Timeline</div>
              <h3 className="font-editorial text-xl mt-1">Actions by this representative</h3>
            </div>
            <div className="divide-y divide-[#E4E4E1]" data-testid="timeline-list">
              {timeline.length === 0 && <div className="px-6 py-8 text-[#52525B] text-sm text-center">No timeline events yet.</div>}
              {timeline.map((t, i) => (
                <div key={i} className="px-6 py-3 text-sm">
                  <div className="flex items-center gap-2">
                    <span className="w-1.5 h-1.5 bg-[#0033A0] rounded-full inline-block" />
                    <span className="font-mono-imh text-[11px] text-[#0A0A0A]">{t.action}</span>
                  </div>
                  <div className="mt-1 font-mono-imh text-[10px] text-[#A1A1AA] pl-3.5">
                    {fmtDate(t.at)} · {t.entity_type}
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

function StatCard({ icon: Icon, kind, stats, testId }) {
  const total = stats?.total || 0;
  return (
    <div className="imh-card p-6" data-testid={testId}>
      <div className="imh-eyebrow flex items-center gap-2"><Icon size={11} strokeWidth={1.6} /> {kind} proposals</div>
      <div className="imh-metric-number text-3xl mt-3">{total}</div>
      <div className="mt-4 flex flex-wrap gap-3 text-[11px] font-mono-imh">
        <Chip label="Approved" value={stats?.approved || 0} color="#166534" />
        <Chip label="Pending"  value={stats?.pending_review || 0} color="#B45309" />
        <Chip label="Revised"  value={stats?.revised || 0} color="#0033A0" />
        <Chip label="Revision" value={stats?.revision_requested || 0} color="#0033A0" />
        <Chip label="Rejected" value={stats?.rejected || 0} color="#991B1B" />
        <Chip label="Archived" value={stats?.archived || 0} color="#52525B" />
      </div>
    </div>
  );
}
const Chip = ({ label, value, color }) => (
  <span className="inline-flex items-center gap-1.5 px-2 py-1 border border-[#E4E4E1]">
    <span className="w-1.5 h-1.5 rounded-full" style={{ background: color }} />
    <span className="text-[#52525B]">{label}</span>
    <b className="text-[#0A0A0A]">{value}</b>
  </span>
);
const Field = ({ icon: Icon, label, children }) => (
  <div>
    <div className="text-[10px] uppercase tracking-widest text-[#52525B] flex items-center gap-1"><Icon size={10} strokeWidth={1.5} /> {label}</div>
    <div className="mt-2 text-sm text-[#0A0A0A]">{children}</div>
  </div>
);
