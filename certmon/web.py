from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Tuple

from flask import Flask, redirect, render_template, request, url_for, flash

from .config import load_config, try_load_config
from .dateutil import add_months
from .db import Database


def create_app(config_path: str = "config.json") -> Flask:
	config = try_load_config(config_path)
	db_path = (config.app.database_path if config else "data/certmon.db")
	db = Database(db_path)
	db.initialize_schema()

	app = Flask(__name__)
	app.secret_key = "change-this-secret-key"

	@app.get("/")
	def index():
		records = Database(db_path).list_certificates()
		today = date.today()
		vm = []
		for r in records:
			is_permanent = int(r.valid_months) < 0 or (r.expires_on.year >= 9999)
			if is_permanent:
				expires_label = "永不过期"
				days_left_label = "永不过期"
			else:
				delta_days = (r.expires_on - today).days
				expires_label = r.expires_on.strftime('%Y-%m-%d')
				days_left_label = f"{delta_days} 天"
			vm.append({
				"id": r.id,
				"name": r.name,
				"email": r.email,
				"acquired_on": r.acquired_on.strftime('%Y-%m-%d'),
				"valid_months": r.valid_months,
				"expires_label": expires_label,
				"days_left_label": days_left_label,
				"last_reminded_on": (r.last_reminded_on.strftime('%Y-%m-%d') if r.last_reminded_on else '-'),
			})
		return render_template("index.html", records=vm)

	@app.post("/add")
	def add():
		name = request.form.get("name", "").strip()
		email = request.form.get("email", "").strip()
		acquired_on_str = request.form.get("acquired_on", "").strip()
		valid_months_str = request.form.get("valid_months", "").strip()
		notes = request.form.get("notes", None)

		if not name or not email or not acquired_on_str or not valid_months_str:
			flash("请填写必要字段", "error")
			return redirect(url_for("index"))

		try:
			acquired_on = datetime.strptime(acquired_on_str, "%Y-%m-%d").date()
			if valid_months_str == "permanent":
				valid_months = -1
			else:
				valid_months = int(valid_months_str)
				if valid_months <= 0:
					raise ValueError("valid months must be positive")
		except Exception:
			flash("日期格式应为 YYYY-MM-DD，且有效月数为正整数或选择永久", "error")
			return redirect(url_for("index"))

		if valid_months < 0:
			# 永久：使用超远未来作为到期占位，避免进入提醒窗口
			expires_on = date(9999, 12, 31)
		else:
			expires_on = add_months(acquired_on, valid_months)
		Database(db_path).add_certificate(name, email, acquired_on, valid_months, expires_on, notes)
		flash("已新增证书", "success")
		return redirect(url_for("index"))

	@app.post("/delete/<int:cid>")
	def delete(cert_id: int = None, cid: int = None):
		# Flask 2.x 传参兼容处理
		target_id = cid if cid is not None else cert_id
		ok = Database(db_path).remove_certificate(int(target_id))
		flash("已删除" if ok else "未找到该记录", "success" if ok else "error")
		return redirect(url_for("index"))

	return app


def main() -> None:
	app = create_app()
	app.run(host="0.0.0.0", port=8000, debug=False)


if __name__ == "__main__":
	main()

