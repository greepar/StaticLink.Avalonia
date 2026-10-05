#!/usr/bin/env python3
"""Build pinned, already dependency-synced SkiaSharp/ANGLE sources from Linux."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
from skia_compat import archive, configure, parse_args, repair_xps, repair_skcms

HERE = Path(__file__).resolve().parent


def run(args, cwd=None, env=None):
    print('+', ' '.join(map(str, args)), flush=True)
    subprocess.run(list(map(str, args)), cwd=cwd, env=env, check=True)


def patch(source, filename):
    path = HERE / 'patches' / filename
    cmd = ['git', '-C', str(source), 'apply']
    if subprocess.run(cmd + ['--reverse', '--check', str(path)], capture_output=True).returncode == 0:
        return
    run(cmd + ['--check', path])
    run(cmd + [path])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--target', choices=['linux-x64', 'linux-arm64', 'linux-musl-x64', 'linux-musl-arm64', 'win-x64', 'win-x86', 'win-arm64', 'osx-x64', 'osx-arm64'], required=True)
    p.add_argument('--sources-manifest', type=Path, help='cross-sources.json from prepare-cross-sources.sh')
    p.add_argument('--source-lock', type=Path, help='Exact version profile; defaults to sources.lock.json')
    p.add_argument('--skia', type=Path, help='SkiaSharp externals/skia, with its pinned dependencies synced')
    p.add_argument('--angle', type=Path, help='ANGLE source with pinned DEPS synced, including tools/win')
    p.add_argument('--angle-gn', type=Path, help='GN from the pinned ANGLE DEPS')
    p.add_argument('--zig', default='zig')
    p.add_argument('--sdk', type=Path, default=Path('/opt/macos-sdk/MacOSX15.5.sdk'))
    p.add_argument('--mingw-headers', type=Path, default=Path('/opt/mingw/usr/share/mingw-w64/include'))
    p.add_argument('--availability-source', type=Path, default=Path('/opt/staticlink/os_version_check.c'))
    p.add_argument('--linux-sysroots', type=Path, default=Path('/opt/sysroots'))
    p.add_argument('--linux-headers', type=Path, default=Path('/opt/staticlink/linux-headers'))
    p.add_argument('--work', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--jobs', type=int, default=4)
    p.add_argument('--configure-only', action='store_true')
    p.add_argument('--component', choices=['all', 'skia'], default='all', help='Build Skia alone when validating a new SkiaSharp release')
    a = p.parse_args()
    if a.sources_manifest:
        sources = json.loads(a.sources_manifest.read_text())
        if a.source_lock is None and sources.get('source_lock'):
            a.source_lock = Path(sources['source_lock'])
        for name in ('skia', 'angle', 'angle_gn'):
            if getattr(a, name) is None:
                setattr(a, name, Path(sources[name]))
    if any(getattr(a, name) is None for name in ('skia', 'angle', 'angle_gn')):
        p.error('Provide --sources-manifest or all of --skia, --angle and --angle-gn')
    if platform.system() != 'Linux' or a.jobs < 1:
        p.error('Requires Linux and positive --jobs')
    for name in ('skia', 'angle', 'angle_gn', 'sdk', 'work', 'output', 'availability_source', 'mingw_headers'):
        setattr(a, name, getattr(a, name).resolve())
    lock = json.loads((a.source_lock or HERE / 'sources.lock.json').read_text())
    for src, key in ((a.skia, 'skia_revision'), (a.angle, 'angle_revision')):
        revision = subprocess.check_output(['git', '-C', str(src), 'rev-parse', 'HEAD'], text=True).strip()
        if revision != lock[key]:
            raise SystemExit(f'{src}: expected {lock[key]}, got {revision}; update the lock and revalidate first')
    if 'skiasharp_build("SkiaSharp")' not in (a.skia / 'BUILD.gn').read_text():
        raise SystemExit('--skia must be the SkiaSharp-patched Skia source, not vanilla Google Skia')
    a.work.mkdir(parents=True, exist_ok=True)
    a.output.mkdir(parents=True, exist_ok=True)
    windows = a.target.startswith('win')
    mac = a.target.startswith('osx')
    linux = a.target.startswith('linux')
    cpu = a.target.rsplit('-', 1)[1]
    os_name = 'win' if windows else ('mac' if mac else 'linux')
    if windows and not (a.mingw_headers / 'windows.ui.composition.h').is_file():
        raise SystemExit('Windows ANGLE requires --mingw-headers containing the pinned WinRT headers')
    recipe = hashlib.sha256()
    for path in sorted(HERE.rglob('*')):
        if path.is_file() and (path.suffix in ('.py', '.in', '.patch', '.c') or path.name in ('cross-toolchain.lock.json', 'linux-sysroots.lock.json', 'linux-sysroots-musl.lock.json')):
            recipe.update(str(path.relative_to(HERE)).encode())
            recipe.update(path.read_bytes())
    variant = hashlib.sha256((json.dumps(lock, sort_keys=True) + recipe.hexdigest()).encode()).hexdigest()[:16]
    shared = {'angle_revision': lock['angle_revision'], 'recipe': recipe.hexdigest(), 'toolchain': json.loads((HERE / 'cross-toolchain.lock.json').read_text())}
    angle_variant = hashlib.sha256(json.dumps(shared, sort_keys=True).encode()).hexdigest()[:16]
    tools = a.work / angle_variant / a.target
    host_cpu = 'arm64' if platform.machine() == 'aarch64' else 'x64'
    host_tools = a.work / angle_variant / ('linux-' + host_cpu)
    for target, output in ((a.target, tools), ('linux-' + host_cpu, host_tools)):
        command = [sys.executable, HERE / 'zig-cross.py', '--zig', a.zig, '--target', target,
             '--output', output, '--sdk', a.sdk, '--mingw-headers', a.mingw_headers]
        if target.startswith('linux'):
            command += ['--linux-sysroot', a.linux_sysroots / target, '--linux-headers', a.linux_headers]
        run(command)
    config = json.loads((tools / 'toolchain.json').read_text())
    zig = config['zig']
    zig_lib = Path(json.loads(subprocess.check_output([zig, 'env'], text=True))['lib_dir'])
    print('skcms Clang compatibility:', repair_skcms(a.skia), flush=True)
    if windows:
        print('XPS compatibility:', repair_xps(a.skia), flush=True)
    # First apply the project's static ANGLE target patch if necessary.
    if 'angle_static_library("libANGLE_static")' not in (a.angle / 'BUILD.gn').read_text():
        patch(a.angle, 'angle-static-targets.patch')
    for filename in ('BUILDCONFIG.gn-zig.patch', 'BUILD.gn-zig.patch',
                     'sdk_info-linux.patch', 'find_sdk-linux.patch', 'gcc-toolchain-objc.patch'):
        patch(a.angle, filename)
    run([sys.executable, a.angle / 'build/util/lastchange.py', '-o', a.angle / 'build/util/LASTCHANGE'], cwd=a.angle)
    # Separate runtime paths prevent architectures from sharing an incompatible cache.
    clang = tools / 'clang'
    runtime = clang / 'lib/clang/19/lib' / ('windows' if windows else ('darwin' if mac else 'linux')) / (
        'clang_rt.builtins-' + {'x64': 'x86_64', 'x86': 'i386', 'arm64': 'aarch64'}[cpu] + '.lib'
        if windows else ('libclang_rt.osx.a' if mac else 'libclang_rt.builtins-' + ('x86_64' if cpu == 'x64' else 'aarch64') + '.a'))
    runtime.parent.mkdir(parents=True, exist_ok=True)
    run([zig, 'build-lib', zig_lib / 'compiler_rt.zig', '-target', config['target'],
         '-O', 'ReleaseFast', '-fPIC', '-femit-bin=' + str(runtime)])
    if linux:
        for runtime_cpu, runtime_target in ((cpu, config['target']), (host_cpu, json.loads((host_tools / 'toolchain.json').read_text())['target'])):
            triple = 'x86_64-unknown-linux-gnu' if runtime_cpu == 'x64' else 'aarch64-unknown-linux-gnu'
            alias = clang / 'lib/clang/19/lib' / triple / 'libclang_rt.builtins.a'
            alias.parent.mkdir(parents=True, exist_ok=True)
            run([zig, 'build-lib', zig_lib / 'compiler_rt.zig', '-target', runtime_target,
                 '-O', 'ReleaseFast', '-fPIC', '-femit-bin=' + str(alias)])
    availability = None
    if mac:
        if hashlib.sha256(a.availability_source.read_bytes()).hexdigest() != 'bc0b9f10e8d1a1ac5905d710f1c9fead23878e31233748d580393edc4e3bfc18':
            raise SystemExit('LLVM availability source checksum mismatch')
        availability = tools / 'os_version_check.o'
        run([tools / 'cc', '-c', a.availability_source, '-o', availability])
        run([tools / 'ar', 'rcs', runtime, availability])
    env = os.environ.copy()
    env['PATH'] = str(tools) + os.pathsep + env['PATH']
    env['CCACHE_BASEDIR'] = str(a.skia)
    env['CCACHE_NOHASHDIR'] = 'true'
    env['CCACHE_COMPILERCHECK'] = 'content'
    env['STATICLINK_MACOS_SDK'] = str(a.sdk)
    env['STATICLINK_DARWIN_TOOLS'] = str(tools)
    skia_out = a.skia / 'out' / ('staticlink-zig-' + a.target + '-' + variant)
    angle_out = a.angle / 'out' / ('staticlink-zig-' + a.target + '-' + angle_variant)
    for out in (skia_out, angle_out):
        out.mkdir(parents=True, exist_ok=True)
    skia_args = (HERE / ('skia-' + os_name + '.gn.in')).read_text().replace('@CPU@', cpu)
    if mac:
        skia_args += f'min_macos_version = "{"11.0" if cpu == "arm64" else "10.13"}"\n'
        skia_args += f'xcode_sysroot = {json.dumps(str(a.sdk))}\n'
        for name in ('cc', 'cxx', 'ar'):
            skia_args += name + ' = ' + json.dumps(str(tools / name)) + '\n'
    if linux:
        for key in ('cc', 'cxx', 'ar'):
            skia_args = skia_args.replace('@' + key.upper() + '@', str(tools / key))
    capabilities = configure(a.skia, skia_out, parse_args(skia_args), a.skia / 'bin/gn', env)
    for target in ('skia', 'SkiaSharp', 'HarfBuzzSharp'):
        description = json.loads(subprocess.check_output([str(a.skia / 'bin/gn'), 'desc', str(skia_out.relative_to(a.skia)),
                                       '//:' + target, '--format=json'], cwd=a.skia, env=env, text=True))
        kind = next(iter(description.values()))['type']
        if kind != 'static_library':
            raise SystemExit(f'{target} is {kind}; expected static_library')
    if windows:
        # Upstream Skia fixes Windows to the MSVC rules; retain its graph and
        # replace compiler/archive commands explicitly with the GNU adapters.
        path = skia_out / 'toolchain.ninja'
        body = path.read_text()
        index = body.index('subninja ')
        rules = ''
        for name, flags in (('cc', 'cflags_c'), ('cxx', 'cflags_cc')):
            rules += f'rule {name}\n  command = {tools / name} -MD -MF ${{out}}.d ${{defines}} ${{include_dirs}} ${{cflags}} ${{{flags}}} -c ${{in}} -o ${{out}}\n  depfile = ${{out}}.d\n  deps = gcc\n'
        rules += f'rule alink\n  command = {tools / "ar"} rcs ${{out}} @${{out}}.rsp\n  rspfile = ${{out}}.rsp\n  rspfile_content = ${{in_newline}}\n'
        rules += 'rule stamp\n  command = touch ${out}\nrule copy\n  command = cp ${in} ${out}\nrule asm\n  command = false\n'
        path.write_text(rules + '\n' + body[index:])
    sdk_link = angle_out / 'sdk/xcode_links/MacOSX15.5.sdk'
    if mac:
        sdk_link.parent.mkdir(parents=True, exist_ok=True)
        if sdk_link.is_symlink():
            sdk_link.unlink()
        sdk_link.symlink_to(a.sdk)
    # Each architecture gets an independent toolchain file; concurrent builds
    # do not rewrite another target's generated GN toolchain.
    toolchain_dir = a.angle / ('staticlink_zig_' + a.target.replace('-', '_') + '_' + angle_variant)
    toolchain_dir.mkdir(exist_ok=True)
    text = 'import("//build/toolchain/gcc_toolchain.gni")\n'
    for name, folder, target_os, target_cpu in (('target', tools, os_name, cpu), ('host', host_tools, 'linux', host_cpu)):
        text += f'gcc_toolchain("{name}") {{\n'
        for var in ('cc', 'cxx', 'ar'):
            text += '  ' + var + ' = ' + json.dumps(str(folder / var)) + '\n'
        text += f'  ld = cxx\n  nm = "nm"\n  readelf = "readelf"\n  toolchain_args = {{ current_os = "{target_os}" current_cpu = "{target_cpu}" is_clang = true use_remoteexec = false }}\n}}\n'
    (toolchain_dir / 'BUILD.gn').write_text(text)
    angle_args = (HERE / ('angle-' + os_name + '.gn.in')).read_text().replace('@CPU@', cpu)
    angle_args += f'custom_toolchain = "//{toolchain_dir.name}:target"\nhost_toolchain = "//{toolchain_dir.name}:host"\n'
    angle_args += 'clang_base_path = ' + json.dumps(str(clang)) + '\n'
    if linux:
        angle_args += 'pkg_config = ' + json.dumps(str(tools / 'pkg-config')) + '\n'
        angle_args += 'host_pkg_config = ' + json.dumps(str(host_tools / 'pkg-config')) + '\n'
    if windows:
        # These mandatory GN metadata paths refer to the real MinGW headers.
        # The SDK/version strings satisfy GN; MSVC/Windows SDK are not used.
        for name, path in (('visual_studio_path', Path(zig).parent), ('wdk_path', Path(zig).parent),
                           ('windows_sdk_path', zig_lib / 'libc/include/any-windows-any')):
            angle_args += name + ' = ' + json.dumps(str(path)) + '\n'
    (angle_out / 'args.gn').write_text(angle_args)
    run([a.angle_gn, 'gen', angle_out.relative_to(a.angle)], cwd=a.angle, env=env)
    if a.configure_only:
        print(f'Configured {lock["skiasharp_version"]} {a.target}: all three Skia targets are static libraries')
        return
    run(['ninja', '-C', skia_out, '-j', a.jobs, 'skia', 'SkiaSharp', 'HarfBuzzSharp'], env=env)
    if a.component == 'all':
        run(['ninja', '-C', angle_out, '-j', a.jobs, 'libANGLE_static', 'libGLESv2_static', 'libEGL_static'], env=env)
    if availability:
        run([tools / 'ar', 'rcs', archive(skia_out, 'skia'), availability])
    files = [(archive(skia_out, name), name)
             for name in ('skia', 'SkiaSharp', 'HarfBuzzSharp')]
    if a.component == 'all':
        files += [(angle_out / ('obj/lib' + name + '_static.a'), name) for name in ('ANGLE', 'GLESv2', 'EGL')]
    manifest = dict(target=a.target, sources=lock, toolchain=config, archives={})
    manifest['build_variant'] = variant
    manifest['skia_capabilities'] = capabilities
    if linux:
        manifest['linux_sdk_packages'] = json.loads((HERE / ('linux-sysroots-musl.lock.json' if 'musl' in a.target else 'linux-sysroots.lock.json')).read_text())[a.target]
    manifest['toolchain_inputs'] = json.loads((HERE / 'cross-toolchain.lock.json').read_text())
    manifest['gn_sha256'] = {str(path): hashlib.sha256(path.read_bytes()).hexdigest()
                            for path in (a.skia / 'bin/gn', a.angle_gn)}
    manifest['recipe_sha256'] = {str(path.relative_to(HERE)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(HERE.rglob('*')) if path.is_file() and (path.suffix in ('.py', '.in', '.patch', '.c') or path.name in ('cross-toolchain.lock.json', 'linux-sysroots.lock.json', 'linux-sysroots-musl.lock.json'))}
    packages = Path('/opt/staticlink/packages.lock')
    if packages.is_file():
        shutil.copy2(packages, a.output / 'toolchain-packages.lock')
        manifest['packages_sha256'] = hashlib.sha256(packages.read_bytes()).hexdigest()
    for source, name in files:
        dest = a.output / ('lib' + name + '.a')
        shutil.copy2(source, dest)
        manifest['archives'][dest.name] = hashlib.sha256(dest.read_bytes()).hexdigest()
    run([sys.executable, HERE / 'link-cross.py', '--toolchain', tools, '--skia', a.skia,
         '--angle', a.angle, '--libraries', a.output, '--output', a.output / 'link-tests', '--component', a.component])
    if a.target == 'win-x86':
        run([sys.executable, HERE / 'x86-thunks.py', '--source', a.skia.parent.parent,
             '--toolchain', tools, '--libraries', a.output])
    manifest['link_tests'] = 'passed; target runtime tests still required'
    (a.output / 'cross-build.json').write_text(json.dumps(manifest, indent=2) + '\n')


if __name__ == '__main__':
    main()
