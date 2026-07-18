import { useEffect, useState } from "react";
import api, { formatApiError } from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogTrigger, DialogFooter } from "@/components/ui/dialog";
import { toast } from "sonner";
import { Plus, ShieldCheck, Trash2 } from "lucide-react";

const ROLE_BADGE = {
  owner: { bg: "#0A1128", color: "#FFFFFF", label: "OWNER" },
  admin: { bg: "#E6F2EA", color: "#166534", label: "ADMIN" },
};

export default function Admins() {
  const [admins, setAdmins] = useState([]);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ email: "", password: "", name: "" });

  const load = () => api.get("/owner/admins").then(r => setAdmins(r.data));
  useEffect(() => { load(); }, []);

  const create = async () => {
    try {
      await api.post("/owner/admins", form);
      toast.success("Administrator created");
      setOpen(false); setForm({ email: "", password: "", name: "" });
      await load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };

  const remove = async (a) => {
    if (!confirm(`Remove administrator ${a.email}?`)) return;
    try { await api.delete(`/owner/admins/${a.id}`); toast.success("Administrator removed"); await load(); }
    catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };

  return (
    <div>
      <PageHeader
        eyebrow="Ownership · Restricted"
        title="Administrators"
        description="Manage the humans with administrative access to Independent Projects. Only the owner can add or remove administrators."
        actions={
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
              <Button data-testid="new-admin-button" className="rounded-none h-10 bg-[#0033A0] hover:bg-[#002277] text-white">
                <Plus size={16} className="mr-2" /> New administrator
              </Button>
            </DialogTrigger>
            <DialogContent className="rounded-none border border-[#0A0A0A]">
              <DialogHeader>
                <DialogTitle className="font-editorial text-2xl">Invite an administrator</DialogTitle>
                <DialogDescription>Create a new administrator account with full access to manage the platform.</DialogDescription>
              </DialogHeader>
              <div className="grid grid-cols-1 gap-4 mt-2">
                <F label="Full name"><Input data-testid="admin-name" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} /></F>
                <F label="Email"><Input data-testid="admin-email" type="email" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} /></F>
                <F label="Initial password"><Input data-testid="admin-password" value={form.password} onChange={e => setForm({ ...form, password: e.target.value })} /></F>
              </div>
              <DialogFooter>
                <Button data-testid="admin-create-submit" onClick={create} className="rounded-none bg-[#0033A0] hover:bg-[#002277]">Create administrator</Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        }
      />
      <div className="px-10 py-10">
        <div className="imh-card overflow-hidden" data-testid="admins-table">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left border-b border-[#E4E4E1] bg-[#F9F9F6]">
                <Th>Name</Th><Th>Email</Th><Th>Role</Th><Th>Created</Th><Th></Th>
              </tr>
            </thead>
            <tbody>
              {admins.map(a => {
                const rb = ROLE_BADGE[a.role] || { bg: "#eee", color: "#000", label: a.role };
                return (
                  <tr key={a.id} className="border-b border-[#E4E4E1] last:border-b-0 hover:bg-[#F9F9F6]" data-testid={`admin-row-${a.id}`}>
                    <Td className="font-editorial text-base flex items-center gap-2">
                      {a.role === "owner" && <ShieldCheck size={14} className="text-[#0033A0]" />} {a.name}
                    </Td>
                    <Td className="font-mono-imh text-xs">{a.email}</Td>
                    <Td>
                      <span className="px-2 py-0.5 text-[10px] tracking-widest font-mono-imh" style={{ background: rb.bg, color: rb.color }}>{rb.label}</span>
                    </Td>
                    <Td className="font-mono-imh text-xs text-[#52525B]">{a.created_at?.slice(0, 10)}</Td>
                    <Td>
                      {a.role === "admin" && (
                        <button onClick={() => remove(a)} data-testid={`admin-remove-${a.id}`} className="text-[#991B1B] hover:opacity-70 inline-flex items-center gap-1 text-xs">
                          <Trash2 size={13} /> Remove
                        </button>
                      )}
                    </Td>
                  </tr>
                );
              })}
              {admins.length === 0 && (
                <tr><Td colSpan={5} className="text-center py-10 text-[#52525B]">No administrators.</Td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

const F = ({ label, children }) => <div><Label className="text-[11px] uppercase tracking-widest text-[#52525B]">{label}</Label><div className="mt-2">{children}</div></div>;
const Th = ({ children }) => <th className="px-6 py-4 text-[11px] uppercase tracking-widest text-[#52525B] font-medium">{children}</th>;
const Td = ({ children, className = "", colSpan }) => <td colSpan={colSpan} className={`px-6 py-4 text-[#0A0A0A] ${className}`}>{children}</td>;
