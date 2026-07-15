import { useEffect, useState } from "react";
import api from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import { useAuth } from "@/contexts/AuthContext";
import ActionableStrip from "@/components/ActionableStrip";
import { Link } from "react-router-dom";
import { ArrowUpRight, Activity, Database, Mail, Clock, CalendarClock } from "lucide-react";

function Metric({ label, value, sub, testId, tone }) {
  const color = tone === "warning" ? "#B45309" : tone === "positive" ? "#166534" : tone === "danger" ? "#991B1B" : "#0A0A0A";
  return (
    <div className="imh-card p-6" data-testid={testId}>
      <div className="imh-eyebrow">{label}</div>
      <div className="imh-metric-number text-3xl mt-3" style={{ color }}>{value}</div>
      {sub && <div className="mt-2 text-xs text-[#52525B]">{sub}</div>}
    </div>
  );
}

export default function AdminDashboard() {
  const { user } = useAuth();
  const [d, setD] = useState(null);
  const [health, setHealth] = useState(null);

  useEffect(() => { api.get("/reports/overview").then(r => setD(r.data)); }, []);

  useEffect(() => {
    let alive = true;
    const load = () => api.get("/admin/system/health")
                          .then(r => { if (alive) setHealth(r.data); })
                          .catch(() => {});
    load();
    // Poll every 30s so the card stays live while the tab is open
    const id = setInterval(load, 30000);
    return () => { alive = false; clearInterval(id); };
  }, []);

  const bp = d?.banner_proposals || {};
  const tp = d?.tv_proposals || {};

  return (
    <div>
      <PageHeader
        eyebrow="Administrator Overview"
        title={`Good day, ${user?.name?.split(" ")[0] || "Admin"}.`}
        description="Commercial activity across Independent Media Network. Review commercial proposals from representatives, monitor approved inventory, and manage editorial concepts."
      />
      <div className="px-10 py-10 space-y-8">
        <ActionableStrip base="/admin" />

        <div>
          <div className="imh-eyebrow mb-3">Proposals awaiting your decision</div>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <Metric testId="metric-all-pending" label="All pending review" value={d?.all_pending_review ?? "—"} sub="Banner + TV proposals" tone={d?.all_pending_review > 0 ? "warning" : undefined} />
            <Metric testId="metric-banner-pending" label="Banner pending" value={bp.pending_review ?? "—"} sub="Confidential offers" tone={bp.pending_review > 0 ? "warning" : undefined} />
            <Metric testId="metric-tv-pending" label="TV pending" value={tp.pending_review ?? "—"} sub="Sponsorship offers" tone={tp.pending_review > 0 ? "warning" : undefined} />
            <Metric testId="metric-reps-active" label="Active representatives" value={d?.total_reps_active ?? "—"} sub="Licensed agencies" />
          </div>
        </div>

        <div>
          <div className="imh-eyebrow mb-3">Approved commercial activity</div>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <Metric testId="metric-banner-approved" label="Approved banner proposals" value={bp.approved ?? "—"} tone="positive" />
            <Metric testId="metric-tv-approved" label="Approved sponsorships" value={tp.approved ?? "—"} tone="positive" />
            <Metric testId="metric-banner-total" label="Total banner proposals" value={bp.total ?? "—"} sub="All statuses" />
            <Metric testId="metric-tv-total" label="Total TV proposals" value={tp.total ?? "—"} sub="All statuses" />
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <QuickLink to="/admin/proposals-review" title="Review pending proposals" desc="Approve, request revision, or reject commercial proposals waiting for your decision." />
          <QuickLink to="/admin/tv-projects" title="Publish a TV project" desc="Add or freeze productions in the sponsorship catalog." />
          <QuickLink to="/admin/inventory" title="Inspect inventory catalog" desc="See the network×position products currently offered to representatives." />
        </div>

        <SystemVitals health={health} />
      </div>
    </div>
  );
}

