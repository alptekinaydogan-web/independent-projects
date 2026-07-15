import { useEffect, useState } from "react";
import api, { formatApiError } from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "sonner";
import { Plus, MoreHorizontal, UserX, KeyRound, UserCheck } from "lucide-react";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";

export default function Representatives() {
  const [reps, setReps] = useState([]);
  const [countries, setCountries] = useState([]);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ email: "", password: "", name: "", agency_name: "", country: "" });

  const load = async () => {
    // Use allSettled so a failure on a secondary lookup (e.g. /countries)
    // does not swallow the primary reps data and take the page down.
    const [r1, r2] = await Promise.allSettled([
      api.get("/admin/representatives"),
      api.get("/countries"),
    ]);
    if (r1.status === "fulfilled") setReps(r1.value.data);
    if (r2.status === "fulfilled") setCountries(r2.value.data);
  };
  useEffect(() => { load(); }, []);

  const create = async () => {
    try {
      await api.post("/admin/representatives", form);
      toast.success("Representative created");
      setOpen(false); setForm({ email: "", password: "", name: "", agency_name: "", country: "" });
      await load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };

  const toggleActive = async (rep) => {
    try {
      await api.patch(`/admin/representatives/${rep.id}`, { is_active: !rep.is_active });
      toast.success(rep.is_active ? "Suspended" : "Reactivated");
      await load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };

  const resetPassword = async (rep) => {
    const newPw = prompt(`New password for ${rep.email}`);
    if (!newPw) return;
    try {
      await api.patch(`/admin/representatives/${rep.id}`, { password: newPw });
      toast.success("Password updated");
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };

  return (
    <div>
      <PageHeader eyebrow="Network"
        title="Representatives"
        description="Licensed commercial partners with access to Independent Media Hub."
        actions={
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
              <Button data-testid="new-rep-button" className="h-10 rounded-none bg-[#0033A0] hover:bg-[#002277] text-white">
                <Plus size={16} className="mr-2" /> New representative
              </Button>
            </DialogTrigger>
            <DialogContent className="rounded-none border border-[#0A0A0A]">
              <DialogHeader>
                <DialogTitle className="font-editorial text-2xl">Invite representative</DialogTitle>
              </DialogHeader>
              <div className="grid grid-cols-1 gap-4 mt-2">
                <Field label="Full name"><Input data-testid="rep-name" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} /></Field>
                <Field label="Agency name"><Input data-testid="rep-agency" value={form.agency_name} onChange={e => setForm({ ...form, agency_name: e.target.value })} /></Field>
                <Field label="Email"><Input data-testid="rep-email" type="email" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} /></Field>
                <Field label="Initial password"><Input data-testid="rep-password" value={form.password} onChange={e => setForm({ ...form, password: e.target.value })} /></Field>
                <Field label="Country">
                  <Select value={form.country} onValueChange={v => setForm({ ...form, country: v })}>
                    <SelectTrigger data-testid="rep-country" className="rounded-none h-10"><SelectValue placeholder="Select country" /></SelectTrigger>
                    <SelectContent>
                      {countries.map(c => <SelectItem key={c.code} value={c.code}>{c.name}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </Field>
              </div>
              <DialogFooter>
                <Button data-testid="rep-create-submit" onClick={create} className="rounded-none bg-[#0033A0] hover:bg-[#002277]">Create representative</Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        }
      />
      <div className="px-10 py-10">
        <div className="imh-card overflow-hidden" data-testid="reps-table">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left border-b border-[#E4E4E1] bg-[#F9F9F6]">
                <Th>Agency</Th><Th>Representative</Th><Th>Email</Th><Th>Country</Th><Th>Status</Th><Th></Th>
              </tr>
            </thead>
            <tbody>
              {reps.map(r => (
                <tr key={r.id} className="border-b border-[#E4E4E1] last:border-b-0 hover:bg-[#F9F9F6]" data-testid={`rep-row-${r.id}`}>
                  <Td className="font-editorial text-base">{r.agency_name}</Td>
                  <Td>{r.name}</Td>
                  <Td className="font-mono-imh text-xs">{r.email}</Td>
                  <Td>{r.country}</Td>
                  <Td>
                    <span className={`inline-flex items-center gap-2 text-xs ${r.is_active ? "text-[#166534]" : "text-[#991B1B]"}`}>
                      <span className={`imh-dot`} style={{ background: r.is_active ? "#166534" : "#991B1B" }} />
                      {r.is_active ? "Active" : "Suspended"}
                    </span>
                  </Td>
                  <Td>
                    <DropdownMenu>
                      <DropdownMenuTrigger data-testid={`rep-menu-${r.id}`}><MoreHorizontal size={16} /></DropdownMenuTrigger>
                      <DropdownMenuContent align="end" className="rounded-none">
                        <DropdownMenuItem onClick={() => toggleActive(r)}>
                          {r.is_active ? <UserX size={14} className="mr-2" /> : <UserCheck size={14} className="mr-2" />}
                          {r.is_active ? "Suspend" : "Reactivate"}
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => resetPassword(r)}>
                          <KeyRound size={14} className="mr-2" /> Reset password
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </Td>
                </tr>
              ))}
              {reps.length === 0 && (
                <tr><Td colSpan={6} className="text-center py-10 text-[#52525B]">No representatives yet.</Td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

const Field = ({ label, children }) => (
  <div><Label className="text-[11px] uppercase tracking-widest text-[#52525B]">{label}</Label><div className="mt-2">{children}</div></div>
);
const Th = ({ children }) => <th className="px-6 py-4 text-[11px] uppercase tracking-widest text-[#52525B] font-medium">{children}</th>;
const Td = ({ children, className = "", colSpan }) => <td colSpan={colSpan} className={`px-6 py-4 text-[#0A0A0A] ${className}`}>{children}</td>;
