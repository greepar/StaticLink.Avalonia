#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
rid="${RID:-linux-x64}"
case "$rid" in
  linux-x64) cpu=x64; platform=linux/amd64 ;;
  linux-arm64) cpu=arm64; platform=linux/arm64 ;;
  *) echo "Debian container currently supports linux-x64 and linux-arm64: $rid" >&2; exit 2 ;;
esac
source_lock="$(realpath "${SOURCE_LOCK:-$root/build/linux-toolchain/sources.lock.json}")"
case "$source_lock" in
  "$root/"*) container_lock="/src/${source_lock#"$root/"}" ;;
  *) echo "SOURCE_LOCK must be inside the mounted repository" >&2; exit 2 ;;
esac
lock_key="$(sha256sum "$source_lock" | cut -c1-16)"
eval "$(python3 - "$source_lock" <<'PY'
import json, shlex, sys
lock = json.load(open(sys.argv[1]))
for key, value in lock.items():
    print(f'{key.upper()}={shlex.quote(value)}')
PY
)"
image="staticlink-debian12:$(sha256sum "$root/build/linux-toolchain/Dockerfile" | cut -c1-16)"
docker build --platform "$platform" -t "$image" "$root/build/linux-toolchain"
docker run --rm --platform "$platform" \
  --user "$(id -u):$(id -g)" \
  -v "$root:/src" -w /src \
  -e HOME=/tmp/staticlink-home \
  -e RID="$rid" -e TARGET_CPU="$cpu" \
  -e BUILD_JOBS="${BUILD_JOBS:-4}" \
  -e WORK_DIR="/src/External/NativeStatic/.work/native-$lock_key" \
  -e SOURCE_LOCK="$container_lock" \
  -e SKIASHARP_VERSION="$SKIASHARP_VERSION" -e SKIASHARP_REVISION="$SKIASHARP_REVISION" \
  -e ANGLE_BRANCH="$ANGLE_BRANCH" -e ANGLE_REVISION="$ANGLE_REVISION" \
  -e DEPOT_TOOLS_DIR=/src/External/NativeStatic/.work/depot_tools \
  "$image" bash -c '
    set -euo pipefail
    mkdir -p "$HOME" "$(dirname "$DEPOT_TOOLS_DIR")"
    # The image checkout is read-only for a non-root user; gclient needs a writable copy.
    if [[ ! -d "$DEPOT_TOOLS_DIR/.git" ]]; then
      cp -a /opt/depot_tools "$DEPOT_TOOLS_DIR"
    fi
    scripts/build-linux-static-graphics.sh "${1:-all}"
    cp /opt/staticlink/packages.lock "External/NativeStatic/$RID/toolchain-packages.lock"
    cp "$SOURCE_LOCK" "External/NativeStatic/$RID/sources.lock.json"
  ' bash "${1:-all}"
