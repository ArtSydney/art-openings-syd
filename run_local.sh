#!/bin/bash
# Load env vars and run pipeline locally
# Usage: ./run_local.sh
#
# To suppress Discord notifications during testing:
#   unset DISCORD_WEBHOOK_URL && ./run_local.sh

set -a
source .env 2>/dev/null
set +a

python3 main.py
