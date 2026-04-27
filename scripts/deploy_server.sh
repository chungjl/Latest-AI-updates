#!/usr/bin/env bash
set -euo pipefail

cd /opt/Latest-AI-updates

git pull --ff-only
npm install
npm run build

.venv/bin/pip install -r requirements.txt
PYTHONPATH=. .venv/bin/python scripts/setup_db.py

systemctl restart latest-ai-updates
systemctl reload nginx

echo "Deployment completed."
