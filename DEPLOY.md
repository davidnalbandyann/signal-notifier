# Hetzner VPS cx23 Deployment Guide

Zero-downtime 24/7 deployment of all three components:
**Vue frontend** + **FastAPI backend** + **C++ engine** on one server, no custom domain.

---

## Architecture on the VPS

```
Browser (your laptop)
    │
    ▼
VPS IP :80 ─── Nginx ──► /api/* ──► uvicorn :8000 (FastAPI)
                  │                       │
                  │ static files          ├─► Playwright → TradingView
                  │                       ├─► NVIDIA NIM API
                  │                       ├─► Telegram Bot API
                  ▼                       ├─► SQLite (tcm.db)
           frontend/dist/                 └─► /trigger ←── C++ engine
                                              (systemd)
                                                      │
                                                      ▼
                                                Binance REST API
```

Single origin (same IP, port 80) — no CORS issues in production.

---

## Step 1 — Create the VPS

1. Go to [Hetzner Cloud](https://console.hetzner.cloud)
2. Create a **cx23** (2 vCPU / 4 GB RAM / 40 GB NVMe)
3. OS: **Ubuntu 24.04 LTS**
4. Add your SSH key
5. Note the **IPv4 address** (e.g. `5.9.123.45`)

---

## Step 2 — SSH & initial setup

```bash
ssh root@<your-server-ip>
```

```bash
# Update system
apt update && apt upgrade -y

# Install core tools
apt install -y git curl wget ufw build-essential cmake \
  libcurl4-openssl-dev libssl-dev pkg-config \
  python3 python3-venv python3-pip nginx
```

---

## Step 3 — Install Node.js (for Vue build)

```bash
# NodeSource LTS (v22)
curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
apt install -y nodejs
node --version   # verify
npm --version
```

---

## Step 4 — Clone the project

```bash
# Create a service user (optional, but cleaner)
useradd -m -s /bin/bash tcm
usermod -aG sudo tcm

# Clone as tcm user
su - tcm
git clone <your-repo-url> /home/tcm/trading-notifier
cd /home/tcm/trading-notifier
```

> If you don't have a remote, `scp` the project folder to the VPS instead.

---

## Step 5 — Build C++ engine

```bash
cd /home/tcm/trading-notifier

cmake -S trading-signal-engine -B trading-signal-engine/build \
  -DCMAKE_BUILD_TYPE=Release

cmake --build trading-signal-engine/build -j$(nproc)

# Verify binary exists
ls -la trading-signal-engine/build/trading_signal_engine
```

---

## Step 6 — Python backend setup

```bash
cd /home/tcm/trading-notifier

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Install Playwright Chromium + system deps (takes ~1 min)
playwright install --with-deps chromium
```

---

## Step 7 — Build Vue frontend

```bash
cd /home/tcm/trading-notifier/frontend
npm install
npm run build

# Verify dist/ exists
ls dist/
# Expected: index.html, assets/, favicon.svg
```

---

## Step 8 — Configure environment

```bash
cd /home/tcm/trading-notifier
cp .env.example .env
```

Edit `.env` with your real values:

```ini
AUTH_USERNAME=admin
AUTH_PASSWORD=<generate-a-strong-password>
JWT_SECRET=<generate-a-random-string>     # openssl rand -hex 32

CHECK_INTERVAL_SECONDS=60
NOTIFICATION_THRESHOLD=8.0
PLAYWRIGHT_WAIT_TIME=5
HEADLESS=true
BROWSER_VIEWPORT_WIDTH=1920
BROWSER_VIEWPORT_HEIGHT=1080

TELEGRAM_TOKEN=123456:ABC...              # from @BotFather
TELEGRAM_CHAT_ID=-1001234567890           # from scripts/get_chat_id.py

NVIDIA_API_KEY=nvapi-...                  # from build.nvidia.com
NVIDIA_MODEL=minimaxai/minimax-m3
AI_CALL_DELAY=2.0

URLS_FILE=urls.yaml
TRIGGER_TOKEN=
CPP_ENGINE_BINARY=trading-signal-engine/build/trading_signal_engine
CPP_ENGINE_CONFIG=trading-signal-engine/config.json
```

---

## Step 9 — Nginx config

Create `/etc/nginx/sites-available/trading-notifier`:

```nginx
server {
    listen 80;
    server_name _;

    root /home/tcm/trading-notifier/frontend/dist;
    index index.html;

    # API proxy
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /health {
        proxy_pass http://127.0.0.1:8000;
    }

    # C++ engine trigger (from localhost)
    location /trigger {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # SPA fallback — everything else → index.html
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Cache static assets
    location /assets/ {
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

Enable it:

```bash
rm -f /etc/nginx/sites-enabled/default
ln -s /etc/nginx/sites-available/trading-notifier /etc/nginx/sites-enabled/
nginx -t
systemctl enable nginx
systemctl restart nginx
```

---

## Step 10 — systemd services

### 10a — FastAPI backend

Create `/etc/systemd/system/trading-notifier-api.service`:

```ini
[Unit]
Description=Trading Notifier FastAPI Backend
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=tcm
Group=tcm
WorkingDirectory=/home/tcm/trading-notifier
Environment=PATH=/home/tcm/trading-notifier/.venv/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=/home/tcm/trading-notifier/.venv/bin/uvicorn app.main:app \
  --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 10b — C++ engine

Create `/etc/systemd/system/trading-notifier-engine.service`:

```ini
[Unit]
Description=Trading Signal C++ Engine
After=trading-notifier-api.service
Wants=trading-notifier-api.service

[Service]
Type=simple
User=tcm
Group=tcm
WorkingDirectory=/home/tcm/trading-notifier
ExecStart=/home/tcm/trading-notifier/trading-signal-engine/build/trading_signal_engine \
  /home/tcm/trading-notifier/trading-signal-engine/config.json
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Enable and start

```bash
systemctl daemon-reload
systemctl enable trading-notifier-api
systemctl enable trading-notifier-engine
systemctl start trading-notifier-api
systemctl start trading-notifier-engine
```

---

## Step 11 — Firewall

```bash
ufw allow OpenSSH
ufw allow 80
ufw --force enable
ufw status
```

---

## Step 12 — Verify everything

```bash
# 1. All services running
systemctl status nginx trading-notifier-api trading-notifier-engine

# 2. Health check
curl http://127.0.0.1:8000/health

# 3. Frontend served (from your laptop)
curl http://<server-ip>/

# 4. API reachable through Nginx
curl http://<server-ip>/api/status

# 5. C++ engine posting to /trigger (check logs)
journalctl -u trading-notifier-engine -f

# 6. Watch all logs together
journalctl -u trading-notifier-api -u trading-notifier-engine -f
```

Then open `http://<server-ip>/` in your browser. Log in with the credentials from `.env`.

---

## Day-to-day commands

```bash
# Stop/start/restart services
systemctl stop trading-notifier-engine
systemctl start trading-notifier-engine
systemctl restart trading-notifier-api

# View real-time logs
journalctl -u trading-notifier-api -f
journalctl -u trading-notifier-engine -f

# Rebuild frontend after changes
cd /home/tcm/trading-notifier/frontend
npm run build

# Rebuild C++ engine after changes
cd /home/tcm/trading-notifier
cmake --build trading-signal-engine/build -j$(nproc)
systemctl restart trading-notifier-engine

# Restart backend after .env or code changes
systemctl restart trading-notifier-api
```

---

## Memory usage estimate (cx23 has 4 GB)

| Component           | ~Memory |
|---------------------|---------|
| C++ engine          | 50 MB   |
| Python + uvicorn    | 200 MB  |
| Playwright Chromium | 500 MB  |
| Nginx               | 20 MB   |
| **Total**           | **~800 MB** |

Well within the 4 GB budget. Spikes during screenshot capture but stays under 1.5 GB.

---

## What runs where

| Service                      | Port        | Managed by |
|------------------------------|-------------|------------|
| Nginx (frontend + proxy)     | 80 (public) | systemd    |
| FastAPI                      | 8000 (local)| systemd    |
| C++ engine                   | outbound    | systemd    |
| SQLite                       | file        | embedded   |
