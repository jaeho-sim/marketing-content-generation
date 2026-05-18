#!/usr/bin/env bash
set -euo pipefail

echo "==> Checking prerequisites"

if ! command -v docker &>/dev/null; then
  echo "Error: Docker is not installed. https://docs.docker.com/get-docker/"
  exit 1
fi

if ! docker compose version &>/dev/null; then
  echo "Error: Docker Compose v2 is not available."
  exit 1
fi

ENV_FILE="backend/.env"
if [[ ! -f "$ENV_FILE" ]]; then
  echo "==> No backend/.env found — copying from .env.example"
  cp backend/.env.example "$ENV_FILE"
  echo ""
  echo "  Please edit backend/.env and set GEMINI_API_KEY (or ANTHROPIC_API_KEY),"
  echo "  then re-run this script."
  echo ""
  exit 0
fi

echo "==> Starting services"
docker compose up --build -d

echo ""
echo "  Services are starting up. Waiting for backend to be ready..."

until curl -sf http://localhost:8000/health &>/dev/null; do
  sleep 2
done

echo ""
echo "  Frontend   http://localhost:3000"
echo "  API docs   http://localhost:8000/docs"
echo ""
echo "  Run 'docker compose logs -f' to follow logs."
echo "  Run 'docker compose down' to stop."
