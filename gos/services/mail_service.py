"""Envío de correo vía SMTP (stdlib). En testing registra sin enviar."""

from __future__ import annotations

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from gos import env

_sent_log: list[dict] = []


def clear_sent_log() -> None:
    _sent_log.clear()


def get_sent_log() -> list[dict]:
    return list(_sent_log)


def smtp_configured() -> bool:
    if env.is_testing():
        return True
    return bool(env.smtp_host())


def send_email(
    *,
    to: list[str],
    subject: str,
    body_text: str,
    body_html: str | None = None,
) -> bool:
    """Envía un correo. Retorna True si se envió (o simuló en testing)."""
    recipients = [e.strip().lower() for e in to if e and e.strip()]
    if not recipients:
        return False

    if env.is_testing():
        _sent_log.append({"to": recipients, "subject": subject, "body": body_text})
        return True

    host = env.smtp_host()
    if not host:
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = env.smtp_from()
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(body_text, "plain", "utf-8"))
    if body_html:
        msg.attach(MIMEText(body_html, "html", "utf-8"))

    port = env.smtp_port()
    use_tls = env.smtp_tls()
    user = env.smtp_user()
    password = env.smtp_password()

    if use_tls:
        server = smtplib.SMTP(host, port, timeout=30)
        server.ehlo()
        server.starttls()
        server.ehlo()
    else:
        server = smtplib.SMTP_SSL(host, port, timeout=30)

    try:
        if user and password:
            server.login(user, password)
        server.sendmail(env.smtp_from(), recipients, msg.as_string())
        return True
    finally:
        server.quit()
