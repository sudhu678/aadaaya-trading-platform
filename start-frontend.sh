#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/dashboard/ui"
[ -d node_modules ] || npm install
npm run dev
