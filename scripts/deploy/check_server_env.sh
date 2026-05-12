#!/usr/bin/env bash
set -euo pipefail

echo "TradingAgents server environment check"
echo "- user: $(whoami)"
echo "- cwd: $(pwd)"
echo "- nginx: $(command -v nginx || echo missing)"
echo "- git: $(command -v git || echo missing)"
echo "- curl: $(command -v curl || echo missing)"

if [ -f "$HOME/miniconda3/etc/profile.d/conda.sh" ]; then
  source "$HOME/miniconda3/etc/profile.d/conda.sh"
  if conda env list | grep -q 'tradingagents'; then
    conda activate tradingagents
    echo "- python: $(command -v python)"
    python --version
  else
    echo "- conda env 'tradingagents' not found"
  fi
else
  echo "- miniconda not found at $HOME/miniconda3"
fi

if [ -f "$HOME/.nvm/nvm.sh" ]; then
  source "$HOME/.nvm/nvm.sh"
  if nvm ls 24 >/dev/null 2>&1; then
    nvm use 24 >/dev/null
    echo "- node: $(command -v node)"
    node -v
    echo "- npm: $(command -v npm)"
    npm -v
  else
    echo "- nvm found, but Node 24 is not installed"
  fi
else
  echo "- nvm not found at $HOME/.nvm"
fi
