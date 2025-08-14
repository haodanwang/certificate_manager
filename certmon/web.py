from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Tuple

from flask import Flask, redirect, render_template, request, url_for, flash, session, jsonify

from .config import load_config, try_load_config
from .dateutil import add_months
from .db import Database
from .auth import hash_password, verify_password


def create_app(config_path: str = "/etc/certmon/config.json") -> Flask:
	# 项目根目录（包上级目录）
	base_dir = Path(__file__).resolve().parent.parent
	# 配置文件路径：相对路径一律按项目根目录解析，避免不同工作目录导致读取不同配置
	conf_path = Path(config_path)
	if not conf_path.is_absolute():
		conf_path = base_dir / conf_path
	config = try_load_config(conf_path.as_posix())

	db_path = (config.app.database_path if config else "data/certmon.db")
	# 数据库路径：相对路径按项目根目录解析，确保稳定
	resolved = Path(db_path)
	if not resolved.is_absolute():
		resolved = base_dir / resolved
	db_path = resolved.as_posix()

	db = Database(db_path)
	db.initialize_schema()
	# 默认管理员：shanks / Huawei12#$ （仅在用户不存在时创建）
	try:
		if not Database(db_path).get_user_by_username("shanks"):
			pwd_hex, salt_hex = hash_password("Huawei12#$")
			Database(db_path).create_user("shanks", pwd_hex, salt_hex, True)
	except Exception:
		pass

	app = Flask(__name__)
	app.secret_key = "change-this-secret-key"

	@app.get("/")
	def index():
		if not session.get("uid"):
			return redirect(url_for("login"))
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
		if not session.get("uid"):
			return redirect(url_for("login"))
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

	@app.get("/settings")
	def settings_page():
		if not session.get("uid"):
			return redirect(url_for("login"))
		settings = Database(db_path).get_smtp_settings()
		return render_template("settings.html", settings=settings)

	@app.post("/settings")
	def save_settings():
		if not session.get("uid"):
			return redirect(url_for("login"))
		host = request.form.get("host") or None
		port = request.form.get("port")
		username = request.form.get("username") or None
		password = request.form.get("password") or None
		use_tls = request.form.get("use_tls")
		from_email = request.form.get("from_email") or None
		try:
			port_val = int(port) if port else None
			use_tls_val = True if use_tls == "on" else False
		except Exception:
			flash("参数不合法", "error")
			return redirect(url_for("settings_page"))
		try:
			Database(db_path).upsert_smtp_settings(host, port_val, username, password, use_tls_val, from_email)
			flash("SMTP 设置已保存", "success")
		except Exception as e:
			flash(f"保存失败: {e}", "error")
		return redirect(url_for("settings_page"))

	@app.post("/delete/<int:cid>")
	def delete(cert_id: int = None, cid: int = None):
		if not session.get("uid"):
			return redirect(url_for("login"))
		# Flask 2.x 传参兼容处理
		target_id = cid if cid is not None else cert_id
		ok = Database(db_path).remove_certificate(int(target_id))
		flash("已删除" if ok else "未找到该记录", "success" if ok else "error")
		return redirect(url_for("index"))

	@app.get("/login")
	def login():
		return render_template("login.html")

	@app.post("/login")
	def do_login():
		username = (request.form.get("username") or "").strip()
		password = (request.form.get("password") or "")
		db_obj = Database(db_path)
		user = db_obj.get_user_by_username(username)
		if user and verify_password(password, user.password_hex, user.salt_hex):
			session["uid"] = user.id
			session["is_admin"] = bool(user.is_admin)
			return redirect(url_for("index"))
		flash("用户名或密码错误", "error")
		return redirect(url_for("login"))

	@app.post("/logout")
	def logout():
		session.clear()
		return redirect(url_for("login"))

	# 仅管理员可调用：新增用户接口
	@app.post("/api/admin/users")
	def api_admin_create_user():
		if not session.get("uid") or not session.get("is_admin"):
			return jsonify({"error": "forbidden"}), 403
		data = request.get_json(silent=True) or {}
		username = (data.get("username") or "").strip()
		password = (data.get("password") or "")
		is_admin = bool(data.get("is_admin", False))
		if not username or not password:
			return jsonify({"error": "username and password required"}), 400
		if Database(db_path).get_user_by_username(username):
			return jsonify({"error": "user exists"}), 409
		pwd_hex, salt_hex = hash_password(password)
		uid = Database(db_path).create_user(username, pwd_hex, salt_hex, is_admin)
		return jsonify({"id": uid, "username": username, "is_admin": is_admin}), 201

	return app


def main() -> None:
	app = create_app()
	app.run(host="0.0.0.0", port=8000, debug=False)


if __name__ == "__main__":
	main()

