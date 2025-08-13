from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class SMTPConfig:
	host: str
	port: int
	username: str
	password: str
	use_tls: bool
	from_email: str


@dataclass
class AppConfig:
	database_path: str = "data/certmon.db"
	reminder_window_days: int = 7


@dataclass
class Config:
	smtp: SMTPConfig
	app: AppConfig


def _load_json(path: Path) -> dict:
	with path.open("r", encoding="utf-8") as f:
		return json.load(f)


def load_config(config_path: str = "config.json") -> Config:
	path = Path(config_path)
	data = _load_json(path)

	smtp = SMTPConfig(
		host=data["smtp"]["host"],
		port=int(data["smtp"]["port"]),
		username=data["smtp"]["username"],
		password=data["smtp"]["password"],
		use_tls=bool(data["smtp"].get("use_tls", True)),
		from_email=data["smtp"]["from_email"],
	)
	app = AppConfig(
		database_path=data.get("app", {}).get("database_path", "data/certmon.db"),
		reminder_window_days=int(data.get("app", {}).get("reminder_window_days", 7)),
	)
	return Config(smtp=smtp, app=app)


def try_load_config(config_path: str = "config.json") -> Optional[Config]:
	path = Path(config_path)
	if not path.exists():
		return None
	return load_config(config_path)

