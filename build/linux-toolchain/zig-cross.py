#!/usr/bin/env python3
"""Pinned Zig compiler adapters for static-library cross-builds on Linux."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import re

TARGETS = {
    "linux-x64": "x86_64-linux-gnu.2.36.0", "linux-arm64": "aarch64-linux-gnu.2.36.0",
    "linux-musl-x64": "x86_64-linux-musl", "linux-musl-arm64": "aarch64-linux-musl",
    "win-x64": "x86_64-windows-gnu", "win-x86": "x86-windows-gnu",
    "win-arm64": "aarch64-windows-gnu", "osx-x64": "x86_64-macos.10.13.0",
    "osx-arm64": "aarch64-macos.11.0.0",
}


def mingw_overlay(zig_lib, output):
    source = zig_lib / "libc/include/any-windows-any/dwrite_3.h"
    text = source.read_text()
    # Add only non-virtual overloads/default arguments. Keep IID, virtual order,
    # virtual parameter types and C vtables exactly as supplied by MinGW.
    for name in ("IDWritePaintReader", "IDWriteFontFace4"):
        start = text.index(name + " : public")
        end = text.index("#ifdef __CRT_UUID_DECL", start)
        block = text[start:end]
        if name == "IDWritePaintReader":
            block = block.replace("UINT32 struct_size) = 0;",
                                  "UINT32 struct_size = sizeof(DWRITE_PAINT_ELEMENT)) = 0;")
            extra = """    HRESULT SetCurrentGlyph(UINT32 glyph, DWRITE_PAINT_ELEMENT *element,
        D2D_RECT_F *clip, DWRITE_PAINT_ATTRIBUTES *attributes = 0) {
        return SetCurrentGlyph(glyph, element, sizeof(DWRITE_PAINT_ELEMENT), clip, attributes);
    }
    HRESULT SetTextColor(const DWRITE_COLOR_F &color) { return SetTextColor(&color); }
"""
        else:
            extra = """    HRESULT GetGlyphImageFormats(UINT16 glyph, UINT32 first, UINT32 last,
        DWRITE_GLYPH_IMAGE_FORMATS *formats) {
        return GetGlyphImageFormats_(glyph, first, last, formats);
    }
