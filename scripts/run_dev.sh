#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "Start the backend in one terminal:"
echo "  cd \"$ROOT_DIR\" && ./scripts/run_backend.sh"
echo
echo "Start the frontend in another terminal:"
echo "  cd \"$ROOT_DIR\" && ./scripts/run_frontend.sh"
