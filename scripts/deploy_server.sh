#!/usr/bin/env bash
set -euo pipefail

cd /opt/Latest-AI-updates

if [ -f /etc/latest-ai-updates.env ]; then
  set -a
  # shellcheck disable=SC1091
  . /etc/latest-ai-updates.env
  set +a
fi

PYTHON_BIN="${PYTHON_BIN:-python3}"

git pull --ff-only
npm ci
git restore package-lock.json package.json 2>/dev/null || true
npm run build

if [ ! -x .venv/bin/python ]; then
  "$PYTHON_BIN" -m venv .venv
fi

.venv/bin/pip install -r requirements.txt
PYTHONPATH=. .venv/bin/python scripts/setup_db.py

if [ -f /etc/systemd/system/latest-ai-updates.service ]; then
  python3 - <<'PY'
from pathlib import Path

service_path = Path("/etc/systemd/system/latest-ai-updates.service")
content = service_path.read_text()
old = "ExecStart=/opt/Latest-AI-updates/.venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8000"
new = old + " --no-access-log"
if old in content and new not in content:
    service_path.write_text(content.replace(old, new))
PY
  systemctl daemon-reload
fi

systemctl restart latest-ai-updates
systemctl reload nginx

echo "Deployment completed."
