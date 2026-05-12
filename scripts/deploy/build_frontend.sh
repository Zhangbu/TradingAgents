#!/usr/bin/env bash
set -euo pipefail

source "$HOME/.nvm/nvm.sh"
nvm use 24 >/dev/null

cd "$(dirname "$0")/../../frontend"
npm install
npm run build
