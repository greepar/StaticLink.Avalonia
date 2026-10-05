#!/usr/bin/env python3
"""Link raster/HarfBuzz and EGL/GLES executables against cross-built archives."""
import argparse
import json
from pathlib import Path
import subprocess
import re

HERE = Path(__file__).resolve().parent


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--toolchain', type=Path, required=True)
    p.add_argument('--skia', type=Path, required=True)
    p.add_argument('--angle', type=Path, required=True)
    p.add_argument('--libraries', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--component', choices=['all', 'skia'], default='all')
    a = p.parse_args()
    config = json.loads((a.toolchain / 'toolchain.json').read_text())
    windows = 'windows' in config['target']
    a.output.mkdir(parents=True, exist_ok=True)
    target = config['target']
    flags = []
    mac = 'macos' in target
    linux = 'linux' in target
    if mac:
        # ANGLE's pinned Chromium build has a macOS 13 deployment minimum.
        target = target.split('-macos.')[0] + '-macos.13.0'
        sdk = config['sdk']
        flags = ['-isysroot', sdk, '-L' + sdk + '/usr/lib', '-F' + sdk + '/System/Library/Frameworks']
    for name in (('raster', 'angle') if a.component == 'all' else ('raster',)):
        obj = a.output / ('smoke-' + name + '.o')
        includes = [a.skia, a.skia / 'third_party/externals/harfbuzz/src', a.angle / 'include']
        command = [str(a.toolchain / 'cc')]
        if name == 'angle':
            command.extend(('-DANGLE_STATIC=1', '-DKHRONOS_STATIC'))
        else:
            header = (a.skia / 'include/core/SkMilestone.h').read_text()
            match = re.search(r'^\s*#define\s+SK_MILESTONE\s+(\d+)', header, re.MULTILINE)
            if not match:
                raise SystemExit('Cannot discover the Skia milestone; inspect the new source layout')
            command.append('-DSTATICLINK_EXPECTED_MILESTONE=' + match[1])
        command += ['-I' + str(path) for path in includes]
        command += ['-c', str(HERE / ('smoke-' + name + '.c')), '-o', str(obj)]
        subprocess.run(command, check=True)
        libs = ('SkiaSharp', 'skia', 'HarfBuzzSharp') if name == 'raster' else ('EGL', 'GLESv2', 'ANGLE')
        command = [config['zig'], 'c++', '-target', target, '-O2', *flags, str(obj)]
        command += [str(a.libraries / ('lib' + library + '.a')) for library in libs]
        if windows:
            command += ['-l' + lib for lib in ('dwrite', 'gdi32', 'ole32', 'oleaut32', 'user32', 'uuid',
                        'windowscodecs', 'dxguid', 'dxgi', 'd3d11', 'd3d9', 'dwmapi', 'shlwapi', 'setupapi', 'version', 'advapi32')]
            if not config.get('windows7_compat'):
                command += ['-lapi-ms-win-core-synch-l1-2-0']
        elif mac:
            for framework in ('CoreFoundation', 'CoreGraphics', 'CoreText', 'Foundation', 'AppKit',
                              'Metal', 'QuartzCore', 'OpenGL', 'IOKit', 'IOSurface'):
                command += ['-framework', framework]
            command += ['-lobjc']
            availability = a.toolchain / 'os_version_check.o'
            if availability.is_file():
                command.append(str(availability))
        elif linux:
            sysroot = Path(config.get('linux_sysroot') or '/')
            for path in (sysroot / 'usr/lib', sysroot / 'lib', sysroot / 'usr/lib' / ('x86_64-linux-gnu' if target.startswith('x86_64') else 'aarch64-linux-gnu')):
                if path.is_dir():
                    command += ['-L' + str(path)]
            command += ['-lfontconfig', '-ldl', '-lm', '-lpthread'] if name == 'raster' else ['-lX11', '-lXext', '-lxcb', '-lwayland-client', '-lwayland-egl', '-lffi', '-ldl', '-lm', '-lpthread']
        command += ['-v']
        command += ['-o', str(a.output / ('smoke-' + name + ('.exe' if windows else '')))]
        result = subprocess.run(command, capture_output=True, text=True)
        print(result.stdout, end='')
        print(result.stderr, end='')
        result.check_returncode()
        if config.get('windows7_compat'):
            imports = subprocess.check_output(['llvm-readobj-16', '--coff-imports', str(a.output / ('smoke-' + name + '.exe'))], text=True)
            forbidden = ('WaitOnAddress', 'WakeByAddressSingle', 'WakeByAddressAll', 'GetSystemTimePreciseAsFileTime', 'CreateFile2', 'SetThreadDescription', 'GetTempPath2W', 'GetTempPath2A')
            found = [symbol for symbol in forbidden if re.search(r'\bSymbol: ' + symbol + r'\b', imports)]
            if found:
                raise SystemExit('Win7-incompatible direct imports: ' + ', '.join(found))
            (a.output / ('smoke-' + name + '-imports.txt')).write_text(imports)
        # Keep the exact runtime archives chosen by this Zig target. AOT consumes
        # these without substituting the consumer machine's C++ toolchain.
        import shlex, shutil
        runtimes = {}
        project_archives = {path.resolve() for path in a.libraries.glob('lib*.a')}
        for line in (result.stdout + '\n' + result.stderr).splitlines():
            try:
                tokens = shlex.split(line)
            except ValueError:
                continue
            for token in tokens:
                path = Path(token)
                if path.suffix in ('.a', '.lib') and path.is_file() and path.resolve() not in project_archives and not path.resolve().is_relative_to(a.libraries.resolve()):
                    dest = a.libraries / 'zig-runtime' / path.name
                    dest.parent.mkdir(exist_ok=True)
                    shutil.copy2(path, dest)
                    runtimes[path.name] = str(path)
        descriptor = a.libraries / 'zig-runtime' / 'inputs.json'
        if descriptor.exists():
            runtimes = dict(json.loads(descriptor.read_text()), **runtimes)
        descriptor.parent.mkdir(exist_ok=True)
        descriptor.write_text(json.dumps(runtimes, indent=2) + '\n')
    print('Executable link tests passed. Run them on the target OS to validate behavior.')


if __name__ == '__main__':
    main()
