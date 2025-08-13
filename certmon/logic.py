from __future__ import annotations

from datetime import date, datetime
from typing import List

from .config import Config
from .db import Certificate, Database
from .emailer import send_email


def _days_until(expiry: date, today: date) -> int:
	return (expiry - today).days


def send_due_reminders(config: Config, db: Database, today: date) -> int:
	window = int(config.app.reminder_window_days)
	due: List[Certificate] = db.query_due_for_reminders(today, window)
	sent = 0
	for cert in due:
		if cert.last_reminded_on == today:
			continue
		days_left = _days_until(cert.expires_on, today)
		if days_left < 0:
			continue
		subject = f"证书到期提醒: {cert.name}"
		body = (
			f"证书: {cert.name}\n"
			f"到期日期: {cert.expires_on.strftime('%Y-%m-%d')}\n"
			f"剩余天数: {days_left} 天\n"
			f"备注: {cert.notes or '-'}\n\n"
			f"此邮件由证书到期提醒服务自动发送。"
		)
		send_email(config.smtp, cert.email, subject, body)
		db.set_last_reminded_today(cert.id, today)
		sent += 1
	return sent