"""
        index = block.rindex("};")
        block = block[:index] + extra + block[index:]
        text = text[:start] + block + text[end:]
    output.mkdir(parents=True, exist_ok=True)
    (output / "dwrite_3.h").write_text(text)
    for name in ("XpsObjectModel.h", "ObjBase.h", "DispatcherQueue.h", "VersionHelpers.h", "T2EmbApi.h", "FontSub.h"):
        alias = output / name
        if alias.is_symlink():
            alias.unlink()
        alias.symlink_to(source.parent / name.lower())
    return hashlib.sha256(source.read_bytes()).hexdigest()


def compiler(config, tool, incoming):
    target = config["target"]
    if "--version" in incoming and "linux-gnu." in target:
        target = target.split("linux-gnu.")[0] + "linux-gnu"
    windows = "windows" in target
    args = ["-I" + config["include"]] if windows else [
        "-isysroot", config["sdk"], "-idirafter", config["sdk"] + "/usr/include",
        "-F", config["sdk"] + "/System/Library/Frameworks", "-Wno-elaborated-enum-base",
    ] if "macos" in target else []
    if config.get('linux_abi_headers'):
        args += ['-idirafter', config['linux_abi_headers']]
    if config.get('linux_headers'):
        args += ['-idirafter', config['linux_headers'], '-idirafter', config['linux_headers'] + '/freetype2']
    if config.get('linux_sysroot') and '-c' not in incoming and '-o' in incoming:
        root = Path(config['linux_sysroot'])
        cpu = 'x86_64' if target.startswith('x86_64') else 'aarch64'
        for path in (root / 'usr/lib' / (cpu + '-linux-gnu'), root / 'lib' / (cpu + '-linux-gnu'), root / 'usr/lib', root / 'lib'):
            args += ['-L' + str(path)]
    if 'linux' in target and '-c' not in incoming and '-o' in incoming:
        args.append('-fuse-ld=lld')
    if windows:
        # Accept Windows header/Skia spellings such as __forceinline while
        # retaining the GNU target ABI and leaving _MSC_VER undefined.
        args.append("-fms-extensions")
    if windows and config.get("mingw_headers"):
        args.extend(("-idirafter", config["mingw_headers"]))
    mapping = {
        "/O2": "-O2", "/fp:precise": "-ffp-model=precise", "/std:c++20": "-std=c++20",
        "/std:c11": "-std=c11", "/GR": "-frtti", "/GR-": "-fno-rtti", "/w": "-w",
        "/Ob2": "-finline-functions", "/arch:AVX2": "-mcpu=x86_64_v3",
        "/arch:AVX512": "-mcpu=x86_64_v4+evex512", "/TC": "-xc", "/TP": "-xc++",
        "/Gy": "-ffunction-sections", "/Gw": "-fdata-sections",
        "/Oy-": "-fno-omit-frame-pointer", "/guard:cf": "-mguard=cf",
        "/W3": "-Wall",
        "-march=x86-64-v3": "-mcpu=x86_64_v3", "-march=x86-64-v4": "-mcpu=x86_64_v4+evex512",
        "-march=armv8-a+crc+crypto": "-mcpu=generic+crc+aes+sha2",
    }
    iterator = iter(incoming)
    for flag in iterator:
        if flag in ("-Wl,--fatal-warnings", "-Wl,--disable-new-dtags"):
            continue
        if flag in ("-o", "-MF", "-MT", "-MQ", "-I", "-isystem", "-isysroot", "-F", "-idirafter", "-include"):
            args.extend((flag, next(iterator)))
            continue
        if flag in ("-target", "--target"):
            next(iterator)
            continue
        if flag.startswith("--target="):
            continue
        if flag.startswith("/clang:"):
            flag = flag[7:]
        if flag.startswith(("-fdiagnostics-show-inlining-chain", "-fno-lifetime-dse",
                            "-fsanitize-ignore-for-ubsan-feature=", "-fmsc-version=")):
            continue
        if flag.startswith("/D"):
            flag = "-D" + flag[2:]
        if re.fullmatch(r"/std:(c\+\+\d+|c\d+)", flag):
            flag = "-std=" + flag[5:]
        if flag in ("/arch:SSE", "/arch:SSE2", "/arch:AVX"):
            flag = {"/arch:SSE": "-msse", "/arch:SSE2": "-msse2", "/arch:AVX": "-mavx"}[flag]
        if flag == "/W4":
            args.extend(("-Wall", "-Wextra"))
            continue
        if flag in ("/bigobj", "/utf-8", "/Zc:inline", "/Zc:lambda", "/Zc:twoPhase", "/FS", "/MT"):
            continue
        if flag.startswith(("/wd", "/we")):
            continue  # MSVC diagnostic numbers have no GNU Clang equivalent.
        if windows and flag.startswith("/") and flag not in mapping and not Path(flag).exists():
            raise SystemExit("Unsupported MSVC option: " + flag)
        if flag == '-stdlib=libstdc++':
            flag = '-stdlib=libc++'
        args.append(mapping.get(flag, flag))
    if any(flag.startswith("-mavx512") for flag in args):
        args.append("-mevex512")
    if windows:
        if "-DCRC32_SIMD_SSE42_PCLMUL" in args:
            args.extend(("-msse4.2", "-mpclmul"))
        if "-DADLER32_SIMD_SSSE3" in args:
            args.append("-mssse3")
    # Older MSVC GN rules express SSE dispatch through a macro: Clang needs
    # matching CPU features on those units, never on ordinary baseline units.
    if target.startswith(("x86", "i386")):
        levels = {"SSE2": ["-msse2"], "SSE3": ["-msse3"], "SSSE3": ["-mssse3"],
                  "SSE41": ["-msse4.1"], "SSE42": ["-msse4.2", "-mcrc32"]}
        for level, features in levels.items():
            if "-DSK_CPU_SSE_LEVEL=SK_CPU_SSE_LEVEL_" + level in args:
                args.extend(features)
    return [config["zig"], "cc" if tool == "cc" else "c++", "-target", target, *args]


def execute(config, tool, incoming):
    if tool in ("cc", "cxx"):
        command = compiler(config, tool, incoming)
    elif tool == "ar":
        flags = [x.replace("rcsT", "rcs") for x in incoming if x not in ("/WX", "/ignore:4221", "-T", "--thin")]
        command = [config["zig"], "ar"]
        if "macos" in config["target"]:
            command.append("--format=darwin")
        command += flags
    else:
        output = None
        inputs = []
        iterator = iter(incoming)
        for flag in iterator:
            if flag in ("-static", "-no_warning_for_no_symbols"):
                continue
            if flag == "-o":
                output = next(iterator)
            elif flag == "-filelist":
                inputs.extend(Path(next(iterator)).read_text().splitlines())
            elif flag.startswith("@"):
                inputs.extend(shlex.split(Path(flag[1:]).read_text()))
            else:
                inputs.append(flag)
        if not output:
            raise SystemExit("Darwin libtool adapter needs -o")
        libtool = shutil.which('llvm-libtool-darwin') or shutil.which('llvm-libtool-darwin-16')
        if not libtool:
            raise SystemExit('The pinned image must provide llvm-libtool-darwin to flatten archive dependencies')
        command = [libtool, '-static', '-o', output, *inputs]
    if tool in ('ar', 'libtool'):
        # Never leave a truncated archive behind when disk/network/job failures
        # interrupt archiving. GN response files contain a complete member list.
        index = next((i for i, arg in enumerate(command[2:], 2)
                      if not arg.startswith('@') and Path(arg).suffix in ('.a', '.lib')), None)
        if index is None:
            raise SystemExit('Cannot identify archive output: ' + str(command))
        dest = Path(command[index])
        temporary = dest.with_name(dest.name + '.tmp-' + str(os.getpid()))
        temporary.unlink(missing_ok=True)
        objects = [x for x in command[index + 1:] if not x.startswith('-')]
        if tool == 'ar' and dest.exists() and len(objects) == 1 and not objects[0].startswith('@'):
            shutil.copy2(dest, temporary)  # Explicit runtime/availability append.
        command[index] = str(temporary)
        try:
            subprocess.run(command, check=True)
            os.replace(temporary, dest)
        finally:
            temporary.unlink(missing_ok=True)
        return
    cache = shutil.which('ccache')
    if tool in ('cc', 'cxx') and cache and os.environ.get('CCACHE_DIR') and '-c' in incoming:
        os.environ['CCACHE_COMPILERTYPE'] = 'clang'
        raw = str(Path(config['output']) / ('_cached-' + tool))
        os.execv(cache, [cache, raw, *command[4:]])
    os.execv(config["zig"], command)


def prepare(args):
    zig = str(Path(shutil.which(args.zig) or args.zig).resolve())
    version = subprocess.check_output([zig, "version"], text=True).strip()
    if version != "0.14.1":
        raise SystemExit("This adapter is verified with Zig 0.14.1; got " + version)
    lib = Path(json.loads(subprocess.check_output([zig, "env"], text=True))["lib_dir"])
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    config = {"zig": zig, "target": TARGETS[args.target], "version": version}
    if args.target.startswith("win"):
        include = output / "include"
        # Regeneration is idempotent; remove only the generated SDK case alias.
        alias = include / "XpsObjectModel.h"
        if alias.is_symlink():
            alias.unlink()
        config["mingw_header_sha256"] = mingw_overlay(lib, include)
        config["include"] = str(include)
        if args.mingw_headers:
            config["mingw_headers"] = str(args.mingw_headers.resolve())
            header = args.mingw_headers / "windows.ui.composition.h"
            if header.is_file():
                original = header.read_text()
                text = original
                # WIDL 11 omitted namespace qualification on these imported
                # types. Use the real declarations already imported by the
                # header; preserve interface UUIDs and method/vtable order.
                for name in ("DirectXAlphaMode", "DirectXPixelFormat"):
                    text = text.replace("enum " + name, "enum ABI::Windows::Graphics::DirectX::" + name)
                text = text.replace("struct Size", "struct ABI::Windows::Foundation::Size")
                for name in ("Vector2", "Vector3", "Vector4", "Matrix3x2", "Matrix4x4", "Quaternion"):
                    text = text.replace("struct " + name, "struct ABI::Windows::Foundation::Numerics::" + name)
                (include / header.name).write_text(text)
                config["composition_header_sha256"] = hashlib.sha256(header.read_bytes()).hexdigest()
    elif args.target.startswith("osx"):
        if not args.sdk or not (args.sdk / "SDKSettings.json").is_file():
            raise SystemExit("macOS target requires --sdk pointing to a macOS SDK")
        config["sdk"] = str(args.sdk.resolve())
        settings = args.sdk / "SDKSettings.json"
        if json.loads(settings.read_text()).get("Version") != "15.5":
            raise SystemExit("ANGLE metadata adapter is pinned to macOS SDK 15.5")
        config["sdk_settings_sha256"] = hashlib.sha256(settings.read_bytes()).hexdigest()
    if args.target.startswith('linux'):
        config['linux_sysroot'] = str(args.linux_sysroot.resolve()) if args.linux_sysroot else ''
        config['linux_headers'] = str(args.linux_headers.resolve()) if args.linux_headers else ''
    config['output'] = str(output)
    if args.target.startswith('linux'):
        root = Path(config['linux_sysroot'])
        abi = output / 'include-linux'
        abi.mkdir(exist_ok=True)
        cpu = 'x86_64' if config['target'].startswith('x86_64') else 'aarch64'
        for name in ('ffi.h', 'ffitarget.h', 'expat.h', 'expat_external.h'):
            for prefix in (root / 'usr/include' / (cpu + '-linux-gnu'), root / 'usr/include'):
                src = prefix / name
                if src.is_file():
                    (abi / name).write_bytes(src.read_bytes())
                    break
        config['linux_abi_headers'] = str(abi)
        gl_headers = abi / 'GL'
        gl_headers.mkdir(exist_ok=True)
        for prefix in (root / 'usr/include/GL', Path('/usr/include/GL')):
            for header in prefix.glob('*.h'):
                destination = gl_headers / header.name
                if not destination.exists():
                    destination.write_bytes(header.read_bytes())
        if not (gl_headers / 'glx.h').is_file():
            raise SystemExit('The pinned Linux SDK/image lacks GL/glx.h')
        pc = output / 'pkg-config'
        dirs = [root / 'usr/lib' / (cpu + '-linux-gnu') / 'pkgconfig', root / 'usr/lib/pkgconfig', root / 'usr/share/pkgconfig']
        pc.write_text('#!/bin/sh\nexport PKG_CONFIG_SYSROOT_DIR=' + shlex.quote(str(root)) + '\nexport PKG_CONFIG_LIBDIR=' + shlex.quote(':'.join(map(str, dirs))) + '\nexec /usr/bin/pkg-config "$@"\n')
        pc.chmod(0o755)
    for kind in ('cc', 'cxx'):
        raw = output / ('_cached-' + kind)
        mode = 'cc' if kind == 'cc' else 'c++'
        raw.write_text('#!/bin/sh\nexec ' + shlex.quote(zig) + ' ' + mode + ' -target ' + shlex.quote(config['target']) + ' "$@"\n')
        raw.chmod(0o755)
    descriptor = output / "toolchain.json"
    descriptor.write_text(json.dumps(config, indent=2) + "\n")
    for tool in ("cc", "cxx", "ar", "libtool"):
        executable = output / tool
        executable.write_text("#!/bin/sh\nexec python3 " + shlex.quote(str(Path(__file__).resolve())) +
                              " run " + shlex.quote(str(descriptor)) + " " + tool + ' "$@"\n')
        executable.chmod(0o755)
    print(descriptor)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "run":
        execute(json.loads(Path(sys.argv[2]).read_text()), sys.argv[3], sys.argv[4:])
    else:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument("--zig", default="zig")
        parser.add_argument("--target", choices=TARGETS, required=True)
        parser.add_argument("--sdk", type=Path)
        parser.add_argument("--mingw-headers", type=Path, help="Pinned extra WinRT headers, after Zig's headers")
        parser.add_argument("--linux-sysroot", type=Path)
        parser.add_argument("--linux-headers", type=Path)
        parser.add_argument("--output", type=Path, required=True)
        prepare(parser.parse_args())
