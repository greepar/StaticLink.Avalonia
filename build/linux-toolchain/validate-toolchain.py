#!/usr/bin/env python3
"""Validate the actual release container before compiling native libraries."""
import argparse
import inspect
import json
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import tarfile
import tempfile


def run(command):
    print("+", " ".join(map(str, command)), flush=True)
    return subprocess.check_output(list(map(str, command)), text=True, stderr=subprocess.STDOUT)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--rids", default="[]")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    report = {"python": sys.version, "targets": {}, "passed": False}
    try:
        if "filter" not in inspect.signature(tarfile.TarFile.extractall).parameters:
            raise RuntimeError("depot_tools requires tarfile extraction filters")
        for module in ("six", "requests", "httplib2"):
            __import__(module)
        run([sys.executable, "/opt/depot_tools/gclient.py", "help"])
        for tool in ("git", "ninja", "clang", "llvm-ar", "lld", "pkg-config", "cmake", "patch", "file", "dotnet", "zig"):
            if not shutil.which(tool):
                raise RuntimeError("Missing tool: " + tool)
        report["zig"] = run(["zig", "version"]).strip()
        if report["zig"] != "0.14.1":
            raise RuntimeError("Unexpected Zig version")
        report["dotnet_sdks"] = run(["dotnet", "--list-sdks"]).splitlines()
        for major in ("8.", "10."):
            if not any(version.startswith(major) for version in report["dotnet_sdks"]):
                raise RuntimeError("Missing .NET SDK " + major)
        adapter = Path(__file__).with_name("zig-cross.py")
        targets = runpy.run_path(str(adapter))["TARGETS"]
        requested = json.loads(args.rids)
        if not isinstance(requested, list) or any(rid not in targets for rid in requested):
            raise ValueError("Expected a JSON array of supported RIDs")
        if requested:
            targets = {rid: targets[rid] for rid in requested}
        sdk = Path("/opt/macos-sdk/MacOSX15.5.sdk")
        if json.loads((sdk / "SDKSettings.json").read_text())["Version"] != "15.5":
            raise RuntimeError("Unexpected macOS SDK version")
        with tempfile.TemporaryDirectory(prefix="staticlink-environment-") as temporary:
            work = Path(temporary)
            plain = work / "main.c"
            plain.write_text("int main(void) { return 0; }\n")
            cpp = work / "probe.cpp"
            for rid in targets:
                target_work = work / rid
                command = [sys.executable, adapter, "--target", rid, "--output", target_work,
                           "--sdk", sdk, "--mingw-headers", "/opt/mingw/usr/share/mingw-w64/include"]
                source = "#include <string>\nint value() { return int(std::string(\\\"ok\\\").size()); }\n".replace('\\\"', '"')
                if rid.startswith("linux"):
                    sysroot = Path("/opt/sysroots") / rid
                    if not (sysroot / "usr/include").is_dir():
                        raise RuntimeError("Missing sysroot: " + rid)
                    if not (sysroot / "usr/include/wayland-client.h").is_file():
                        raise RuntimeError("Missing Wayland headers: " + rid)
                    command += ["--linux-sysroot", sysroot, "--linux-headers", "/opt/staticlink/linux-headers"]
                    source += "#include <fontconfig/fontconfig.h>\n#include <ffi.h>\n#include <ft2build.h>\n#include FT_FREETYPE_H\n"
                elif rid.startswith("win"):
                    source += "#include <windows.h>\n#include <dwrite_3.h>\n#include <XpsObjectModel.h>\n#include <windows.ui.composition.h>\n"
                cpp.write_text(source)
                run(command)
                run([target_work / "cxx", "-std=c++17", "-c", cpp, "-o", target_work / "cpp.o"])
                run([target_work / "cc", "-c", plain, "-o", target_work / "main.o"])
                run([target_work / "ar", "rcs", target_work / "probe.a", target_work / "main.o"])
                executable = target_work / ("probe.exe" if rid.startswith("win") else "probe")
                run([target_work / "cc", plain, "-o", executable])
                if rid.startswith("osx"):
                    objc = work / "probe.mm"
                    objc.write_text("#import <Cocoa/Cocoa.h>\n#import <Metal/Metal.h>\nint value() { return sizeof(CFIndex); }\n")
                    run([target_work / "cxx", "-fobjc-arc", "-fblocks", "-c", objc, "-o", target_work / "objc.o"])
                report["targets"][rid] = {
                    "passed": True,
                    "object": run(["file", target_work / "main.o"]).strip(),
                    "executable": run(["file", executable]).strip(),
                }
                print(rid + ": C/C++ compile, archive and executable link PASS", flush=True)
        report["passed"] = True
    except Exception as error:
        report["error"] = str(error)
        if isinstance(error, subprocess.CalledProcessError):
            report["error_output"] = error.output
            print(error.output, flush=True)
        raise
    finally:
        (args.output / "environment-validation.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
