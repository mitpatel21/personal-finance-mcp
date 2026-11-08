#!/bin/bash
# Starts the MCP server from this repo's virtualenv. Used by the launchd agent.
cd "$(dirname "$0")/.." || exit 1
exec ./.venv/bin/python server.py
