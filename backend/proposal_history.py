"""Proposal lifecycle history helpers.

Every commercial proposal (banner in `campaigns`, TV sponsorship in
`sponsorships`) carries a `history` array that captures every lifecycle
transition. Each entry records:

    {
      "status": "submitted" | "revision_requested" | "revised" | "approved" |
                "rejected" | "archived",
      "at": iso-timestamp,
      "actor_id": str, "actor_name": str, "actor_role": "representative"|"admin"|"owner"|"system",
      "representative_feedback": str,  # visible to rep
      "internal_notes": str,           # admin-only
    }

Reps must never see `internal_notes` — use `strip_internal_notes()` before
returning any proposal-shaped document to a representative.
"""
from typing import Optional
from core import now_iso

REP_LIFECYCLE_STATUSES = (
    "submitted", "revision_requested", "revised", "approved", "rejected", "archived",
)

# Legacy `pending_review` is equivalent to "submitted" in the lifecycle vocabulary.
STATUS_LIFECYCLE_MAP = {
    "pending_review": "submitted",
}


def history_entry(status: str, actor: dict,
                  representative_feedback: str = "",
                  internal_notes: str = "") -> dict:
    """Build a single history record."""
    return {
        "status": status,
        "at": now_iso(),
        "actor_id": actor.get("id", ""),
        "actor_name": actor.get("name") or actor.get("email") or "system",
        "actor_role": actor.get("role", "system"),
        "representative_feedback": representative_feedback or "",
        "internal_notes": internal_notes or "",
    }


def strip_internal_notes(doc: Optional[dict]) -> Optional[dict]:
    """Return a copy of the proposal safe to expose to a representative.

    Removes `internal_notes` from top-level and from every history entry.
    """
    if not doc:
        return doc
    d = dict(doc)
    d.pop("internal_notes", None)
    if isinstance(d.get("history"), list):
        d["history"] = [
            {k: v for k, v in h.items() if k != "internal_notes"}
            for h in d["history"]
        ]
    return d


def resolve_feedback(body) -> str:
    """Pick representative_feedback, falling back to legacy admin_notes."""
    return (getattr(body, "representative_feedback", "") or getattr(body, "admin_notes", "") or "").strip()
