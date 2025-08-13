from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterable, List, Optional, Tuple


@dataclass
class Certificate:
	id: int
	name: str
	email: str
	acquired_on: date
	valid_months: int
	expires_on: date
	notes: Optional[str]
	last_reminded_on: Optional[date]
	created_at: datetime
	updated_at: datetime


class Database:
	def __init__(self, database_path: str) -> None:
		self._path = Path(database_path)
		self._path.parent.mkdir(parents=True, exist_ok=True)

	def connect(self) -> sqlite3.Connection:
		conn = sqlite3.connect(self._path.as_posix())
		conn.row_factory = sqlite3.Row
		return conn

	def initialize_schema(self) -> None:
		with self.connect() as conn:
			conn.execute(
				"""
				CREATE TABLE IF NOT EXISTS certificates (
					id INTEGER PRIMARY KEY AUTOINCREMENT,
					name TEXT NOT NULL,
					email TEXT NOT NULL,
					acquired_on TEXT NOT NULL,
					valid_months INTEGER NOT NULL,
					expires_on TEXT NOT NULL,
					notes TEXT,
					last_reminded_on TEXT,
					created_at TEXT NOT NULL,
					updated_at TEXT NOT NULL
				);
				"""
			)
			conn.execute(
				"""
				CREATE INDEX IF NOT EXISTS idx_certificates_expires_on
				ON certificates (expires_on);
				"""
			)

	@staticmethod
	def _today_string(d: Optional[date] = None) -> str:
		dt = d or date.today()
		return dt.strftime("%Y-%m-%d")

	@staticmethod
	def _now_string() -> str:
		return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

	def add_certificate(self, name: str, email: str, acquired_on: date, valid_months: int, expires_on: date, notes: Optional[str]) -> int:
		with self.connect() as conn:
			cursor = conn.execute(
				"""
				INSERT INTO certificates (name, email, acquired_on, valid_months, expires_on, notes, last_reminded_on, created_at, updated_at)
				VALUES (?, ?, ?, ?, ?, ?, NULL, ?, ?)
				""",
				(
					name,
					email,
					acquired_on.strftime("%Y-%m-%d"),
					int(valid_months),
					expires_on.strftime("%Y-%m-%d"),
					notes,
					self._now_string(),
					self._now_string(),
				),
			)
			return int(cursor.lastrowid)

	def list_certificates(self) -> List[Certificate]:
		with self.connect() as conn:
			rows = conn.execute(
				"SELECT id, name, email, acquired_on, valid_months, expires_on, notes, last_reminded_on, created_at, updated_at FROM certificates ORDER BY date(expires_on) ASC, id ASC"
			).fetchall()
			result: List[Certificate] = []
			for r in rows:
				result.append(
					Certificate(
						id=int(r["id"]),
						name=str(r["name"]),
						email=str(r["email"]),
						acquired_on=datetime.strptime(str(r["acquired_on"]), "%Y-%m-%d").date(),
						valid_months=int(r["valid_months"]),
						expires_on=datetime.strptime(str(r["expires_on"]), "%Y-%m-%d").date(),
						notes=(str(r["notes"]) if r["notes"] is not None else None),
						last_reminded_on=(
							datetime.strptime(str(r["last_reminded_on"]), "%Y-%m-%d").date()
							if r["last_reminded_on"]
							else None
						),
						created_at=datetime.strptime(str(r["created_at"]), "%Y-%m-%dT%H:%M:%SZ"),
						updated_at=datetime.strptime(str(r["updated_at"]), "%Y-%m-%dT%H:%M:%SZ"),
					)
				)
			return result

	def remove_certificate(self, certificate_id: int) -> bool:
		with self.connect() as conn:
			cursor = conn.execute("DELETE FROM certificates WHERE id = ?", (certificate_id,))
			return cursor.rowcount > 0

	def set_last_reminded_today(self, certificate_id: int, today: Optional[date] = None) -> None:
		with self.connect() as conn:
			conn.execute(
				"UPDATE certificates SET last_reminded_on = ?, updated_at = ? WHERE id = ?",
				(self._today_string(today), self._now_string(), certificate_id),
			)

	def query_due_for_reminders(self, today: date, reminder_window_days: int) -> List[Certificate]:
		start = self._today_string(today)
		with self.connect() as conn:
			rows = conn.execute(
				"""
				SELECT id, name, email, acquired_on, valid_months, expires_on, notes, last_reminded_on, created_at, updated_at
				FROM certificates
				WHERE date(expires_on) >= date(?)
				  AND date(expires_on) <= date(?, '+' || ? || ' days')
				ORDER BY date(expires_on) ASC, id ASC
				""",
				(start, start, reminder_window_days),
			).fetchall()
			result: List[Certificate] = []
			for r in rows:
				cert = Certificate(
					id=int(r["id"]),
					name=str(r["name"]),
					email=str(r["email"]),
					acquired_on=datetime.strptime(str(r["acquired_on"]), "%Y-%m-%d").date(),
					valid_months=int(r["valid_months"]),
					expires_on=datetime.strptime(str(r["expires_on"]), "%Y-%m-%d").date(),
					notes=(str(r["notes"]) if r["notes"] is not None else None),
					last_reminded_on=(
						datetime.strptime(str(r["last_reminded_on"]), "%Y-%m-%d").date()
						if r["last_reminded_on"]
						else None
					),
					created_at=datetime.strptime(str(r["created_at"]), "%Y-%m-%dT%H:%M:%SZ"),
					updated_at=datetime.strptime(str(r["updated_at"]), "%Y-%m-%dT%H:%M:%SZ"),
				)
				result.append(cert)
			return result

