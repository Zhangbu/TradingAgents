#!/usr/bin/env bash
set -euo pipefail

sudo systemctl restart tradingagents-api
sudo systemctl restart tradingagents-web
sudo systemctl reload nginx

echo "Services restarted:"
sudo systemctl --no-pager --full status tradingagents-api | sed -n '1,8p'
sudo systemctl --no-pager --full status tradingagents-web | sed -n '1,8p'
