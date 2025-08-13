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
		return render_template("index.html", records=records)

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
			valid_months = int(valid_months_str)
			if valid_months <= 0:
				raise ValueError("valid months must be positive")
		except Exception:
			flash("日期格式应为 YYYY-MM-DD，且有效月数为正整数", "error")
			return redirect(url_for("index"))

		expires_on = add_months(acquired_on, valid_months)
		Database(db_path).add_certificate(name, email, acquired_on, valid_months, expires_on, notes)
		flash("已新增证书", "success")
		return redirect(url_for("index"))

	return app


def main() -> None:
	app = create_app()
	app.run(host="0.0.0.0", port=8000, debug=False)


if __name__ == "__main__":
	main()

