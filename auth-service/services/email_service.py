"""
Async email service using aiosmtplib.

Supports:
  - GoDaddy Workspace Email  (SMTP_HOST=smtpout.secureserver.net, SMTP_PORT=465, SMTP_USE_SSL=true)
  - Microsoft 365             (SMTP_HOST=smtp.office365.com,       SMTP_PORT=587, SMTP_USE_TLS=true, SMTP_USE_SSL=false)
  - Google Workspace          (SMTP_HOST=smtp.gmail.com,           SMTP_PORT=587, SMTP_USE_TLS=true, SMTP_USE_SSL=false)
"""
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def send_email(
    to_email: str,
    subject: str,
    html_body: str,
    text_body: str | None = None,
) -> bool:
    """
    Send an email via configured SMTP.
    Returns True on success, False on failure (never raises — logs the error instead).
    """
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM}>"
    msg["To"] = to_email

    if text_body:
        msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        await aiosmtplib.send(
            msg,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USERNAME,
            password=settings.SMTP_PASSWORD,
            use_tls=settings.SMTP_USE_SSL,   # True = wrap entire connection in SSL (port 465)
            start_tls=settings.SMTP_USE_TLS, # True = STARTTLS upgrade (port 587)
        )
        logger.info("Email sent to %s (subject: %s)", to_email, subject)
        return True
    except Exception as exc:
        logger.error("Failed to send email to %s: %s", to_email, exc)
        return False


async def send_password_reset_email(
    to_email: str,
    reset_link: str,
    org_name: str = "",
) -> bool:
    """Send the password-reset email with a secure one-time link."""
    subject = "Reset your authYantra password"

    html_body = f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Reset Your Password</title>
</head>
<body style="margin:0;padding:0;background:#f1f5f9;font-family:'Segoe UI',Roboto,Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="padding:40px 16px;">
    <tr>
      <td align="center">
        <table width="100%" cellpadding="0" cellspacing="0" style="max-width:520px;">

          <!-- Header -->
          <tr>
            <td align="center" style="padding-bottom:24px;">
              <table cellpadding="0" cellspacing="0">
                <tr>
                  <td style="background:#4f46e5;border-radius:12px;padding:12px 20px;">
                    <span style="color:#fff;font-size:18px;font-weight:700;letter-spacing:-0.3px;">
                      authYantra
                    </span>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Card -->
          <tr>
            <td style="background:#fff;border-radius:16px;padding:40px 36px;
                       box-shadow:0 1px 3px rgba(0,0,0,.1);">

              <h1 style="margin:0 0 8px;font-size:22px;font-weight:700;color:#0f172a;">
                Reset your password
              </h1>
              <p style="margin:0 0 24px;color:#64748b;font-size:14px;line-height:1.6;">
                {"We received a password reset request for your account" + (f" in <strong>{org_name}</strong>" if org_name else "") + "."}
                Click the button below — this link is valid for <strong>1&nbsp;hour</strong>
                and can only be used once.
              </p>

              <!-- CTA Button -->
              <table cellpadding="0" cellspacing="0" style="margin:0 0 28px;">
                <tr>
                  <td style="background:#4f46e5;border-radius:8px;">
                    <a href="{reset_link}"
                       style="display:inline-block;padding:14px 32px;color:#fff;
                              font-size:15px;font-weight:600;text-decoration:none;
                              letter-spacing:-0.2px;">
                      Reset Password
                    </a>
                  </td>
                </tr>
              </table>

              <!-- Fallback link -->
              <p style="margin:0 0 4px;color:#94a3b8;font-size:12px;">
                Or copy and paste this link into your browser:
              </p>
              <p style="margin:0 0 28px;word-break:break-all;">
                <a href="{reset_link}" style="color:#4f46e5;font-size:12px;">{reset_link}</a>
              </p>

              <hr style="border:none;border-top:1px solid #e2e8f0;margin:0 0 20px;" />

              <p style="margin:0;color:#94a3b8;font-size:12px;line-height:1.6;">
                If you didn't request a password reset, you can safely ignore this email —
                your password will not be changed. For security, this link expires in 1 hour.
              </p>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td align="center" style="padding-top:24px;">
              <p style="margin:0;color:#94a3b8;font-size:11px;">
                Sent by authYantra Identity Service &middot; noreply@marketyantra.com
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""

    text_body = (
        f"Reset your authYantra password\n\n"
        f"Click the link below to reset your password (valid for 1 hour):\n"
        f"{reset_link}\n\n"
        f"If you didn't request this, you can safely ignore this email."
    )

    return await send_email(to_email, subject, html_body, text_body)


async def send_invite_email(
    to_email: str,
    org_name: str,
    invite_link: str,
    role: str = "member",
    expires_hours: int = 72,
) -> bool:
    """Send an org invite email."""
    subject = f"You've been invited to join {org_name} on authYantra"

    html_body = f"""
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>Invitation</title></head>
<body style="margin:0;padding:0;background:#f1f5f9;font-family:'Segoe UI',Roboto,Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="padding:40px 16px;">
    <tr><td align="center">
      <table width="100%" cellpadding="0" cellspacing="0" style="max-width:520px;">
        <tr><td align="center" style="padding-bottom:24px;">
          <table cellpadding="0" cellspacing="0"><tr>
            <td style="background:#4f46e5;border-radius:12px;padding:12px 20px;">
              <span style="color:#fff;font-size:18px;font-weight:700;">authYantra</span>
            </td>
          </tr></table>
        </td></tr>
        <tr><td style="background:#fff;border-radius:16px;padding:40px 36px;box-shadow:0 1px 3px rgba(0,0,0,.1);">
          <h1 style="margin:0 0 8px;font-size:22px;font-weight:700;color:#0f172a;">
            You've been invited
          </h1>
          <p style="margin:0 0 24px;color:#64748b;font-size:14px;line-height:1.6;">
            You've been invited to join <strong>{org_name}</strong> as a
            <strong>{role}</strong>. This invite expires in <strong>{expires_hours}&nbsp;hours</strong>.
          </p>
          <table cellpadding="0" cellspacing="0" style="margin:0 0 28px;"><tr>
            <td style="background:#4f46e5;border-radius:8px;">
              <a href="{invite_link}" style="display:inline-block;padding:14px 32px;color:#fff;
                 font-size:15px;font-weight:600;text-decoration:none;">
                Accept Invitation
              </a>
            </td>
          </tr></table>
          <p style="margin:0 0 4px;color:#94a3b8;font-size:12px;">Or copy this link:</p>
          <p style="margin:0 0 28px;word-break:break-all;">
            <a href="{invite_link}" style="color:#4f46e5;font-size:12px;">{invite_link}</a>
          </p>
          <hr style="border:none;border-top:1px solid #e2e8f0;margin:0 0 20px;"/>
          <p style="margin:0;color:#94a3b8;font-size:12px;line-height:1.6;">
            If you weren't expecting this invitation, you can safely ignore this email.
          </p>
        </td></tr>
        <tr><td align="center" style="padding-top:24px;">
          <p style="margin:0;color:#94a3b8;font-size:11px;">
            Sent by authYantra Identity Service
          </p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body></html>
"""
    text_body = (
        f"You've been invited to join {org_name} as {role}.\n\n"
        f"Accept your invite: {invite_link}\n\n"
        f"This invite expires in {expires_hours} hours."
    )
    return await send_email(to_email, subject, html_body, text_body)
