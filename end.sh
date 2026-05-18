#!/usr/bin/env bash
set -euo pipefail

echo "==> Stopping services"
docker compose down

echo ""
echo "  All services stopped."
echo "  Volumes (database, GCS data, Whisper cache) were preserved."
echo "  Run 'docker compose down -v' to also remove volumes."
