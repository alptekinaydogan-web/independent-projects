import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import api, { formatApiError } from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { toast } from "sonner";
import { ArrowLeft, Mail, Phone, Globe2, Calendar, Radio, FilmIcon, Activity,
          KeyRound, UserX, UserCheck, Edit3, MapPin, Bell, Send } from "lucide-react";

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
const fmtDateTime = (iso) => iso ? new Date(iso).toLocaleString(undefined, { year: "numeric", month: "short", day: "2-digit", hour: "2-digit", minute: "2-digit" }) : "—";

export default function RepresentativeProfile() {
  const { id } = useParams();
  const [profile, setProfile] = useState(null);
  const [historyFilter, setHistoryFilter] = useState("all");
  const [editOpen, setEditOpen] = useState(false);

  const load = () => api.get(`/admin/representatives/${id}/profile`).then(r => setProfile(r.data));
  useEffect(() => { load(); }, [id]);

  const toggleActive = async () => {
    try {
      await api.patch(`/admin/representatives/${id}`, { is_active: !profile.representative.is_active });
      toast.success(profile.representative.is_active ? "Suspended." : "Reactivated.");
      await load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };
  const resetPassword = async () => {
    const pw = window.prompt("New password for this representative:");
    if (!pw) return;
    try {
      await api.patch(`/admin/representatives/${id}`, { password: pw });
      toast.success("Password updated.");
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };

  if (!profile) return <div className="p-10 text-[#52525B] font-mono-imh text-xs" data-testid="profile-loading">Loading profile…</div>;
  const { representative: r, banner_stats, tv_stats, active_campaigns, history, timeline, notifications } = profile;

  const filteredHistory = historyFilter === "all" ? history :
                          historyFilter === "banner" ? history.filter(h => h.kind === "banner") :
                          historyFilter === "sponsorship" ? history.filter(h => h.kind === "sponsorship") :
                          history.filter(h => h.status === historyFilter);

  return (
    <div>
      <PageHeader
        eyebrow="Representative CRM"
        title={r.agency_name}
        description={`${r.name} · ${r.email}`}
        actions={
          <div className="flex gap-2">
            <Link to="/admin/representatives" data-testid="profile-back"
                  className="h-9 px-3 border border-[#E4E4E1] hover:border-[#0A0A0A] text-[11px] uppercase tracking-widest inline-flex items-center gap-1">
              <ArrowLeft size={12} /> All partners
            </Link>
            <Button onClick={() => setEditOpen(true)} data-testid="rep-edit-btn" variant="outline"
                    className="h-9 rounded-none border-[#E4E4E1] hover:border-[#0A0A0A]">
              <Edit3 size={13} className="mr-2" /> Edit
            </Button>
            <Button onClick={resetPassword} data-testid="rep-reset-btn" variant="outline"
                    className="h-9 rounded-none border-[#E4E4E1] hover:border-[#0A0A0A]">
              <KeyRound size={13} className="mr-2" /> Reset password
            </Button>
            <Button onClick={toggleActive} data-testid="rep-toggle-btn"
                    className={`h-9 rounded-none text-white ${r.is_active ? "bg-[#991B1B] hover:bg-[#7f1616]" : "bg-[#166534] hover:bg-[#0f4a25]"}`}>
              {r.is_active ? <><UserX size={13} className="mr-2" />Suspend</> : <><UserCheck size={13} className="mr-2" />Reactivate</>}
            </Button>
          </div>
        }
      />
      <div className="px-10 py-10 space-y-6" data-testid="rep-profile">
        {/* Identity — top bar */}
        <div className="imh-card p-6 grid grid-cols-2 lg:grid-cols-4 gap-6" data-testid="rep-identity">
          <Field icon={Mail} label="Email">{r.email}</Field>
          <Field icon={Phone} label="Phone">{r.phone || "—"}</Field>
          <Field icon={Globe2} label="Website">{r.website ? <a href={r.website} target="_blank" rel="noreferrer" className="hover:text-[#0033A0]">{r.website}</a> : "—"}</Field>
          <Field icon={MapPin} label="Country / Territory">{r.country || "—"}{r.territory ? ` · ${r.territory}` : ""}</Field>
          <Field icon={Activity} label="Status">
            <span className={r.is_active ? "text-[#166534]" : "text-[#991B1B]"}>{r.is_active ? "Active" : "Suspended"}</span>
          </Field>
          <Field icon={Calendar} label="Registered">{fmtDate(r.created_at)}</Field>
          <Field icon={Calendar} label="Approved on">{fmtDate(r.approved_at || r.created_at)}</Field>
          <Field icon={Activity} label="Last login">{fmtDateTime(r.last_login_at)}</Field>
        </div>

        {/* Commercial activity — condensed KPI strip */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4" data-testid="rep-kpis">
          <Kpi icon={Radio} label="Banner offers" value={banner_stats?.total || 0}
                sub={`${banner_stats?.approved || 0} approved · ${banner_stats?.pending_review || 0} pending · ${banner_stats?.rejected || 0} rejected`} testId="kpi-banner" />
          <Kpi icon={FilmIcon} label="TV proposals" value={tv_stats?.total || 0}
                sub={`${tv_stats?.approved || 0} approved · ${tv_stats?.pending_review || 0} pending · ${tv_stats?.rejected || 0} rejected`} testId="kpi-tv" />
          <Kpi icon={Send} label="Active banner campaigns" value={active_campaigns.filter(c => c.network_name).length}
                sub="Currently live or scheduled" testId="kpi-active-banners" />
          <Kpi icon={FilmIcon} label="Active TV sponsorships" value={tv_stats?.approved || 0}
                sub="Approved sponsorships" testId="kpi-active-tv" />
        </div>

        {/* Tabbed views: History / Timeline / Notifications / Campaigns */}
        <Tabs defaultValue="history" className="mt-2" data-testid="crm-tabs">
          <TabsList className="rounded-none border border-[#E4E4E1] bg-white p-0 h-auto">
            <TabsTrigger value="history" className="rounded-none data-[state=active]:bg-[#0A0A0A] data-[state=active]:text-white px-4 py-2 text-xs uppercase tracking-widest" data-testid="tab-history">Proposal history</TabsTrigger>
            <TabsTrigger value="campaigns" className="rounded-none data-[state=active]:bg-[#0A0A0A] data-[state=active]:text-white px-4 py-2 text-xs uppercase tracking-widest" data-testid="tab-campaigns">Active campaigns</TabsTrigger>
            <TabsTrigger value="notifications" className="rounded-none data-[state=active]:bg-[#0A0A0A] data-[state=active]:text-white px-4 py-2 text-xs uppercase tracking-widest" data-testid="tab-notifications">Notifications</TabsTrigger>
            <TabsTrigger value="timeline" className="rounded-none data-[state=active]:bg-[#0A0A0A] data-[state=active]:text-white px-4 py-2 text-xs uppercase tracking-widest" data-testid="tab-timeline">Timeline</TabsTrigger>
          </TabsList>

          <TabsContent value="history" className="mt-4">
            <div className="imh-card">
              <div className="px-6 py-4 border-b border-[#E4E4E1] flex items-center justify-between flex-wrap gap-3">
                <div>
                  <div className="imh-eyebrow">Proposal history</div>
                  <h3 className="font-editorial text-xl mt-1">{filteredHistory.length} entries</h3>
                </div>
                <div className="flex gap-2 flex-wrap" data-testid="history-filters">
                  {["all", "banner", "sponsorship", "approved", "pending_review", "revision_requested", "rejected", "archived"].map(f => (
                    <button key={f} onClick={() => setHistoryFilter(f)} data-testid={`filter-${f}`}
                             className={`px-2 py-1 text-[10px] uppercase tracking-widest border ${historyFilter === f ? "bg-[#0A0A0A] text-white border-[#0A0A0A]" : "bg-white border-[#E4E4E1] hover:border-[#0A0A0A]"}`}>
                      {f.replace("_", " ")}
                    </button>
                  ))}
                </div>
              </div>
              <div className="divide-y divide-[#E4E4E1]" data-testid="history-list">
                {filteredHistory.length === 0 && <div className="px-6 py-10 text-[#52525B] text-sm text-center">No entries match this filter.</div>}
                {filteredHistory.map(h => {
                  const s = STATUS_STYLE[h.status] || STATUS_STYLE.pending_review;
                  return (
                    <div key={`${h.kind}-${h.id}`} className="px-6 py-3 flex items-center justify-between text-sm">
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <span className="imh-eyebrow" style={{ color: h.kind === "banner" ? "#0033A0" : "#B45309" }}>
                            {h.kind === "banner" ? "Banner" : "TV"}
                          </span>
                          <span className="px-2 py-0.5 text-[10px] uppercase tracking-widest font-mono-imh"
                                style={{ background: s.bg, color: s.color }}>{h.status?.replace("_", " ")}</span>
                        </div>
                        <div className="mt-1 truncate">{h.title || "—"}</div>
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
          </TabsContent>

          <TabsContent value="campaigns" className="mt-4">
            <div className="imh-card">
              <div className="px-6 py-4 border-b border-[#E4E4E1]">
                <div className="imh-eyebrow">Active</div>
                <h3 className="font-editorial text-xl mt-1">{active_campaigns.length} live commercial engagements</h3>
              </div>
              <div className="divide-y divide-[#E4E4E1]" data-testid="active-list">
                {active_campaigns.length === 0 && <div className="px-6 py-10 text-[#52525B] text-sm text-center">No active engagements.</div>}
                {active_campaigns.map(c => (
                  <div key={c.id} className="px-6 py-3 flex items-center justify-between text-sm">
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
            </div>
          </TabsContent>

          <TabsContent value="notifications" className="mt-4">
            <div className="imh-card">
              <div className="px-6 py-4 border-b border-[#E4E4E1]">
                <div className="imh-eyebrow flex items-center gap-1"><Bell size={11} strokeWidth={1.6} /> Notifications sent to this partner</div>
                <h3 className="font-editorial text-xl mt-1">{notifications?.length || 0} messages</h3>
              </div>
              <div className="divide-y divide-[#E4E4E1]" data-testid="notifications-list">
                {(!notifications || notifications.length === 0) && <div className="px-6 py-10 text-[#52525B] text-sm text-center">No notifications yet.</div>}
                {(notifications || []).map(n => (
                  <div key={n.id} className="px-6 py-3 text-sm">
                    <div className="flex items-center gap-2">
                      <span className="w-1.5 h-1.5 rounded-full" style={{ background: n.severity === "action_required" ? "#B45309" : n.severity === "reminder" ? "#0033A0" : "#166534" }} />
                      <span className="font-editorial">{n.title}</span>
                      {!n.read && <span className="text-[9px] uppercase tracking-widest font-mono-imh px-1.5 py-0.5 bg-[#F5F0E1] text-[#B45309]">unread</span>}
                    </div>
                    <div className="mt-1 text-xs text-[#52525B] pl-3.5">{n.message}</div>
                    <div className="mt-1 text-[10px] font-mono-imh text-[#A1A1AA] pl-3.5">{fmtDateTime(n.created_at)}</div>
                  </div>
                ))}
              </div>
            </div>
          </TabsContent>

          <TabsContent value="timeline" className="mt-4">
            <div className="imh-card">
              <div className="px-6 py-4 border-b border-[#E4E4E1]">
                <div className="imh-eyebrow">Timeline</div>
                <h3 className="font-editorial text-xl mt-1">Complete activity history</h3>
              </div>
              <div className="divide-y divide-[#E4E4E1]" data-testid="timeline-list">
                {(!timeline || timeline.length === 0) && <div className="px-6 py-10 text-[#52525B] text-sm text-center">No timeline events yet.</div>}
                {(timeline || []).map((t, i) => (
                  <div key={i} className="px-6 py-3 text-sm">
                    <div className="flex items-center gap-2">
                      <span className="w-1.5 h-1.5 bg-[#0033A0] rounded-full inline-block" />
                      <span className="font-mono-imh text-[11px] text-[#0A0A0A]">{t.action}</span>
                      {t.actor_role && <span className="text-[10px] text-[#A1A1AA]">by {t.actor_name || t.actor_role}</span>}
                    </div>
                    <div className="mt-1 font-mono-imh text-[10px] text-[#A1A1AA] pl-3.5">
                      {fmtDateTime(t.at)} · {t.entity_type}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </TabsContent>
        </Tabs>
      </div>

      <EditRepDialog open={editOpen} onOpenChange={setEditOpen} rep={r} onSaved={load} />
    </div>
  );
}

function EditRepDialog({ open, onOpenChange, rep, onSaved }) {
  const [form, setForm] = useState({});
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    if (open) setForm({
      name: rep.name || "", agency_name: rep.agency_name || "",
      country: rep.country || "", phone: rep.phone || "",
      website: rep.website || "", territory: rep.territory || "",
    });
  }, [open, rep]);

  const save = async () => {
    setBusy(true);
    try {
      await api.patch(`/admin/representatives/${rep.id}`, form);
      onOpenChange(false);
      setTimeout(() => { toast.success("Profile updated."); onSaved && onSaved(); }, 0);
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
    finally { setBusy(false); }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="rounded-none border border-[#0A0A0A] max-w-lg" data-testid="edit-rep-dialog">
        <DialogHeader><DialogTitle className="font-editorial text-2xl">Edit representative</DialogTitle></DialogHeader>
        <div className="grid grid-cols-1 gap-3 mt-2">
          <F label="Full name"><Input value={form.name || ""} onChange={e => setForm(s => ({ ...s, name: e.target.value }))} /></F>
          <F label="Agency name"><Input value={form.agency_name || ""} onChange={e => setForm(s => ({ ...s, agency_name: e.target.value }))} /></F>
          <div className="grid grid-cols-2 gap-3">
            <F label="Country"><Input value={form.country || ""} onChange={e => setForm(s => ({ ...s, country: e.target.value }))} /></F>
            <F label="Territory"><Input value={form.territory || ""} onChange={e => setForm(s => ({ ...s, territory: e.target.value }))} /></F>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <F label="Phone"><Input value={form.phone || ""} onChange={e => setForm(s => ({ ...s, phone: e.target.value }))} /></F>
            <F label="Website"><Input value={form.website || ""} onChange={e => setForm(s => ({ ...s, website: e.target.value }))} placeholder="https://" /></F>
          </div>
        </div>
        <DialogFooter className="mt-4">
          <Button onClick={save} disabled={busy} data-testid="edit-rep-submit" className="rounded-none bg-[#0033A0] hover:bg-[#002277]">
            {busy ? "Saving…" : "Save changes"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

const Kpi = ({ icon: Icon, label, value, sub, testId }) => (
  <div className="imh-card p-5" data-testid={testId}>
    <div className="imh-eyebrow flex items-center gap-2"><Icon size={11} strokeWidth={1.6} /> {label}</div>
    <div className="imh-metric-number text-3xl mt-3">{value}</div>
    <div className="mt-2 text-[11px] font-mono-imh text-[#52525B]">{sub}</div>
  </div>
);
const F = ({ label, children }) => (
  <div>
    <Label className="text-[11px] uppercase tracking-widest text-[#52525B]">{label}</Label>
    <div className="mt-2">{children}</div>
  </div>
);
const Field = ({ icon: Icon, label, children }) => (
  <div>
    <div className="text-[10px] uppercase tracking-widest text-[#52525B] flex items-center gap-1"><Icon size={10} strokeWidth={1.5} /> {label}</div>
    <div className="mt-2 text-sm text-[#0A0A0A]">{children}</div>
  </div>
);
