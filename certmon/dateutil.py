from __future__ import annotations

from calendar import monthrange
from datetime import date


def add_months(start: date, months: int) -> date:
	if months == 0:
		return start
	year = start.year + (start.month - 1 + months) // 12
	month = (start.month - 1 + months) % 12 + 1
	day = start.day
	last_day = monthrange(year, month)[1]
	if day > last_day:
		day = last_day
	return date(year, month, day)

