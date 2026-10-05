#!/usr/bin/env bash
set -euo pipefail
SCRIPT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_LOCK="${SOURCE_LOCK:-$SCRIPT_ROOT/build/linux-toolchain/sources.lock.json}"
SOURCE_LOCK="$(realpath "$SOURCE_LOCK")"
export WORK_DIR="${WORK_DIR:-$SCRIPT_ROOT/External/NativeStatic/.work/zig-sources}"
export LLVM_AR="${LLVM_AR:-llvm-ar}"
mkdir -p "$WORK_DIR"
read -r SKIASHARP_VERSION SKIASHARP_REVISION ANGLE_BRANCH ANGLE_REVISION < <(
  python3 - "$SOURCE_LOCK" <<'PY'
import json, sys
lock = json.load(open(sys.argv[1]))
print(lock['skiasharp_version'], lock['skiasharp_revision'], lock['angle_branch'], lock['angle_revision'])
PY
)
export SKIASHARP_VERSION SKIASHARP_REVISION ANGLE_BRANCH ANGLE_REVISION
export WORK_DIR="$WORK_DIR/$SKIASHARP_VERSION-$(sha256sum "$SOURCE_LOCK" | cut -c1-16)"
mkdir -p "$WORK_DIR"
source "$SCRIPT_ROOT/scripts/build-linux-static-graphics.sh"
if [[ ! -d "$WORK_DIR/depot_tools/.git" ]]; then
  cp -a /opt/depot_tools "$WORK_DIR/depot_tools"
fi
export DEPOT_TOOLS_DIR="$WORK_DIR/depot_tools"
ensure_tools
ensure_depot_tools
initialize_depot_tools_system_python "$DEPOT_TOOLS_DIR"
patch_depot_tools_python_deps "$DEPOT_TOOLS_DIR"
export VPYTHON_BYPASS="manually managed python not supported by chrome operations"
skia_sharp="$(sync_skiasharp)" || exit $?
retry_source_download python3 "$SCRIPT_ROOT/build/linux-toolchain/sync-skia-deps.py" --source "$skia_sharp/externals/skia" --cache "$SCRIPT_ROOT/External/NativeStatic/.work/skia-deps"
angle="$(sync_angle)" || exit $?
project_patch="$SCRIPT_ROOT/External/NativeStatic/patches/angle-chromium-$ANGLE_BRANCH.patch"
if git -C "$angle" apply --reverse --check "$project_patch" >/dev/null 2>&1; then
  :
else
  git -C "$angle" apply --check "$project_patch"
  git -C "$angle" apply "$project_patch"
fi
python3 - "$angle/.gclient" <<'PY'
from pathlib import Path
import sys
Path(sys.argv[1]).write_text('''solutions = [{
  "name": ".", "url": "https://chromium.googlesource.com/angle/angle.git",
  "deps_file": "DEPS", "managed": False,
  "custom_deps": {"third_party/llvm-build/Release+Asserts": None},
  "custom_vars": {"checkout_angle_cl_deps": False, "checkout_angle_dawn_deps": False},
}]
target_os = ["linux", "win", "mac"]
''')
PY
# Zig and the image's SDKs supply the compiler/runtime; skip native Xcode/MSVC
# setup hooks while retaining the pinned source dependencies for every target.
(cd "$angle" && retry_source_download gclient sync --nohooks --force)
python3 - "$WORK_DIR/cross-sources.json" "$skia_sharp/externals/skia" "$angle" "$SOURCE_LOCK" <<'PY'
import json, sys
from pathlib import Path
Path(sys.argv[1]).write_text(json.dumps({'skia': sys.argv[2], 'angle': sys.argv[3],
    'angle_gn': sys.argv[3] + '/buildtools/linux64/gn', 'source_lock': sys.argv[4]}, indent=2) + '\n')
PY
echo "Prepared $WORK_DIR/cross-sources.json"
