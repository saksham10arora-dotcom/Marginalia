#!/usr/bin/env bash
# Build a zip of extension/ suitable for Chrome Web Store upload, or for
# handing someone a single file they can unzip and load unpacked.
#
# Deliberately zips the working tree rather than a build step: this extension
# has no bundler, so what is in extension/ IS what ships, and introducing a
# build would mean the thing tested is no longer the thing shipped.
set -euo pipefail

cd "$(dirname "$0")/.."

VERSION=$(node -p "require('./extension/manifest.json').version")
OUT_DIR="dist"
OUT="${OUT_DIR}/margin-${VERSION}.zip"

# Fail loudly on a version mismatch rather than shipping a zip whose manifest
# disagrees with package.json about what release this is.
PKG_VERSION=$(node -p "require('./package.json').version")
if [ "$VERSION" != "$PKG_VERSION" ]; then
  echo "Version mismatch: extension/manifest.json says ${VERSION}, package.json says ${PKG_VERSION}" >&2
  exit 1
fi

mkdir -p "$OUT_DIR"
rm -f "$OUT"

# -x excludes test files: they import vitest, which is not a runtime dependency
# and would be dead weight (and a reviewer question mark) in a store upload.
(cd extension && zip -rq "../${OUT}" . \
  -x "*.test.js" \
  -x "*.DS_Store" \
  -x "__MACOSX/*")

echo "Built ${OUT} ($(du -h "$OUT" | cut -f1))"
echo
echo "Load unpacked:  chrome://extensions -> Developer Mode -> Load unpacked -> extension/"
echo "Web Store:      upload ${OUT}"
