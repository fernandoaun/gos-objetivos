"""Wrapper mail QDV → GOS."""

from __future__ import annotations

from typing import Any

from gos.services import mail_service as gos_mail


def is_mail_fully_configured(app: Any = None) -> bool:  # noqa: ARG001
    return gos_mail.smtp_configured()


def enviar_mail(
    *,
    to: list[str] | str,
    subject: str,
    body_text: str = "",
    body_html: str | None = None,
    **kwargs: Any,
) -> bool:
    recipients = to if isinstance(to, list) else [to]
    return gos_mail.send_email(
        to=recipients,
        subject=subject,
        body_text=body_text or (body_html or ""),
        body_html=body_html,
    )