function SystemVitals({ health }) {
  if (!health) {
    return (
      <div className="imh-card p-6" data-testid="system-vitals-loading">
        <div className="imh-eyebrow">System vitals</div>
        <div className="mt-3 text-xs font-mono-imh text-[#A1A1AA]">Loading…</div>
      </div>
    );
  }

  const okOverall = health.status === "ok";
  const dbOk      = health.database?.ok;
  const dbLat     = health.database?.latency_ms;
  const queue     = health.background_tasks?.outstanding ?? 0;
  const emailMode = health.email?.mode || "unknown";
  const emailLive = emailMode === "live";
  const uptimeH   = health.uptime_seconds != null ? formatUptime(health.uptime_seconds) : "—";
  const archiveDays = health.scheduler?.proposal_archive_days;
  const reminders   = (health.scheduler?.campaign_reminder_days || []).join(" · ");

  return (
    <div className="imh-card p-6" data-testid="system-vitals">
      <div className="flex items-baseline justify-between mb-4">
        <div>
          <div className="imh-eyebrow flex items-center gap-2">
            <Activity size={11} strokeWidth={1.6} />
            System vitals
          </div>
          <h3 className="font-editorial text-xl mt-1">Platform is {okOverall ? "healthy" : "degraded"}</h3>
        </div>
        <div className="flex items-center gap-2" data-testid="vitals-status-badge">
          <span className="inline-block w-2 h-2 rounded-full" style={{ background: okOverall ? "#166534" : "#991B1B" }} />
          <span className="text-[10px] uppercase tracking-widest font-mono-imh" style={{ color: okOverall ? "#166534" : "#991B1B" }}>
            {okOverall ? "All systems normal" : "Degraded"}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        <Vital icon={Database} label="Database"
                value={dbOk ? "Connected" : "Unreachable"}
                sub={dbOk && dbLat != null ? `${dbLat} ms ping` : ""}
                tone={dbOk ? "positive" : "danger"} testId="vital-database" />
        <Vital icon={Clock} label="Queue depth"
                value={queue}
                sub={queue === 0 ? "No pending tasks" : `${queue} background task${queue === 1 ? "" : "s"} running`}
                tone={queue > 5 ? "warning" : queue > 0 ? "neutral" : "positive"}
                testId="vital-queue" />
        <Vital icon={Mail} label="Email delivery"
                value={emailLive ? "Live" : "Dev fallback"}
                sub={emailLive ? `via ${health.email.from || "resend"}` : "RESEND_API_KEY not set"}
                tone={emailLive ? "positive" : "warning"} testId="vital-email" />
        <Vital icon={CalendarClock} label="Scheduler"
                value={`Archive · ${archiveDays}d`}
                sub={reminders ? `Reminders · ${reminders}d` : "—"}
                tone="neutral" testId="vital-scheduler" />
        <Vital icon={Activity} label="Uptime"
                value={uptimeH}
                sub="Since last restart"
                tone="neutral" testId="vital-uptime" />
      </div>
    </div>
  );
}

function Vital({ icon: Icon, label, value, sub, tone, testId }) {
  const color = tone === "positive" ? "#166534"
               : tone === "warning"  ? "#B45309"
               : tone === "danger"   ? "#991B1B"
               : "#0A0A0A";
  return (
    <div className="border-l-2 border-[#E4E4E1] pl-4" data-testid={testId}>
      <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-widest text-[#52525B]">
        <Icon size={10} strokeWidth={1.6} /> {label}
      </div>
      <div className="mt-2 font-editorial text-lg" style={{ color }}>{value}</div>
      {sub && <div className="mt-1 text-[11px] font-mono-imh text-[#A1A1AA]">{sub}</div>}
    </div>
  );
}

function formatUptime(sec) {
  const s = Math.max(0, Math.floor(sec));
  if (s < 60) return `${s}s`;
  if (s < 3600) return `${Math.floor(s/60)}m ${s%60}s`;
  if (s < 86400) return `${Math.floor(s/3600)}h ${Math.floor((s%3600)/60)}m`;
  const d = Math.floor(s/86400);
  return `${d}d ${Math.floor((s%86400)/3600)}h`;
}

function QuickLink({ to, title, desc }) {
  return (
    <Link to={to} className="imh-card p-6 group hover:border-[#0A0A0A]" style={{ transition: "border-color 160ms ease" }}>
      <div className="flex items-start justify-between">
        <h4 className="font-editorial text-xl">{title}</h4>
        <ArrowUpRight size={18} className="text-[#0033A0] group-hover:-translate-y-0.5 group-hover:translate-x-0.5" style={{ transition: "transform 160ms ease" }} />
      </div>
      <p className="mt-3 text-sm text-[#52525B]">{desc}</p>
    </Link>
  );
}
