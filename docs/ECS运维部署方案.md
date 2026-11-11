# 工业资产商城推荐系统 — 阿里云 ECS 运维部署方案

## 1. 环境信息

| 项目 | 说明 |
|---|---|
| ECS 实例 | `i-2zebzk3crpikal1lik8k`（cn-beijing） |
| 操作系统 | Alibaba Cloud Linux 3 / CentOS 7.x |
| 后端 | Python 3.12 + FastAPI + uvicorn (端口 8000) |
| 前端 | React + Vite (静态文件，Nginx 托管) |
| 进程管理 | systemd |
| 反向代理 | Nginx (端口 80/443) |

## 2. 目录规划

```
/opt/
├── apps/
│   └── deeptime-rec/        # 项目根目录 (git clone 到此)
│       ├── backend/
│       ├── frontend/
│       └── docs/
├── logs/
│   ├── backend/             # 后端日志
│   │   ├── access.log
│   │   └── error.log
│   └── nginx/               # Nginx 日志
├── ssl/                     # SSL 证书
└── scripts/                 # 运维脚本
```

## 3. 环境初始化

### 3.1 基础工具

```bash
# 更新系统
sudo dnf update -y  # Alibaba Cloud Linux 3
# 或 sudo yum update -y  # CentOS 7

# 安装基础依赖
sudo dnf install -y git nginx curl wget gcc make

# 安装 Node.js 22 (LTS)
curl -fsSL https://rpm.nodesource.com/setup_22.x | sudo bash -
sudo dnf install -y nodejs

# 安装 uv (Python 包管理)
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.cargo/env
```

### 3.2 Python 环境

```bash
# uv 会自动管理 Python 版本，无需手动安装
uv python install 3.12
```

## 4. 项目部署

### 4.1 拉取代码

```bash
cd /opt/apps
git clone <your-repo-url> deeptime-rec
cd deeptime-rec
```

### 4.2 后端部署

```bash
cd /opt/apps/deeptime-rec/backend

# 同步依赖
uv sync

# 手动验证
uv run uvicorn app:app --host 0.0.0.0 --port 8000
# Ctrl+C 退出
```

### 4.3 前端构建

```bash
cd /opt/apps/deeptime-rec/frontend

# 安装依赖 & 构建
npm install
npm run build
# 产出在 frontend/dist/
```

## 5. systemd 进程守护

### 5.1 后端服务

创建 `/etc/systemd/system/deeptime-backend.service`：

```ini
[Unit]
Description=DeepTime Rec Backend
After=network.target

[Service]
Type=simple
User=ecs-user
WorkingDirectory=/opt/apps/deeptime-rec/backend
Environment="UV_CACHE_DIR=/tmp/.uv_cache"
ExecStart=/home/ecs-user/.cargo/bin/uv run uvicorn app:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5
StandardOutput=append:/opt/logs/backend/access.log
StandardError=append:/opt/logs/backend/error.log

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable deeptime-backend
sudo systemctl start deeptime-backend
sudo systemctl status deeptime-backend
```

### 5.2 Nginx

```bash
sudo systemctl enable nginx
sudo systemctl start nginx
```

## 6. Nginx 配置

创建 `/etc/nginx/conf.d/deeptime-rec.conf`：

```nginx
# HTTP → HTTPS 重定向
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate     /opt/ssl/fullchain.pem;
    ssl_certificate_key /opt/ssl/privkey.pem;

    # 静态前端
    root /opt/apps/deeptime-rec/frontend/dist;
    index index.html;

    # SPA 路由回退
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API 反向代理
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Swagger 文档
    location /docs {
        proxy_pass http://127.0.0.1:8000/docs;
        proxy_set_header Host $host;
    }

    location /openapi.json {
        proxy_pass http://127.0.0.1:8000/openapi.json;
        proxy_set_header Host $host;
    }

    # 静态资源缓存
    location /assets/ {
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

验证并重载：

```bash
sudo nginx -t
sudo systemctl reload nginx
```

## 7. 安全组配置

在阿里云 ECS 控制台 → 安全组 → 入方向规则：

| 端口 | 协议 | 来源 | 说明 |
|---|---|---|---|
| 22 | TCP | 办公 IP 段 | SSH |
| 80 | TCP | 0.0.0.0/0 | HTTP |
| 443 | TCP | 0.0.0.0/0 | HTTPS |

> ⚠️ 后端 8000 端口不对外开放，仅 Nginx 本地代理访问。

## 8. SSL 证书

```bash
# 使用阿里云免费 SSL (推荐) 或 Let's Encrypt
sudo dnf install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
# 证书自动续期
sudo systemctl enable certbot-renew.timer
```

或者直接在阿里云 SSL 证书控制台申请免费证书，下载后放到 `/opt/ssl/`。

## 9. 日志管理

### 9.1 日志轮转

创建 `/etc/logrotate.d/deeptime-rec`：

```
/opt/logs/backend/*.log
/opt/logs/nginx/*.log {
    daily
    rotate 30
    missingok
    notifempty
    compress
    delaycompress
    copytruncate
    dateext
}
```

### 9.2 查看日志

```bash
# 后端实时日志
tail -f /opt/logs/backend/access.log

# Nginx 访问日志
tail -f /opt/logs/nginx/access.log

# systemd 日志
journalctl -u deeptime-backend -f
```

## 10. 更新部署脚本

创建 `/opt/scripts/deploy.sh`：

```bash
#!/bin/bash
set -e

cd /opt/apps/deeptime-rec

echo "=== Pull ==="
git pull origin main

echo "=== Backend ==="
cd backend
uv sync
sudo systemctl restart deeptime-backend

echo "=== Frontend ==="
cd ../frontend
npm install
npm run build

echo "=== Nginx ==="
sudo nginx -t && sudo systemctl reload nginx

echo "=== Done ==="
```

```bash
chmod +x /opt/scripts/deploy.sh
```

## 11. 监控 & 告警

| 维度 | 方案 |
|---|---|
| ECS 基础监控 | 阿里云云监控（CPU/内存/磁盘/网络，控制台免费开通） |
| 进程存活 | `systemctl status` + 云监控自定义报警 |
| 接口健康检查 | 阿里云云监控站点拨测，检查 `GET /api/health` |
| 日志错误告警 | 阿里云日志服务 SLS（可选，有成本） |

## 12. 快速排查命令

```bash
# 服务状态
sudo systemctl status deeptime-backend nginx

# 端口占用
sudo ss -tlnp | grep -E '80|443|8000'

# 后端健康检查
curl -s http://127.0.0.1:8000/api/health

# 磁盘空间
df -h /opt

# 进程资源
htop -p $(pgrep -f uvicorn)
```
