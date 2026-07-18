"""Email delivery via Resend. Fully environment-variable driven.

Set RESEND_API_KEY and RESEND_FROM_EMAIL in .env to enable delivery.
When RESEND_API_KEY is empty (dev), reset links are logged instead of sent
so the flow remains testable without external dependency.
"""
import asyncio
import base64
import resend

from core import logger, RESEND_API_KEY, RESEND_FROM_EMAIL, FRONTEND_URL

if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY


def _reset_link(token: str) -> str:
    return f"{FRONTEND_URL}/reset-password?token={token}" if FRONTEND_URL else f"/reset-password?token={token}"


def _reset_html(name: str, reset_link: str) -> str:
    return f"""
    <table width="100%" cellpadding="0" cellspacing="0" style="background:#F9F9F6;padding:32px 0;font-family:Helvetica,Arial,sans-serif;">
      <tr><td align="center">
        <table width="560" cellpadding="0" cellspacing="0" style="background:#ffffff;border:1px solid #E4E4E1;">
          <tr><td style="padding:32px 40px 8px 40px;">
            <div style="font-size:11px;letter-spacing:0.24em;text-transform:uppercase;color:#52525B;">Independent Projects</div>
            <h1 style="font-family:Georgia,serif;font-size:28px;font-weight:600;margin:12px 0 0 0;color:#0A0A0A;">Reset your password</h1>
          </td></tr>
          <tr><td style="padding:16px 40px 8px 40px;color:#0A0A0A;font-size:15px;line-height:1.6;">
            <p style="margin:0 0 16px 0;">Hi {name or 'there'},</p>
            <p style="margin:0 0 16px 0;">We received a request to reset the password for your Independent Projects account. This link is valid for 60 minutes.</p>
          </td></tr>
          <tr><td style="padding:16px 40px 24px 40px;">
            <a href="{reset_link}" style="display:inline-block;background:#0033A0;color:#ffffff;text-decoration:none;padding:14px 24px;font-size:14px;letter-spacing:0.02em;">Reset password &rarr;</a>
          </td></tr>
          <tr><td style="padding:0 40px 32px 40px;color:#52525B;font-size:12px;line-height:1.6;">
            <p style="margin:0 0 8px 0;">If you didn&apos;t request this, you can safely ignore this email.</p>
            <p style="margin:0;word-break:break-all;">Or paste this link into your browser:<br/><span style="font-family:monospace;color:#0033A0;">{reset_link}</span></p>
          </td></tr>
          <tr><td style="border-top:1px solid #E4E4E1;padding:16px 40px;font-size:11px;letter-spacing:0.14em;text-transform:uppercase;color:#A1A1AA;">&copy; Independent Media Network &middot; Confidential</td></tr>
        </table>
      </td></tr>
    </table>
    """


async def send_password_reset_email(to_email: str, name: str, token: str) -> bool:
    link = _reset_link(token)
    if not RESEND_API_KEY:
        logger.info(f"[PASSWORD RESET · no RESEND_API_KEY] link for {to_email}: {link}")
        return False
    try:
        await asyncio.to_thread(resend.Emails.send, {
            "from": RESEND_FROM_EMAIL,
            "to": [to_email],
            "subject": "Reset your Independent Projects password",
            "html": _reset_html(name, link),
        })
        logger.info(f"password reset email sent to {to_email}")
        return True
    except Exception as e:
        logger.error(f"resend send failed for {to_email}: {e}")
        logger.info(f"[FALLBACK · resend error] link for {to_email}: {link}")
        return False

# ---------------------------------------------------------------------------
# Approved commercial proposal — deliver the branded PDF straight to the rep.
# ---------------------------------------------------------------------------
def _proposal_link(kind: str, proposal_id: str) -> str:
    path = "/rep/banners" if kind == "banner" else "/rep/sponsorships"
    return f"{FRONTEND_URL}{path}" if FRONTEND_URL else path


