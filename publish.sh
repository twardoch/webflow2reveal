#!/bin/bash
# this_file: publish.sh
set -e

# Make sure we are in the script directory
cd "$(dirname "$0")"

echo "=== Running Build ==="
./build.sh

echo "=== Staging files for Git ==="
git add .

echo "=== Generating Next Version and Git Tag ==="
uvx gitnextver

echo "=== Pushing to Git Repository ==="
git push origin main --tags

echo "=== Rebuilding with new Git Version Tag ==="
./build.sh

echo "=== Publishing to PyPI ==="
uv publish

echo "=== Publishing to NPM ==="
cd js
# We use npm publish. The user will be prompted for OTP/login if needed
npm publish --access public
cd ..

echo "=== Publish Complete ==="
