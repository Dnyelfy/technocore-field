#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p public
cat src/page-head.html src/page-app.html > public/index.html
echo "wrote public/index.html ($(wc -c < public/index.html) bytes)"
