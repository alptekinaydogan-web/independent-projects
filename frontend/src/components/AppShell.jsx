import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { LogOut, Users, LayoutGrid, Radio, FilmIcon, Send, BarChart3, Globe2, Sparkles, ShieldCheck, ScrollText, Bell } from "lucide-react";
import NotificationBell from "@/components/NotificationBell";

function Section({ label, children }) {
  return (
    <div className="mt-6">
      <div className="px-4 pb-2 imh-eyebrow" style={{ color: "#5E6884" }}>{label}</div>
      <div className="flex flex-col">{children}</div>
    </div>
  );
}

function Item({ to, icon: Icon, children, testId }) {
  return (
    <NavLink to={to} end
      data-testid={testId}
      className={({ isActive }) => `imh-sidebar-item ${isActive ? "active" : ""}`}>
      <Icon size={16} strokeWidth={1.5} />
      <span>{children}</span>
    </NavLink>
  );
}

export default function AppShell({ role }) {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  const isAdmin = role === "admin";
  const isOwner = user?.role === "owner";
  const base = isAdmin ? "/admin" : "/rep";
  const notifBase = isAdmin ? "/admin/notifications" : "/rep/notifications";

  return (
    <div className="min-h-screen flex bg-[#F9F9F6]">
      <aside className="w-[260px] shrink-0 text-white imh-grain relative flex flex-col" style={{ background: "#0A1128" }}>
        <div className="px-6 pt-8 pb-6 border-b border-[#1E293B] flex items-start justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <span className="imh-dot" style={{ background: "#fff" }} />
              <span className="imh-eyebrow" style={{ color: "#93A0C2" }}>Independent</span>
            </div>
            <h1 className="font-editorial text-2xl leading-tight mt-1">Media Hub</h1>
            <p className="text-[11px] mt-1" style={{ color: "#93A0C2", letterSpacing: "0.06em" }}>
              {isAdmin ? (isOwner ? "OWNER CONSOLE" : "ADMINISTRATOR CONSOLE") : "REPRESENTATIVE CONSOLE"}
            </p>
          </div>
          <NotificationBell notificationsBase={notifBase} />
        </div>

        {isAdmin ? (
          <>
            <Section label="Overview">
              <Item to={`${base}`} icon={LayoutGrid} testId="nav-admin-dashboard">Dashboard</Item>
              <Item to={notifBase} icon={Bell} testId="nav-admin-notifications">Notifications</Item>
            </Section>
            <Section label="Commercial">
              <Item to={`${base}/inventory`} icon={Globe2} testId="nav-admin-inventory">Inventory Catalog</Item>
              <Item to={`${base}/proposals-review`} icon={Sparkles} testId="nav-admin-review">Proposals Review</Item>
              <Item to={`${base}/tv-projects`} icon={FilmIcon} testId="nav-admin-tv">TV Projects</Item>
              <Item to={`${base}/proposals`} icon={Send} testId="nav-admin-editorial">Editorial Proposals</Item>
            </Section>
            <Section label="Network">
              <Item to={`${base}/representatives`} icon={Users} testId="nav-admin-reps">Representatives</Item>
              <Item to={`${base}/reports`} icon={BarChart3} testId="nav-admin-reports">Reports</Item>
              <Item to={`${base}/audit-log`} icon={ScrollText} testId="nav-admin-audit">Audit Log</Item>
              {isOwner && <Item to={`${base}/admins`} icon={ShieldCheck} testId="nav-owner-admins">Administrators</Item>}
            </Section>
          </>
        ) : (
          <>
            <Section label="Overview">
              <Item to={`${base}`} icon={LayoutGrid} testId="nav-rep-dashboard">Dashboard</Item>
              <Item to={notifBase} icon={Bell} testId="nav-rep-notifications">Notifications</Item>
            </Section>
            <Section label="Sell">
              <Item to={`${base}/banners`} icon={Radio} testId="nav-rep-campaigns">Banner Proposals</Item>
              <Item to={`${base}/tv`} icon={FilmIcon} testId="nav-rep-tv">TV Sponsorships</Item>
            </Section>
            <Section label="Grow">
              <Item to={`${base}/proposals`} icon={Send} testId="nav-rep-proposals">Editorial Proposals</Item>
              <Item to={`${base}/reports`} icon={BarChart3} testId="nav-rep-reports">Reports</Item>
            </Section>
          </>
        )}

        <div className="mt-auto px-6 py-6 border-t border-[#1E293B]">
          <div className="text-[11px] tracking-widest uppercase" style={{ color: "#93A0C2" }}>Signed in</div>
          <div className="mt-1 text-sm font-medium flex items-center gap-2">
            {user?.name}
            {isOwner && <ShieldCheck size={12} className="text-[#93A0C2]" />}
          </div>
          <div className="text-xs" style={{ color: "#93A0C2" }}>{user?.email}</div>
          <button
            data-testid="logout-button"
            onClick={async () => { await logout(); nav("/"); }}
            className="mt-4 inline-flex items-center gap-2 text-xs px-3 py-2 border border-[#334155] hover:bg-[#111a34]" style={{ transition: "background 160ms" }}>
            <LogOut size={13} /> Sign out
          </button>
        </div>
      </aside>

      <main className="flex-1 min-w-0">
        <Outlet />
      </main>
    </div>
  );
}
