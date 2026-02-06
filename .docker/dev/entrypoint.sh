#!/bin/sh
set -e

# 1. Always run uv sync
echo "Syncing dependencies..."
uv sync --active --no-managed-python

# 2. Execute the passed command (CMD)
# 'exec' ensures the app replaces the shell script as PID 1,
# which is important for signal handling (like stopping the container).
exec "$@"
