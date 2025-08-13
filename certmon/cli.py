from __future__ import annotations

import argparse
import os
import sys
from datetime import date, datetime
from pathlib import Path

from .config import Config, load_config, try_load_config
from .db import Database
from .dateutil import add_months
from .logic import send_due_reminders
from .emailer import send_email


def _parse_date(yyyy_mm_dd: str) -> date:
	try:
		return datetime.strptime(yyyy_mm_dd, "%Y-%m-%d").date()
	except ValueError as e:
		raise argparse.ArgumentTypeError(f"无效日期格式: {yyyy_mm_dd}，期望 YYYY-MM-DD") from e


def _resolve_db_path(config: Config | None) -> str:
    # 统一与 Web 一致：相对路径一律以项目根目录（包上级目录）为基准
    raw_path = config.app.database_path if config is not None else "data/certmon.db"
    p = Path(raw_path)
    if p.is_absolute():
        return p.as_posix()
    base_dir = Path(__file__).resolve().parent.parent
    return (base_dir / p).as_posix()


def cmd_init_db(args: argparse.Namespace) -> int:
	config = try_load_config(args.config)
	db = Database(_resolve_db_path(config))
	db.initialize_schema()
	print(f"数据库已初始化: {Path(_resolve_db_path(config)).as_posix()}")
	return 0


def cmd_add(args: argparse.Namespace) -> int:
	config = try_load_config(args.config)
	db = Database(_resolve_db_path(config))
	if args.expires is not None:
		expires_on = _parse_date(args.expires)
		acquired_on = expires_on
		valid_months = 0
	else:
		if args.acquired is None or args.months is None:
			raise argparse.ArgumentTypeError("新模式需要同时提供 --acquired 与 --months")
		acquired_on = _parse_date(args.acquired)
		try:
			valid_months = int(args.months)
		except Exception as e:
			raise argparse.ArgumentTypeError("有效月数必须为正整数") from e
		if valid_months <= 0:
			raise argparse.ArgumentTypeError("有效月数必须为正整数")
		expires_on = add_months(acquired_on, valid_months)
	new_id = db.add_certificate(args.name, args.email, acquired_on, valid_months, expires_on, args.notes)
	print(f"已添加，id={new_id}，到期日={expires_on.strftime('%Y-%m-%d')}")
	return 0


def cmd_list(args: argparse.Namespace) -> int:
	config = try_load_config(args.config)
	db = Database(_resolve_db_path(config))
	records = db.list_certificates()
	if not records:
		print("暂无记录")
		return 0
	print("id\tname\temail\tacquired_on\tmonths\texpires_on\tlast_reminded_on")
	for r in records:
		last_day = r.last_reminded_on.strftime("%Y-%m-%d") if r.last_reminded_on else "-"
		print(f"{r.id}\t{r.name}\t{r.email}\t{r.acquired_on.strftime('%Y-%m-%d')}\t{r.valid_months}\t{r.expires_on.strftime('%Y-%m-%d')}\t{last_day}")
	return 0


def cmd_remove(args: argparse.Namespace) -> int:
	config = try_load_config(args.config)
	db = Database(_resolve_db_path(config))
	success = db.remove_certificate(int(args.id))
	if success:
		print("已删除")
		return 0
	print("未找到指定 id")
	return 1


def cmd_send_reminders(args: argparse.Namespace) -> int:
	config = load_config(args.config)
	db = Database(_resolve_db_path(config))
	now = date.today()
	count = send_due_reminders(config, db, now)
	print(f"已发送提醒: {count} 封")
	return 0


def cmd_send_test(args: argparse.Namespace) -> int:
	config = load_config(args.config)
	to_email = args.to
	subject = args.subject or "CertMon 测试邮件"
	body = args.body or "这是一封来自 CertMon 的测试邮件。"
	try:
		send_email(config.smtp, to_email, subject, body)
		print("测试邮件发送成功")
		return 0
	except Exception as e:
		print(f"测试邮件发送失败: {e}")
		return 2


def build_parser() -> argparse.ArgumentParser:
	parser = argparse.ArgumentParser(
		prog="certmon",
		description="证书到期提醒服务",
	)
	parser.add_argument(
		"-C",
		"--chdir",
		help="在执行前切换至该目录",
		default=None,
	)
	parser.add_argument(
		"-c",
		"--config",
		help="配置文件路径 (默认: config.json)",
		default="config.json",
	)
	sp = parser.add_subparsers(dest="cmd", required=True)

	sp_init = sp.add_parser("init-db", help="初始化数据库")
	sp_init.set_defaults(func=cmd_init_db)

	sp_add = sp.add_parser("add", help="添加证书记录")
	sp_add.add_argument("--name", required=True, help="证书名称/类目")
	sp_add.add_argument("--email", required=True, help="接收提醒邮箱")
	group = sp_add.add_mutually_exclusive_group(required=True)
	group.add_argument("--expires", help="旧模式：直接指定到期日期 YYYY-MM-DD")
	group.add_argument("--acquired", help="新模式：获取日期 YYYY-MM-DD")
	sp_add.add_argument("--months", type=int, required=False, help="新模式：有效月数（正整数，如 14/24）")
	sp_add.add_argument("--notes", required=False, default=None, help="备注")
	sp_add.set_defaults(func=cmd_add)

	sp_list = sp.add_parser("list", help="列出证书记录")
	sp_list.set_defaults(func=cmd_list)

	sp_rm = sp.add_parser("remove", help="按 id 删除证书记录")
	sp_rm.add_argument("--id", required=True, help="证书 id")
	sp_rm.set_defaults(func=cmd_remove)

	sp_send = sp.add_parser("send-reminders", help="发送到期提醒")
	sp_send.set_defaults(func=cmd_send_reminders)

	sp_test = sp.add_parser("send-test", help="发送测试邮件以验证 SMTP 配置")
	sp_test.add_argument("--to", required=True, help="收件人邮箱")
	sp_test.add_argument("--subject", required=False, help="主题，默认：CertMon 测试邮件")
	sp_test.add_argument("--body", required=False, help="正文，默认：测试邮件内容")
	sp_test.set_defaults(func=cmd_send_test)

	return parser


def main(argv: list[str] | None = None) -> int:
	argv = list(sys.argv[1:] if argv is None else argv)
	parser = build_parser()
	args = parser.parse_args(argv)
	if args.chdir:
		os.chdir(args.chdir)
	return args.func(args)


if __name__ == "__main__":
	sys.exit(main())

