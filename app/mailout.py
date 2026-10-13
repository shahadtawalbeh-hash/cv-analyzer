from __future__ import annotations

import os
import re
from urllib.parse import quote

import httpx


def _addr_ok(addr: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", addr.strip()))


def _send_web3forms(to_addr: str, subject: str, body: str) -> None:
    key = (os.environ.get("WEB3FORMS_ACCESS_KEY") or "").strip()
    if not key:
        raise RuntimeError("WEB3FORMS_ACCESS_KEY missing")
    full_body = (
        f"Recipient typed in the app: {to_addr}\n\n---\n\n{body}"
    )
    payload = {
        "access_key": key,
        "subject": subject,
        "message": full_body,
        "from_name": "CV Fitboard",
    }
    try:
        resp = httpx.post(
            "https://api.web3forms.com/submit",
            json=payload,
            headers={"Accept": "application/json", "User-Agent": "CVFitboard/1.0"},
            timeout=45.0,
        )
    except httpx.HTTPError as exc:
        raise RuntimeError(f"Web3Forms request failed: {exc}") from exc

    if resp.status_code >= 400:
        raise RuntimeError(f"Web3Forms returned {resp.status_code}: {resp.text[:200]}")
    try:
        data = resp.json()
    except Exception:
        return
    if isinstance(data, dict) and not data.get("success"):
        raise RuntimeError(data.get("message") or "Web3Forms refused the send.")


def _send_formsubmit(to_addr: str, subject: str, body: str) -> None:
    addr = to_addr.strip()
    sender = (os.environ.get("FORMSUBMIT_FROM") or "cv-fitboard@local").strip()
    payload = {
        "name": "CV Fitboard",
        "email": sender,
        "message": body,
        "_subject": subject,
        "_captcha": "false",
    }
    headers_json = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36"
        ),
        "Origin": "https://formsubmit.co",
        "Referer": "https://formsubmit.co/",
    }
    urls = [
        f"https://formsubmit.co/ajax/{quote(addr, safe='')}",
        f"https://formsubmit.co/ajax/{addr}",
    ]
    last_status: int | None = None
    for url in urls:
        for use_json in (True, False):
            try:
                if use_json:
                    resp = httpx.post(
                        url, json=payload, headers=headers_json, timeout=45.0
                    )
                else:
                    h2 = {k: v for k, v in headers_json.items() if k != "Content-Type"}
                    h2["Content-Type"] = "application/x-www-form-urlencoded"
                    resp = httpx.post(url, data=payload, headers=h2, timeout=45.0)
                last_status = resp.status_code
                if resp.status_code < 400:
                    try:
                        data = resp.json()
                    except Exception:
                        return
                    if isinstance(data, dict):
                        s = data.get("success")
                        if s is False or s == "false":
                            raise RuntimeError(
                                data.get("message") or "FormSubmit error."
                            )
                    return
            except httpx.HTTPError:
                continue
    raise RuntimeError(
        f"FormSubmit failed (last HTTP {last_status}). "
        "521 usually means their edge blocked this machine. "
        "Use WEB3FORMS_ACCESS_KEY instead (free, web3forms.com)."
    )


def _send_smtp(to_addr: str, subject: str, body: str) -> None:
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    host = os.environ.get("SMTP_HOST", "").strip()
    port = int(os.environ.get("SMTP_PORT", "587") or "587")
    user = os.environ.get("SMTP_USER", "").strip()
    password = os.environ.get("SMTP_PASS", "").strip()
    mail_from = (os.environ.get("SMTP_FROM") or user).strip()

    if not host or not user or not password:
        raise RuntimeError("SMTP is not fully configured.")

    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = mail_from
    msg["To"] = to_addr
    msg.attach(MIMEText(body, "plain", "utf-8"))

    with smtplib.SMTP(host, port, timeout=30) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(user, password)
        server.sendmail(mail_from, [to_addr], msg.as_string())


def send_summary_email(to_addr: str, subject: str, body: str) -> None:
    to_addr = to_addr.strip()
    if not _addr_ok(to_addr):
        raise ValueError("That does not look like a real email address.")

    force_smtp = (os.environ.get("MAIL_USE_SMTP") or "").strip().lower() in (
        "1",
        "true",
        "yes",
    )
    smtp_host = (os.environ.get("SMTP_HOST") or "").strip()
    web3 = (os.environ.get("WEB3FORMS_ACCESS_KEY") or "").strip()

    if force_smtp:
        _send_smtp(to_addr, subject, body)
        return
    if web3:
        _send_web3forms(to_addr, subject, body)
        return
    if smtp_host:
        _send_smtp(to_addr, subject, body)
        return
    _send_formsubmit(to_addr, subject, body)
