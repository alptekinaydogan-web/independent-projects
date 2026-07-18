"""Email delivery via Resend. Fully environment-variable driven.

Post-cleanup: the banner/sponsorship approval PDF email helper has been
removed. Only the password-reset email remains — Resend usage in the
platform is intentionally minimal.
"""
import asyncio
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
