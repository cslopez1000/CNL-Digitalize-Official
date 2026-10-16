#!/usr/bin/env bash
set -euo pipefail
project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ ! -x "$project_root/.venv/bin/python" ]]; then
    printf '%s\n' 'Virtual environment missing. Run: bash scripts/install_ubuntu.sh' >&2
    exit 1
fi
source "$project_root/.venv/bin/activate"
export COMBINATION_CHARTS_DIR="$project_root/build/ubuntu"
if [[ ! -d "$COMBINATION_CHARTS_DIR" ]]; then
    printf '%s\n' 'Native build missing. Run: bash scripts/install_ubuntu.sh' >&2
    exit 1
fi
exec "$project_root/.venv/bin/python" -B "$project_root/main.py" "$@"
