#!/usr/bin/env bash
set -euo pipefail
MODE="master"
MASTER_URL=""
NODE_NAME=""
LOCATION=""
NODE_TOKEN=""
REPO_DIR="/opt/nightking"

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --node) MODE="node"; shift ;;
      --master) MODE="master"; shift ;;
      --master-url) MASTER_URL="$2"; shift 2 ;;
      --node-name) NODE_NAME="$2"; shift 2 ;;
      --location) LOCATION="$2"; shift 2 ;;
      --token) NODE_TOKEN="$2"; shift 2 ;;
      *) echo "Unknown arg: $1"; exit 1 ;;
    esac
  done
}

require_cmd() { command -v "$1" >/dev/null 2>&1; }

install_prereqs() {
  if require_cmd docker && docker compose version >/dev/null 2>&1; then
    return
  fi
  sudo apt-get update -y
  sudo apt-get install -y ca-certificates curl git
  sudo install -m 0755 -d /etc/apt/keyrings
  if [ ! -f /etc/apt/keyrings/docker.gpg ]; then
    curl -fsSL https://download.docker.com/linux/$(. /etc/os-release && echo "$ID")/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  fi
  echo \
"deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/$(. /etc/os-release && echo "$ID") $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
  sudo apt-get update -y
  sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin || true
  if ! docker compose version >/dev/null 2>&1; then
    sudo curl -SL "https://github.com/docker/compose/releases/download/v2.27.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
  fi
}

clone_repo() {
  if [ -d "$REPO_DIR/.git" ]; then
    cd "$REPO_DIR"
    sudo git pull --rebase || true
  else
    sudo mkdir -p "$REPO_DIR"
    sudo git clone https://github.com/mmparvand/nightking.git "$REPO_DIR"
    cd "$REPO_DIR"
  fi
}

ensure_env() {
  cd "$REPO_DIR"
  if [ ! -f .env ]; then
    cp .env.example .env
  fi
}

run_master() {
  cd "$REPO_DIR"
  sudo docker compose up -d --build
}

run_node() {
  cd "$REPO_DIR"
  sudo docker compose up -d --build node_agent xray || sudo docker compose up -d --build node-agent xray || sudo docker-compose up -d --build node_agent xray
}

print_summary() {
  echo "\nInstallation complete (mode: $MODE)."
  if [ "$MODE" = "master" ]; then
    echo "- Services: docker compose ps"
    echo "- Logs: docker compose logs backend"
    echo "- Update: git -C $REPO_DIR pull && docker compose up -d --build"
  else
    echo "- Services: docker compose ps"
    echo "- Logs: docker compose logs node_agent"
    echo "- Ensure NODE_TOKEN matches master-registered token"
  fi
}

parse_args "$@"
install_prereqs
clone_repo
ensure_env
if [ "$MODE" = "master" ]; then
  run_master
else
  if [ -z "$NODE_TOKEN" ]; then read -p "Node token: " NODE_TOKEN; fi
  if [ -z "$NODE_NAME" ]; then read -p "Node name: " NODE_NAME; fi
  if [ -z "$LOCATION" ]; then read -p "Location: " LOCATION; fi
  if [ -z "$MASTER_URL" ]; then read -p "Master URL: " MASTER_URL; fi
  export NODE_TOKEN NODE_NAME LOCATION MASTER_URL
  run_node
fi
print_summary
