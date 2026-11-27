#!/usr/bin/env bash
# Build the display app into app/build/ADRIA.app (no Xcode needed).
# The ADRIA_HOME and adria-engine paths and PATH are recorded inside the bundle
# so the app also works when double-clicked; the bundle is a local build
# product and is never committed.
set -euo pipefail
source "$(dirname "$0")/_env.sh"

web="$ADRIA_ENGINE/app/web"
mac="$ADRIA_ENGINE/app/mac"
out="$ADRIA_ENGINE/app/build/ADRIA.app"

echo "== web"
(cd "$web" && [ -d node_modules ] || npm ci --no-audit --no-fund)
(cd "$web" && npm run build)

echo "== native"
(cd "$mac" && swift build -c release 2>&1 | grep -v "ld: warning: search path")
bin="$(cd "$mac" && swift build -c release --show-bin-path)/ADRIA"

echo "== bundle"
/bin/rm -rf "$out"
mkdir -p "$out/Contents/MacOS" "$out/Contents/Resources"
cp "$bin" "$out/Contents/MacOS/ADRIA"
cp -R "$web/dist" "$out/Contents/Resources/web"
printf '%s\n' "$ADRIA_HOME" > "$out/Contents/Resources/adria_home"
# Opened by itself, the app starts the voice loop with scripts/harness.sh; a
# double-clicked app gets no shell PATH, so record the one that finds uv.
printf '%s\n' "$ADRIA_ENGINE" > "$out/Contents/Resources/adria_engine"
printf '%s\n' "$PATH" > "$out/Contents/Resources/search_path"
cat > "$out/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleIdentifier</key><string>local.adria.display</string>
  <key>CFBundleName</key><string>ADRIA</string>
  <key>CFBundleDisplayName</key><string>ADRIA</string>
  <key>CFBundleExecutable</key><string>ADRIA</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleShortVersionString</key><string>0.1.0</string>
  <key>CFBundleVersion</key><string>1</string>
  <key>LSMinimumSystemVersion</key><string>14.0</string>
  <key>NSHighResolutionCapable</key><true/>
  <key>NSMicrophoneUsageDescription</key><string>ADRIA listens while a conversation is on (after a click on the character).</string>
</dict>
</plist>
PLIST
codesign --force --sign - "$out" >/dev/null 2>&1
echo "built $out"
