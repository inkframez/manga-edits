#!/bin/bash
# Cloud sessions: install the Python render stack and build the fonts/ folder so the render scripts run.
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "$CLAUDE_PROJECT_DIR"
pip install -q --root-user-action=ignore -r requirements.txt
python3 tools/setup_fonts.py   # no-op when fonts/manifest.json is current
