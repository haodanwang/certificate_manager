from __future__ import annotations

import smtplib
from email.message import EmailMessage
from typing import Optional
import ssl as _ssl

from .config import SMTPConfig


def _connect(smtp: SMTPConfig) -> smtplib.SMTP:
	# 基础校验：当需要加密（STARTTLS 或 SMTPS 465）时，Python 必须包含 ssl 支持
	needs_ssl = bool(smtp.use_tls) or int(smtp.port) == 465
	if needs_ssl and not hasattr(_ssl, "SSLContext"):
		raise RuntimeError(
			"当前 Python 缺少 SSL 支持，无法建立加密 SMTP 连接。请安装带 SSL 的 Python 或改用本机 MTA。"
		)

	if smtp.use_tls:
		server = smtplib.SMTP(smtp.host, smtp.port, timeout=30)
		server.ehlo()
		server.starttls()
		server.ehlo()
	else:
		if int(smtp.port) == 465:
			SMTP_SSL = getattr(smtplib, "SMTP_SSL", None)
			if SMTP_SSL is None:
				raise RuntimeError(
					"此 Python 不支持 SMTP_SSL，无法连接 465 端口。可改用 587 端口并将 use_tls 设为 true，或安装带 SSL 的 Python。"
				)
			server = SMTP_SSL(smtp.host, smtp.port, timeout=30)
		else:
			server = smtplib.SMTP(smtp.host, smtp.port, timeout=30)
	server.login(smtp.username, smtp.password)
	return server


def send_email(smtp: SMTPConfig, to_email: str, subject: str, body: str) -> None:
	msg = EmailMessage()
	msg["From"] = smtp.from_email
	msg["To"] = to_email
	msg["Subject"] = subject
	msg.set_content(body)

	server = _connect(smtp)
	try:
		server.send_message(msg)
	finally:
		server.quit()

