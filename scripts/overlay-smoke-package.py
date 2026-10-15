#!/usr/bin/env python3
"""Re-test linker targets against an existing CI package without recompiling Skia."""
import argparse
import json
from pathlib import Path
import shutil
import time
import zipfile

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--package', type=Path, required=True)
p.add_argument('--targets', type=Path, required=True)
p.add_argument('--native-root', type=Path)
p.add_argument('--rids', nargs='+', choices=['win-x64', 'win-x86'], default=['win-x64', 'win-x86'])
a = p.parse_args()
replacements = {'buildTransitive/StaticLink.Avalonia.targets': a.targets}
for helper in a.targets.parent.glob('StaticLink.Avalonia.*.ps1'):
    replacements['buildTransitive/' + helper.name] = helper
if a.native_root:
    with zipfile.ZipFile(a.package) as package:
        baseline = json.loads(package.read('buildMetadata/sources.lock.json'))
    for rid in a.rids:
        native = a.native_root / ('native-static-' + rid) / 'native'
        if not (native / 'zig-build.json').is_file():
            raise SystemExit('Missing replacement native manifest: ' + str(native))
        manifest = json.loads((native / 'zig-build.json').read_text())
        if manifest['target'] != rid or manifest['sources'] != baseline or not manifest['toolchain'].get('windows7_compat'):
            raise SystemExit('Replacement must match baseline sources and the Win7 native profile: ' + rid)
        for path in native.rglob('*'):
            if path.is_file():
                replacements['static/' + rid + '/native/' + path.relative_to(native).as_posix()] = path
temporary = a.package.with_suffix('.overlay.nupkg')
with zipfile.ZipFile(a.package) as original, zipfile.ZipFile(temporary, 'w', zipfile.ZIP_STORED) as result:
    names = set()
    for entry in original.infolist():
        name = entry.filename
        if name == '.signature.p7s':
            continue
        # Runtime archive names can differ with the minimum OS target. Do not
        # leave stale normal-profile libraries in a Win7 replacement directory.
        if a.native_root and name.startswith(tuple('static/' + rid + '/native/' for rid in a.rids)):
            continue
        result.writestr(entry, replacements[name].read_bytes() if name in replacements else original.read(entry))
        names.add(name)
    for name, path in replacements.items():
        if name not in names:
            # NuGet interprets ZIP timestamps as UTC. Local wall time in a
            # UTC+ timezone makes new libraries appear to be in the future,
            # breaking AotAnywhere's incremental takeover of LinkNative.
            entry = zipfile.ZipInfo(name, time.gmtime()[:6])
            result.writestr(entry, path.read_bytes())
shutil.move(temporary, a.package)
print('Updated smoke-only package:', a.package)
