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

echo "=== Copying browser bundle to docs ==="
mkdir -p docs/dist
cp js/dist/index.global.js docs/dist/index.global.js

echo "=== Building webflow2reveal Python package ==="
# Clean old builds
rm -rf dist/
uv build

echo "=== Build Complete ==="
