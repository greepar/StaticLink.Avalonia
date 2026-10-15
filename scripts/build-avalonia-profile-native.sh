#!/usr/bin/env bash
set -euo pipefail
: "${AVALONIA_PROFILE:?AVALONIA_PROFILE is required}"
read -r version revision < <(python3 - "$AVALONIA_PROFILE" <<'PY'
import json, sys
lock = json.load(open(sys.argv[1]))
print(lock['avalonia_version'], lock['avalonia_revision'])
PY
)
source_dir="/src/External/NativeStatic/.work/avalonia-native/$version-$revision"
if [[ ! -d "$source_dir/.git" ]]; then
  git init "$source_dir"
  git -C "$source_dir" remote add origin https://github.com/AvaloniaUI/Avalonia.git
  git -C "$source_dir" fetch --depth 1 origin "$revision"
  git -C "$source_dir" checkout --detach FETCH_HEAD
fi
test "$(git -C "$source_dir" rev-parse HEAD)" = "$revision"
if git -C "$source_dir" config -f .gitmodules --get-regexp path | grep -q '[[:space:]]external/Numerge$'; then
  git -C "$source_dir" submodule update --init --depth 1 external/Numerge
fi
for rid in osx-x64 osx-arm64; do
  python3 build/linux-toolchain/build-avalonia-native-cross.py \
    --source "$source_dir" --rid "$rid" --sdk /opt/macos-sdk/MacOSX15.5.sdk \
    --work "/src/External/NativeStatic/.work/avalonia-native/zig-$version-$rid" \
    --output "/src/artifacts/avalonia-native/$version/$rid/native"
done
