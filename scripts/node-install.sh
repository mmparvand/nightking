#!/usr/bin/env bash
set -euo pipefail
if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sh
fi
if ! command -v docker-compose >/dev/null 2>&1; then
  DOCKER_CONFIG=${DOCKER_CONFIG:-$HOME/.docker}
  mkdir -p $DOCKER_CONFIG/cli-plugins
  curl -SL https://github.com/docker/compose/releases/download/v2.27.0/docker-compose-$(uname -s)-$(uname -m) -o $DOCKER_CONFIG/cli-plugins/docker-compose
  chmod +x $DOCKER_CONFIG/cli-plugins/docker-compose
fi
read -p "Master panel URL: " MASTER_URL
read -p "Node token: " NODE_TOKEN
read -p "Node name: " NODE_NAME
read -p "Location: " NODE_LOCATION
cat > docker-compose.yml <<YML
version: '3.9'
services:
  node-agent:
    image: python:3.12-slim
    environment:
      NODE_TOKEN: ${NODE_TOKEN}
      NODE_CONFIG_PATH: /etc/xray/config.json
      NODE_RELOAD_COMMAND: "xray -test -config /etc/xray/config.json && supervisorctl restart xray"
    volumes:
      - ./node-agent:/app
      - ./xray-config:/etc/xray
    working_dir: /app
    command: ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
  xray:
    image: teddysun/xray:1.8.9
    volumes:
      - ./xray-config:/etc/xray
    ports:
      - "8443:8443"
YML
mkdir -p node-agent
cat > node-agent/main.py <<'PY'
from main import app
PY
docker compose up -d --build
echo "Register this node in master with token ${NODE_TOKEN}, name ${NODE_NAME}, location ${NODE_LOCATION}"
echo "Master: ${MASTER_URL}"
