#!/usr/bin/env bash
set -euo pipefail
: "${RID:?RID is required}"
: "${AVALONIA_VERSION:?AVALONIA_VERSION is required}"
mkdir -p "$HOME"
source_dir="/src/External/AvaloniaNative/.work/Avalonia-$AVALONIA_VERSION"
git clone --depth 1 --branch "$AVALONIA_VERSION" https://github.com/AvaloniaUI/Avalonia.git "$source_dir"
if git -C "$source_dir" config -f .gitmodules --get-regexp path | grep -q "[[:space:]]external/Numerge$"; then
  git -C "$source_dir" submodule update --init --depth 1 external/Numerge
fi
python3 build/linux-toolchain/build-avalonia-native-cross.py \
  --source "$source_dir" --rid "$RID" --sdk /opt/macos-sdk/MacOSX15.5.sdk \
  --work "/src/External/AvaloniaNative/.work/zig-$AVALONIA_VERSION-$RID" \
  --output "/src/External/AvaloniaNative/$RID/native"

