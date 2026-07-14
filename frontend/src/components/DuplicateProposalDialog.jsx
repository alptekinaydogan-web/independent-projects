import { useState, useEffect } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import api, { formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { Send } from "lucide-react";

/**
 * Dialog to revise a proposal by duplicating it. Preserves everything from the
 * original and lets the rep modify only the fields that changed. The parent
 * proposal remains untouched — a fresh proposal is created with status="revised"
 * and `parent_proposal_id` back-linking to the source.
 *
 * Props:
 *   kind: "banner" | "sponsorship"
 *   original: the proposal being revised
 */
export default function DuplicateProposalDialog({ kind, original, open, onOpenChange, onDone }) {
  const isBanner = kind === "banner";
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState(defaults(original, isBanner));

  useEffect(() => { setForm(defaults(original, isBanner)); }, [original, isBanner]);

  if (!original) return null;

  const submit = async () => {
    const overrides = isBanner ? {
      proposal_name: form.proposal_name,
      client_reference: form.client_reference,
      impressions: form.impressions === "" ? null : Number(form.impressions),
      start_date: form.start_date || undefined,
      end_date: form.end_date || undefined,
      offer_amount_usd: Number(form.offer_amount_usd),
      notes: form.notes,
    } : {
      proposal_name: form.proposal_name,
      client_reference: form.client_reference,
      offer_amount_usd: Number(form.offer_amount_usd),
      notes: form.notes,
      // episodes stay unchanged in this dialog (must revisit TV detail page to change)
    };
    if (!overrides.offer_amount_usd || overrides.offer_amount_usd <= 0) {
      toast.error("Offer amount must be positive");
      return;
    }
    setBusy(true);
    try {
      const endpoint = isBanner
        ? `/campaigns/${original.id}/duplicate`
        : `/sponsorships/${original.id}/duplicate`;
      const r = await api.post(endpoint, overrides);
      toast.success("Revised proposal submitted — awaiting admin review.");
      onOpenChange(false);
      onDone && onDone(r.data);
    } catch (e) {
      toast.error(formatApiError(e.response?.data?.detail));
    } finally { setBusy(false); }
  };

  const inventoryLine = isBanner
    ? `${original.network_name} · ${original.position_name}`
    : `${original.tv_project_title} · ${original.episode_count || (original.episode_numbers || []).length} episode(s)`;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xl rounded-none border border-[#E4E4E1] p-0 bg-white" data-testid="duplicate-dialog">
        <DialogHeader className="px-6 pt-6 pb-4 border-b border-[#E4E4E1] text-left">
          <div className="imh-eyebrow">Duplicate & revise</div>
          <DialogTitle className="font-editorial text-2xl">Resubmit an updated proposal</DialogTitle>
          <DialogDescription className="text-xs text-[#52525B]">
            {inventoryLine}. Adjust only what changed — everything else is preserved from the original.
          </DialogDescription>
        </DialogHeader>

        <div className="px-6 py-5 space-y-4">
          <F label="Proposal name">
            <Input data-testid="dup-name" value={form.proposal_name}
                    onChange={e => setForm({ ...form, proposal_name: e.target.value })} />
          </F>
          <F label="Client reference (private)">
            <Input data-testid="dup-client" value={form.client_reference}
                    onChange={e => setForm({ ...form, client_reference: e.target.value })} />
          </F>
          <F label="Revised offer to Independent Media Network (USD)">
            <Input data-testid="dup-offer" type="number" value={form.offer_amount_usd}
                    onChange={e => setForm({ ...form, offer_amount_usd: e.target.value })} />
          </F>
          {isBanner && (
            <>
              <F label="Requested impressions (optional)">
                <Input data-testid="dup-impressions" type="number" value={form.impressions}
                        onChange={e => setForm({ ...form, impressions: e.target.value })} />
              </F>
              <div className="grid grid-cols-2 gap-3">
                <F label="Start date">
                  <Input data-testid="dup-start" type="date" value={form.start_date}
                          onChange={e => setForm({ ...form, start_date: e.target.value })} />
                </F>
                <F label="End date">
                  <Input data-testid="dup-end" type="date" value={form.end_date}
                          onChange={e => setForm({ ...form, end_date: e.target.value })} />
                </F>
              </div>
            </>
          )}
          <F label="Notes for the administrator">
            <Textarea data-testid="dup-notes" rows={3} className="rounded-none" value={form.notes}
                       onChange={e => setForm({ ...form, notes: e.target.value })} />
          </F>
        </div>

        <DialogFooter className="px-6 py-4 border-t border-[#E4E4E1] flex-row justify-end gap-2">
          <Button variant="outline" onClick={() => onOpenChange(false)} data-testid="dup-cancel"
                  className="rounded-none border-[#E4E4E1]">Cancel</Button>
          <Button onClick={submit} disabled={busy} data-testid="dup-submit"
                  className="rounded-none bg-[#0033A0] hover:bg-[#002277] text-white">
            {busy ? "Submitting…" : "Submit revised proposal"} <Send size={13} className="ml-2" />
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function defaults(o, isBanner) {
  if (!o) return {};
  const strip = (s) => (s ? String(s).slice(0, 10) : "");
  return {
    proposal_name: o.campaign_name || o.proposal_name || "",
    client_reference: o.client_reference || o.client_name || "",
    offer_amount_usd: o.offer_amount_usd ?? "",
    impressions: o.impressions ?? "",
    start_date: strip(o.start_date),
    end_date: strip(o.end_date),
    notes: o.notes || "",
  };
}

const F = ({ label, children }) => (
  <div>
    <Label className="text-[11px] uppercase tracking-widest text-[#52525B]">{label}</Label>
    <div className="mt-2">{children}</div>
  </div>
);
