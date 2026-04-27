#!/usr/bin/env bash
set -euo pipefail

cd /opt/Latest-AI-updates

if [ -f /etc/latest-ai-updates.env ]; then
  set -a
  # shellcheck disable=SC1091
  . /etc/latest-ai-updates.env
  set +a
fi

git pull --ff-only
npm ci
git restore package-lock.json package.json 2>/dev/null || true
npm run build

.venv/bin/pip install -r requirements.txt
PYTHONPATH=. .venv/bin/python scripts/setup_db.py

systemctl restart latest-ai-updates
systemctl reload nginx

echo "Deployment completed."
