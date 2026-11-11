# 部署执行步骤

> 在 ECS 上按顺序执行，每步都是复制粘贴即可。

---

## 一、连接服务器

```bash
ssh ecs-user@<ECS公网IP>
```

---

## 二、创建目录结构

```bash
sudo mkdir -p /opt/{apps,logs/backend,logs/nginx,ssl,scripts}
sudo chown -R $USER:$USER /opt
```

---

## 三、安装运行环境

```bash
# 更新系统
sudo dnf update -y

# 基础工具 + Nginx
sudo dnf install -y git nginx curl wget gcc make

# Node.js 22
curl -fsSL https://rpm.nodesource.com/setup_22.x | sudo bash -
sudo dnf install -y nodejs

# uv (Python 包管理)
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.cargo/env
uv python install 3.12
```

验证：

```bash
node -v    # v22.x
uv --version
nginx -v
```

---

## 四、拉取项目代码

```bash
cd /opt/apps
git clone <你的仓库地址> deeptime-rec

# 如果是私有仓库，先配 SSH Key 或用 HTTPS + token
```

---

## 五、部署后端

```bash
cd /opt/apps/deeptime-rec/backend

# 安装依赖
UV_CACHE_DIR=/tmp/.uv_cache uv sync

# 试运行验证（Ctrl+C 退出）
UV_CACHE_DIR=/tmp/.uv_cache uv run uvicorn app:app --host 127.0.0.1 --port 8000

# 看到 "Uvicorn running on http://127.0.0.1:8000" 就对了
```

---

## 六、部署前端

```bash
cd /opt/apps/deeptime-rec/frontend

# 安装依赖 + 构建
npm install
npm run build

# 确认产物
ls dist/index.html
```

---

## 七、注册 systemd 服务

```bash
sudo tee /etc/systemd/system/deeptime-backend.service << 'EOF'
[Unit]
Description=DeepTime Rec Backend
After=network.target

[Service]
Type=simple
User=SET_USER
WorkingDirectory=/opt/apps/deeptime-rec/backend
Environment="UV_CACHE_DIR=/tmp/.uv_cache"
ExecStart=SET_HOME/.cargo/bin/uv run uvicorn app:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5
StandardOutput=append:/opt/logs/backend/access.log
StandardError=append:/opt/logs/backend/error.log

[Install]
WantedBy=multi-user.target
EOF

# 替换占位符为实际值
sudo sed -i "s/SET_USER/$USER/g" /etc/systemd/system/deeptime-backend.service
sudo sed -i "s|SET_HOME|$HOME|g" /etc/systemd/system/deeptime-backend.service
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable deeptime-backend
sudo systemctl start deeptime-backend
```

验证：

```bash
sudo systemctl status deeptime-backend   # 看到 active (running)
curl http://127.0.0.1:8000/api/health     # 返回 {"status":"ok"}
```

---

## 八、配置 Nginx

```bash
sudo tee /etc/nginx/conf.d/deeptime-rec.conf << 'EOF'
server {
    listen 80;
    server_name _;

    root /opt/apps/deeptime-rec/frontend/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /docs {
        proxy_pass http://127.0.0.1:8000/docs;
        proxy_set_header Host $host;
    }

    location /openapi.json {
        proxy_pass http://127.0.0.1:8000/openapi.json;
        proxy_set_header Host $host;
    }
}
EOF
```

```bash
# 删掉 Nginx 默认配置
sudo rm -f /etc/nginx/conf.d/default.conf

sudo nginx -t
sudo systemctl enable nginx
sudo systemctl restart nginx
```

---

## 九、开放安全组

阿里云控制台 -> ECS -> 安全组 -> 添加规则：

| 端口 | 来源 | 说明 |
|---|---|---|
| 80 | 0.0.0.0/0 | HTTP |
| 22 | 你的办公 IP | SSH |

---

## 十、验证

浏览器访问 `http://<ECS公网IP>`，应该看到商城首页。

```bash
# 命令行验证
curl http://<ECS公网IP>/api/health
curl http://<ECS公网IP>/api/products?size=2
```

---

## 十一、一键部署脚本（可选）

```bash
tee /opt/scripts/deploy.sh << 'EOF'
#!/bin/bash
set -e
cd /opt/apps/deeptime-rec

echo "=== Pull ==="
git pull origin main

echo "=== Backend ==="
cd backend
UV_CACHE_DIR=/tmp/.uv_cache uv sync
sudo systemctl restart deeptime-backend

echo "=== Frontend ==="
cd ../frontend
npm install
npm run build

echo "=== Nginx ==="
sudo nginx -t && sudo systemctl reload nginx

echo "=== Done ==="
EOF

chmod +x /opt/scripts/deploy.sh
```

以后更新只需：

```bash
/opt/scripts/deploy.sh
```