def _proposal_html(name: str, kind: str, proposal: dict, link: str) -> str:
    is_banner = kind == "banner"
    title = proposal.get("campaign_name") or proposal.get("proposal_name") or "Commercial proposal"
    inventory_line = (f"{proposal.get('network_name', '')} · {proposal.get('position_name', '')}"
                       if is_banner else
                       f"{proposal.get('tv_project_title', '')} · "
                       f"{proposal.get('episode_count') or len(proposal.get('episode_numbers') or [])} episode(s)")
    amount_str = f"${int(round(float(proposal.get('offer_amount_usd', 0)))):,}"
    reference = str(proposal.get("id", ""))[:8].upper()
    kind_label = "Banner campaign" if is_banner else "TV sponsorship"
    return f"""
    <table width="100%" cellpadding="0" cellspacing="0" style="background:#F9F9F6;padding:32px 0;font-family:Helvetica,Arial,sans-serif;">
      <tr><td align="center">
        <table width="560" cellpadding="0" cellspacing="0" style="background:#ffffff;border:1px solid #E4E4E1;">
          <tr><td style="padding:32px 40px 8px 40px;">
            <div style="font-size:11px;letter-spacing:0.24em;text-transform:uppercase;color:#52525B;">Independent Projects</div>
            <div style="font-size:11px;letter-spacing:0.24em;text-transform:uppercase;color:#166534;margin-top:6px;">Proposal approved</div>
            <h1 style="font-family:Georgia,serif;font-size:28px;font-weight:600;margin:14px 0 4px 0;color:#0A0A0A;">Your proposal is ready to share</h1>
            <div style="color:#52525B;font-size:13px;">{kind_label} · {inventory_line}</div>
          </td></tr>
          <tr><td style="padding:16px 40px 8px 40px;color:#0A0A0A;font-size:15px;line-height:1.6;">
            <p style="margin:0 0 16px 0;">Hi {name or 'there'},</p>
            <p style="margin:0 0 16px 0;">Independent Media Network has approved your commercial proposal <strong>{title}</strong>. Attached to this email is the signed proposal document — a client-ready presentation you can share with your customer immediately.</p>
          </td></tr>
          <tr><td style="padding:8px 40px;">
            <table width="100%" cellpadding="0" cellspacing="0" style="background:#F9F9F6;border-left:3px solid #0033A0;">
              <tr><td style="padding:16px 20px;">
                <div style="font-size:10px;letter-spacing:0.24em;text-transform:uppercase;color:#52525B;">Approved amount</div>
                <div style="font-family:Georgia,serif;font-size:24px;color:#0A0A0A;margin-top:4px;">{amount_str} USD</div>
                <div style="font-size:11px;color:#52525B;margin-top:8px;font-family:monospace;">Reference · {reference}</div>
              </td></tr>
            </table>
          </td></tr>
          <tr><td style="padding:20px 40px 8px 40px;">
            <a href="{link}" style="display:inline-block;background:#0033A0;color:#ffffff;text-decoration:none;padding:14px 24px;font-size:14px;letter-spacing:0.02em;">Open in Media Hub &rarr;</a>
          </td></tr>
          <tr><td style="padding:16px 40px 24px 40px;color:#52525B;font-size:12px;line-height:1.6;">
            <p style="margin:0;">You can also re-download the PDF at any time from your dashboard.</p>
          </td></tr>
          <tr><td style="border-top:1px solid #E4E4E1;padding:16px 40px;font-size:11px;letter-spacing:0.14em;text-transform:uppercase;color:#A1A1AA;">&copy; Independent Media Network &middot; Confidential</td></tr>
        </table>
      </td></tr>
    </table>
    """


async def send_approved_proposal_email(to_email: str, name: str, kind: str,
                                        proposal: dict, pdf_bytes: bytes) -> bool:
    """Deliver the branded approval PDF as an attachment via Resend.

    Fire-and-forget from the caller's perspective — returns True on success and
    False on any failure (missing key, upstream error). Never raises.
    """
    if not to_email:
        return False
    link = _proposal_link(kind, proposal.get("id", ""))
    ref = str(proposal.get("id", ""))[:8].upper()
    filename = (f"IMN-proposal-{ref}.pdf" if kind == "banner"
                else f"IMN-sponsorship-{ref}.pdf")
    subject = ("Your commercial proposal has been approved · "
                + (proposal.get("campaign_name") or proposal.get("proposal_name") or ref))

    if not RESEND_API_KEY:
        logger.info(f"[APPROVED PROPOSAL · no RESEND_API_KEY] would email {to_email} "
                     f"(ref {ref}, {len(pdf_bytes)} bytes)")
        return False

    try:
        payload = {
            "from": RESEND_FROM_EMAIL,
            "to": [to_email],
            "subject": subject,
            "html": _proposal_html(name, kind, proposal, link),
            "attachments": [{
                "filename": filename,
                "content": base64.b64encode(pdf_bytes).decode("ascii"),
                "content_type": "application/pdf",
            }],
        }
        await asyncio.to_thread(resend.Emails.send, payload)
        logger.info(f"approved-proposal email sent to {to_email} (ref {ref})")
        return True
    except Exception as e:
        logger.error(f"resend approved-proposal send failed for {to_email}: {e}")
        return False

