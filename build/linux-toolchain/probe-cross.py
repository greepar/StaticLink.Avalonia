#!/usr/bin/env python3
"""Compile target objects and SDK API probes; this does not build release libraries."""
import argparse
import json
import pathlib
import subprocess
import tempfile

TARGETS = (
    "x86-windows-gnu", "x86_64-windows-gnu", "aarch64-windows-gnu",
    "x86-windows-msvc", "x86_64-windows-msvc", "aarch64-windows-msvc",
    "x86_64-macos", "aarch64-macos",
)
SOURCES = {
    "plain": "int answer(void) { return 42; }\n",
    "cpp": '#include <string>\nextern "C" int answer(void) { std::string s="test"; return int(s.size()); }\n',
    "windows": '''#include <windows.h>
#include <dwrite_3.h>
#include <xpsobjectmodel.h>
// These call shapes are required by Skia 4.150.1's DirectWrite paint backend.
HRESULT paint_child(IDWritePaintReader* reader, DWRITE_PAINT_ELEMENT* element) {
    return reader->MoveToFirstChild(element);
}
void paint_color(IDWritePaintReader* reader, DWRITE_COLOR_F color) {
    reader->SetTextColor(color);
}
''',
    "macos": '''#include <ApplicationServices/ApplicationServices.h>
#import <Metal/Metal.h>
int answer(void) { return sizeof(CFIndex); }
''',
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zig", default="zig")
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--target", choices=TARGETS, action="append")
    parser.add_argument("--macos-sdk", type=pathlib.Path)
    parser.add_argument("--windows-sdk", type=pathlib.Path,
                        help="An xwin splat containing crt/include and sdk/include")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    version = subprocess.check_output([args.zig, "version"], text=True).strip()
    results = {"zig_version": version, "targets": {}}
    with tempfile.TemporaryDirectory(prefix="staticlink-probe-") as temporary:
        source_dir = pathlib.Path(temporary)
        for name, source in SOURCES.items():
            suffix = ".mm" if name == "macos" else ".cpp"
            (source_dir / (name + suffix)).write_text(source)
        for target in args.target or TARGETS:
            destination = output / target
            destination.mkdir(exist_ok=True)
            flags = []
            if "macos" in target and args.macos_sdk:
                sdk = args.macos_sdk.resolve()
                flags += ["-isysroot", str(sdk), "-F", str(sdk / "System/Library/Frameworks")]
            if target.endswith("windows-msvc") and args.windows_sdk:
                sdk = args.windows_sdk.resolve()
                for include in ("crt/include", "sdk/include/ucrt", "sdk/include/shared", "sdk/include/um"):
                    flags += ["-isystem", str(sdk / include)]
            target_results = {}
            for name in ("plain", "cpp", "windows" if "windows" in target else "macos"):
                suffix = ".mm" if name == "macos" else ".cpp"
                command = [args.zig, "c++", "-target", target, "-std=c++20", *flags,
                           "-c", str(source_dir / (name + suffix)),
                           "-o", str(destination / (name + ".o"))]
                result = subprocess.run(command, stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT, text=True)
                (destination / (name + ".log")).write_text(result.stdout)
                target_results[name] = {"exit_code": result.returncode, "command": command}
                print(target, name, "PASS" if result.returncode == 0 else "FAIL", flush=True)
            results["targets"][target] = target_results
    (output / "results.json").write_text(json.dumps(results, indent=2) + "\n")
    return int(any(test["exit_code"] for tests in results["targets"].values() for test in tests.values()))


if __name__ == "__main__":
    raise SystemExit(main())
