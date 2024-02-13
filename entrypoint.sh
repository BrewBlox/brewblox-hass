#!/bin/env bash
set -euo pipefail

python3 ./parse_appenv.py "$@" >.appenv

exec uvicorn \
    --host 0.0.0.0 \
    --port 5000 \
    --factory \
    brewblox_hass.app_factory:create_app
