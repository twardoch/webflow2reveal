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
VERSION=$(git describe --tags --abbrev=0 | sed 's/^v//')
echo "=== Updating JS package.json version to $VERSION ==="
cd js
npm version "$VERSION" --no-git-tag-version
npm run build
npm publish --access public
cd ..

echo "=== Publish Complete ==="
