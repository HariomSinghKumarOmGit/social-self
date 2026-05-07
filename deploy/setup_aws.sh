#!/usr/bin/env bash
# ============================================================
# AWS EC2 Ubuntu setup script for Social Media Automation Agent
# Targets: Ubuntu 22.04+ on t2.micro (free tier)
# ============================================================
set -euo pipefail

APP_USER="ubuntu"
APP_DIR="/home/${APP_USER}/social-self"
VENV_DIR="${APP_DIR}/.venv"
SERVICE_NAME="social-agent"
PYTHON_VERSION="3.11"

echo "========================================"
echo "  Social Agent — AWS EC2 Setup Script"
echo "========================================"

# -------------------------------------------------------
# 1. System packages
# -------------------------------------------------------
echo "[1/7] Installing system packages…"
sudo apt-get update -y
sudo apt-get install -y \
    software-properties-common \
    python${PYTHON_VERSION} \
    python${PYTHON_VERSION}-venv \
    python3-pip \
    git \
    curl \
    wget \
    unzip \
    libnss3 libxss1 libasound2 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libgbm1 libgtk-3-0 libxcomposite1 \
    libxdamage1 libxrandr2 xdg-utils fonts-liberation

# -------------------------------------------------------
# 2. Clone / update the project (skip if already present)
# -------------------------------------------------------
echo "[2/7] Setting up project directory…"
if [ ! -d "${APP_DIR}" ]; then
    echo "  -> Project not found at ${APP_DIR}."
    echo "  -> Please upload or git-clone your project there, then re-run."
    exit 1
fi

# -------------------------------------------------------
# 3. Python venv + dependencies
# -------------------------------------------------------
echo "[3/7] Creating virtual environment and installing dependencies…"
python${PYTHON_VERSION} -m venv "${VENV_DIR}"
source "${VENV_DIR}/bin/activate"
pip install --upgrade pip
pip install -r "${APP_DIR}/requirements.txt"

# -------------------------------------------------------
# 4. Playwright browsers
# -------------------------------------------------------
echo "[4/7] Installing Playwright browsers…"
python -m playwright install chromium
python -m playwright install-deps chromium

# -------------------------------------------------------
# 5. .env sanity check
# -------------------------------------------------------
echo "[5/7] Checking .env…"
if [ ! -f "${APP_DIR}/.env" ]; then
    echo "  ⚠️  .env file missing! Create ${APP_DIR}/.env with:"
    echo "      TELEGRAM_BOT_TOKEN=your_token"
    echo "      TELEGRAM_CHAT_ID=your_chat_id"
    echo "      APIFY_API_TOKEN=your_apify_token"
fi

# -------------------------------------------------------
# 6. systemd service
# -------------------------------------------------------
echo "[6/7] Creating systemd service…"
sudo tee /etc/systemd/system/${SERVICE_NAME}.service > /dev/null <<EOF
[Unit]
Description=Social Media Automation Agent
After=network.target

[Service]
Type=simple
User=${APP_USER}
WorkingDirectory=${APP_DIR}
ExecStart=${VENV_DIR}/bin/python ${APP_DIR}/main.py
Restart=on-failure
RestartSec=10
Environment="PATH=${VENV_DIR}/bin:/usr/local/bin:/usr/bin:/bin"

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable ${SERVICE_NAME}
sudo systemctl start ${SERVICE_NAME}

# -------------------------------------------------------
# 7. Firewall — open port 5000
# -------------------------------------------------------
echo "[7/7] Opening port 5000…"
sudo ufw allow 5000/tcp 2>/dev/null || true

# -------------------------------------------------------
# Done
# -------------------------------------------------------
echo ""
echo "========================================"
echo "  ✅ Setup complete!"
echo "========================================"
echo ""
echo "Service status:  sudo systemctl status ${SERVICE_NAME}"
echo "View logs:       sudo journalctl -u ${SERVICE_NAME} -f"
echo "Web UI:          http://$(curl -s ifconfig.me 2>/dev/null || echo '<your-ip>'):5000"
echo ""
echo "IMPORTANT: Also allow port 5000 in your AWS Security Group."
echo ""
