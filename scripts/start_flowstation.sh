#!/usr/bin/env bash
set -e

# start_flowstation.sh - create venv and run FlowStation (wrapper)
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
pip install -U pip
# pip install -r requirements.txt  # uncomment if you have deps
python3 FlowStation-v1.1.0-FC_FLOW.py
