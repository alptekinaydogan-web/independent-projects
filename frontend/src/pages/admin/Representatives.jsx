import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api, { formatApiError } from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from "@/components/ui/dialog";
import { toast } from "sonner";
import { Plus } from "lucide-react";

/**
 * Representatives (CRM index).
 *
 * The previous incarnation crashed with a React "removeChild" error when
 * creating a rep — root cause was Radix Select receiving an empty-string
 * value AND the create handler closing the dialog while immediately swapping
 * the table beneath it. We fixed both by:
 *   1. Using a plain native <select> for the country (still fully accessible)
 *      to sidestep Radix's portal race.
 *   2. Closing the dialog first, then reloading the table on a microtask so
 *      React can finish unmounting the dialog subtree before the parent
 *      re-renders.
 * Row actions are moved out of a dropdown into a link to the CRM profile page,
 * where they are exposed as first-class administrative actions.
 */
export default function Representatives() {
  const [reps, setReps] = useState([]);
  const [countries, setCountries] = useState([]);
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState(initialForm());

  const load = async () => {
    const [r1, r2] = await Promise.allSettled([
      api.get("/admin/representatives"),
      api.get("/countries"),
    ]);
    if (r1.status === "fulfilled") setReps(r1.value.data);
    if (r2.status === "fulfilled") setCountries(r2.value.data);
  };
  useEffect(() => { load(); }, []);

  const create = async () => {
    if (!form.email || !form.password || !form.name || !form.agency_name || !form.country) {
      toast.error("Please fill in all required fields.");
      return;
    }
    setBusy(true);
    try {
      await api.post("/admin/representatives", form);
      // 1) Close the dialog first so Radix can unmount cleanly
      setOpen(false);
      // 2) On the next tick, reset the form + refresh the table
      setTimeout(() => {
        setForm(initialForm());
        load();
        toast.success("Representative created.");
      }, 0);
    } catch (e) {
      toast.error(formatApiError(e.response?.data?.detail));
    } finally { setBusy(false); }
  };

  return (
    <div>
      <PageHeader
        eyebrow="Network"
        title="Representatives"
        description="Licensed commercial partners of Independent Media Network. Click any row to open the full CRM profile."
        actions={
          <Button data-testid="new-rep-button" onClick={() => setOpen(true)}
                  className="h-10 rounded-none bg-[#0033A0] hover:bg-[#002277] text-white">
            <Plus size={16} className="mr-2" /> New representative
          </Button>
        }
      />

      <div className="px-10 py-10">
        <div className="imh-card overflow-hidden" data-testid="reps-table">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left border-b border-[#E4E4E1] bg-[#F9F9F6]">
                <Th>Agency</Th><Th>Representative</Th><Th>Country</Th>
                <Th className="text-right">Active</Th>
                <Th className="text-right">Pending</Th>
                <Th className="text-right">Approved</Th>
                <Th>Last activity</Th>
                <Th>Status</Th>
              </tr>
            </thead>
            <tbody>
              {reps.map(r => (
                <tr key={r.id} className="border-b border-[#E4E4E1] last:border-b-0 hover:bg-[#F9F9F6]"
                    data-testid={`rep-row-${r.id}`}>
                  <Td className="font-editorial text-base">
                    <Link to={`/admin/representatives/${r.id}`} className="hover:text-[#0033A0]"
                          data-testid={`rep-profile-link-${r.id}`}>
                      {r.agency_name}
                    </Link>
                  </Td>
                  <Td>
                    <div>{r.name}</div>
                    <div className="font-mono-imh text-[10px] text-[#A1A1AA]">{r.email}</div>
                  </Td>
                  <Td className="font-mono-imh text-xs">{r.country || "—"}</Td>
                  <Td className="text-right font-mono-imh">{r.active_engagements ?? 0}</Td>
                  <Td className="text-right font-mono-imh">{r.pending_offers ?? 0}</Td>
                  <Td className="text-right font-mono-imh">{r.approved_offers ?? 0}</Td>
                  <Td className="font-mono-imh text-[11px] text-[#52525B]">{relTime(r.last_activity_at || r.last_login_at)}</Td>
                  <Td>
                    <span className={`inline-flex items-center gap-2 text-xs ${r.is_active ? "text-[#166534]" : "text-[#991B1B]"}`}>
                      <span className="imh-dot" style={{ background: r.is_active ? "#166534" : "#991B1B" }} />
                      {r.is_active ? "Active" : "Suspended"}
                    </span>
                  </Td>
                </tr>
              ))}
              {reps.length === 0 && (
                <tr><Td colSpan={8} className="text-center py-10 text-[#52525B]">No representatives yet.</Td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="rounded-none border border-[#0A0A0A] max-w-lg" data-testid="new-rep-dialog">
          <DialogHeader>
            <DialogTitle className="font-editorial text-2xl">Invite a representative</DialogTitle>
            <DialogDescription className="text-xs text-[#52525B]">
              Create an active partner account. The representative can sign in immediately.
            </DialogDescription>
          </DialogHeader>
          <div className="grid grid-cols-1 gap-3 mt-2">
            <F label="Full name">
              <Input data-testid="rep-name" value={form.name} onChange={e => setForm(s => ({ ...s, name: e.target.value }))} />
            </F>
            <F label="Agency name">
              <Input data-testid="rep-agency" value={form.agency_name} onChange={e => setForm(s => ({ ...s, agency_name: e.target.value }))} />
            </F>
            <div className="grid grid-cols-2 gap-3">
              <F label="Email">
                <Input data-testid="rep-email" type="email" value={form.email} onChange={e => setForm(s => ({ ...s, email: e.target.value }))} />
              </F>
              <F label="Initial password">
                <Input data-testid="rep-password" value={form.password} onChange={e => setForm(s => ({ ...s, password: e.target.value }))} />
              </F>
            </div>
            <F label="Country">
              <select data-testid="rep-country" value={form.country}
                       onChange={e => setForm(s => ({ ...s, country: e.target.value }))}
                       className="h-10 border border-[#E4E4E1] px-3 text-sm bg-white w-full">
                <option value="">Select country…</option>
                {countries.map(c => <option key={c.code} value={c.code}>{c.name}</option>)}
              </select>
            </F>
            <div className="grid grid-cols-2 gap-3">
              <F label="Territory (optional)">
                <Input data-testid="rep-territory" value={form.territory} onChange={e => setForm(s => ({ ...s, territory: e.target.value }))} />
              </F>
              <F label="Phone (optional)">
                <Input data-testid="rep-phone" value={form.phone} onChange={e => setForm(s => ({ ...s, phone: e.target.value }))} />
              </F>
            </div>
            <F label="Website (optional)">
              <Input data-testid="rep-website" value={form.website} onChange={e => setForm(s => ({ ...s, website: e.target.value }))} placeholder="https://" />
            </F>
          </div>
          <DialogFooter className="mt-4">
            <Button data-testid="rep-create-submit" onClick={create} disabled={busy}
                     className="rounded-none bg-[#0033A0] hover:bg-[#002277]">
              {busy ? "Creating…" : "Create representative"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function initialForm() {
  return { email: "", password: "", name: "", agency_name: "", country: "",
            phone: "", website: "", territory: "" };
}

function relTime(iso) {
  if (!iso) return "—";
  const d = new Date(iso);
  const secs = Math.floor((Date.now() - d.getTime()) / 1000);
  if (secs < 60) return "just now";
  if (secs < 3600) return `${Math.floor(secs / 60)}m ago`;
  if (secs < 86400) return `${Math.floor(secs / 3600)}h ago`;
  return `${Math.floor(secs / 86400)}d ago`;
}

const F = ({ label, children }) => (
  <div>
    <Label className="text-[11px] uppercase tracking-widest text-[#52525B]">{label}</Label>
    <div className="mt-2">{children}</div>
  </div>
);
const Th = ({ children, className = "" }) => <th className={`px-6 py-4 text-[11px] uppercase tracking-widest text-[#52525B] font-medium ${className}`}>{children}</th>;
const Td = ({ children, className = "", colSpan }) => <td colSpan={colSpan} className={`px-6 py-4 text-[#0A0A0A] ${className}`}>{children}</td>;
