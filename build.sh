#!/bin/bash
# this_file: build.sh
set -e

# Make sure we are in the script directory
cd "$(dirname "$0")"

echo "=== Building webflow2revealjs ==="
cd js
npm install
npm run build
cd ..

echo "=== Copying browser bundle to docs demo ==="
mkdir -p docs/demo/dist
cp js/dist/index.global.js docs/demo/dist/index.global.js

echo "=== Building webflow2reveal Python package ==="
# Clean old builds
rm -rf dist/
uv build

echo "=== Build Complete ==="
