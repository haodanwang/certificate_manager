## 证书到期提醒服务（Linux 可运行）

一个轻量的 Python 程序，用于记录证书的名称/类目与到期时间，并在到期前 7 天内每日邮件提醒。

### 功能
- 记录证书：名称/类目、到期日期、接收提醒邮箱、备注
- 列表查看、删除
- 到期前 7 天内每日邮件提醒（通过 cron 定时执行）

### 运行环境
- Python 3.8+
- Linux 服务器（推荐使用 cron 定时任务）
 - 可选 Web 管理界面（Flask）

### 快速开始
1) 克隆或下载本项目到服务器，并进入目录。

2) 准备配置 `config.json`（可复制 `config.example.json` 并修改）：
```json
{
  "smtp": {
    "host": "smtp.example.com",
    "port": 587,
    "username": "user@example.com",
    "password": "REPLACE_WITH_REAL_PASSWORD",
    "use_tls": true,
    "from_email": "noreply@example.com"
  },
  "app": {
    "database_path": "data/certmon.db",
    "reminder_window_days": 7
  }
}
```

3) 初始化数据库：
```bash
python3 -m certmon.cli init-db
```

4) 添加一条证书记录：
```bash
python3 -m certmon.cli add --name "示例SSL证书" --email owner@example.com --expires 2025-09-30 --notes "生产环境网关"
```

5) 查看证书列表：
```bash
python3 -m certmon.cli list
```

6) 手动发送提醒（可先测试）：
```bash
python3 -m certmon.cli send-reminders
```

### Web 管理界面（可选）
- 安装依赖（需要 Flask）：
```bash
pip3 install -r requirements.txt
```
- 启动 Web：
```bash
python3 -m certmon.web
```
- 浏览器访问：`http://<服务器IP>:8000/`
- 页面支持：
  - 新增证书（获取日期 + 有效月数，自动计算到期日期）
  - 查看证书列表

### 关于已存在的数据库
若在添加 Web 与新 CLI 模式前已初始化过数据库（旧版没有 `acquired_on` 与 `valid_months` 字段），请删除旧数据库后重新初始化：
```bash
rm -f data/certmon.db && python3 -m certmon.cli init-db
```

### 设置定时任务（cron）
建议每天 09:00 执行一次提醒任务（每日一次，不会重复同日多发）：
```bash
crontab -e
```
写入：
```bash
0 9 * * * /usr/bin/python3 -m certmon.cli send-reminders -C /path/to/your/project > /var/log/certmon.log 2>&1
```
- 可使用 `-C` 指定项目目录（否则默认当前工作目录）。
- 日志输出到 `/var/log/certmon.log`。

### 启停脚本（可选，不使用 systemd 时）
在项目根目录下提供 `scripts/certmon.sh`，支持后台运行 Gunicorn：
```bash
chmod +x scripts/certmon.sh

# 启动（后台）
./scripts/certmon.sh start

# 查看状态 / 平滑重载 / 重启 / 停止
./scripts/certmon.sh status
./scripts/certmon.sh reload
./scripts/certmon.sh restart
./scripts/certmon.sh stop

# 查看实时日志
./scripts/certmon.sh tail
```
可通过环境变量覆盖：`PYTHON`、`BIND`、`WORKERS`、`TIMEOUT`、`GUNICORN_APP`。

### 命令说明
- 初始化数据库：
```bash
python3 -m certmon.cli init-db
```

- 添加证书：
```bash
# 方式一：直接指定到期日（旧模式）
python3 -m certmon.cli add --name "名称/类目" --email someone@example.com --expires YYYY-MM-DD [--notes "备注"]

# 方式二：获取日期 + 有效月数（新模式，会自动计算到期日）
python3 -m certmon.cli add --name "名称/类目" --email someone@example.com --acquired 2025-01-15 --months 14 [--notes "备注"]
```

- 列表证书：
```bash
python3 -m certmon.cli list
```

- 删除证书（按 id）：
```bash
python3 -m certmon.cli remove --id 1
```

- 发送提醒：
```bash
python3 -m certmon.cli send-reminders
```

- 发送测试邮件（验证 SMTP 配置）：
```bash
python3 -m certmon.cli send-test --to you@example.com \
  --subject "CertMon 测试" \
  --body "这是一封测试邮件"
```

### 提醒策略
- 在到期前 `reminder_window_days`（默认 7 天）内的每一天都会发送一封提醒邮件。
- 同一天内对同一证书仅发送一次（通过 `last_reminded_on` 字段防抖）。

### 安全建议
- 使用专用的 SMTP 账号和强密码。
- 如支持，启用应用专用密码。
- 限制 `config.json` 文件权限：`chmod 600 config.json`。

### SMTP 配置与排错
- 配置文件 `config.json` 示例（确保主机、端口、凭据正确且收件人可被投递）：
```json
{
  "smtp": {
    "host": "smtp.example.com",
    "port": 587,
    "username": "user@example.com",
    "password": "REPLACE_WITH_REAL_PASSWORD",
    "use_tls": true,
    "from_email": "noreply@example.com"
  },
  "app": {
    "database_path": "data/certmon.db",
    "reminder_window_days": 7
  }
}
```

- 常见问题排查：
  - 检查端口：`587` 通常为 STARTTLS，`465` 为 SMTPS（需将 `use_tls` 设为 false，走 SSL）。
  - 用户名/密码：不少服务要求“应用专用密码”而非登录口令；需在邮箱安全设置中创建。
  - 发件人与 SMTP 账号匹配：有些服务要求 `from_email` 与账号一致或同域。
  - 防火墙/云安全组：确认服务器能连通 SMTP 端口（telnet/openssl s_client）。
  - SPF/DKIM：若自定义域名发信，确保 DNS 记录正确，否则可能被收件方拒收或进垃圾箱。
  - 服务器拒信错误：运行 `send-test` 命令查看报错信息，通常会包含 4xx/5xx 状态与原因。
  - Python 无 SSL：错误如 “No SSL support included in this Python”，请安装带 SSL 的 Python 或使用系统 Python。
  - 无 SMTP_SSL：错误如 “module 'smtplib' has no attribute 'SMTP_SSL'”，建议改用 587 + use_tls=true，或安装带 SSL 支持的 Python。

- 自检命令：
```bash
python -c "import ssl, smtplib, sys; print(sys.executable); print(sys.version); print('SSL?', hasattr(ssl,'SSLContext')); print('SMTP_SSL?', hasattr(smtplib,'SMTP_SSL'))"
```
若 `SSL?` 或 `SMTP_SSL?` 为 False，说明当前 Python 不具备必要的 SSL 功能。

### 许可证
MIT


