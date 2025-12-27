#!/usr/bin/env bash
set -euo pipefail
curl -fsSL https://raw.githubusercontent.com/mmparvand/nightking/main/install.sh | sudo bash -s -- --node "$@"
