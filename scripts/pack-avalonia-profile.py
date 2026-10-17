#!/usr/bin/env python3
"""Pack complete locally validated archives for an exact official Avalonia profile."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile
import xml.etree.ElementTree as ET
from avalonia_package_versions import native_package_version

ROOT = Path(__file__).resolve().parents[1]
RIDS = ['linux-x64', 'linux-arm64', 'linux-musl-x64', 'linux-musl-arm64',
        'win-x64', 'win-x86', 'win-arm64', 'osx-x64', 'osx-arm64']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--avalonia-version', required=True)
    parser.add_argument('--graphics-only', action='store_true', help='Pack graphics without building or packing the independent macOS Native package')
    parser.add_argument('--validation-dir', type=Path, default=ROOT / 'artifacts/avalonia-validation')
    args = parser.parse_args()
    profile_path = ROOT / 'build/avalonia-profiles' / (args.avalonia_version + '.json')
    profile = json.loads(profile_path.read_text())
    native_version = native_package_version(profile)
    report = json.loads((args.validation_dir / 'matrix.json').read_text())
    if report.get('environment_exit_code') != 0:
        raise SystemExit('The toolchain environment gate must pass before packing')
    recipe = None
    for rid in RIDS:
        key = args.avalonia_version + '/' + rid
        if report['builds'].get(key, {}).get('status') != 'passed':
            raise SystemExit('Cannot pack an incomplete matrix: ' + key)
        manifest = json.loads((args.validation_dir / args.avalonia_version / rid / 'native/zig-build.json').read_text())
        if manifest['sources'] != profile:
            raise SystemExit('Archive source provenance does not match the candidate: ' + rid)
        if recipe is None:
            recipe = manifest['recipe_sha256']
        if manifest['recipe_sha256'] != recipe:
            raise SystemExit('Target archives were built from different compiler recipes')
        for relative, expected in recipe.items():
            if hashlib.sha256((ROOT / 'build/linux-toolchain' / relative).read_bytes()).hexdigest() != expected:
                raise SystemExit('Compiler recipe changed after the target was validated: ' + relative)
        windows_names = {'libskia.a': 'skia.lib', 'libSkiaSharp.a': 'SkiaSharp.lib',
                         'libHarfBuzzSharp.a': 'libHarfBuzzSharp.lib', 'libANGLE.a': 'libANGLE_static.lib',
                         'libGLESv2.a': 'libGLESv2_static.lib', 'libEGL.a': 'libEGL_static.lib'}
        unix_names = dict(windows_names, **{'libANGLE.a': 'libANGLE_static.a',
                                          'libGLESv2.a': 'libGLESv2_static.a', 'libEGL.a': 'libEGL_static.a'})
        unix_names.update({name: name for name in ('libskia.a', 'libSkiaSharp.a', 'libHarfBuzzSharp.a')})
        for source, expected in manifest['archives'].items():
            filename = (windows_names if rid.startswith('win') else unix_names).get(source, source)
            path = args.validation_dir / args.avalonia_version / rid / 'native' / filename
            if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                raise SystemExit('Candidate archive was modified after validation: ' + str(path))
    feed = ROOT / 'artifacts/avalonia-packages' / args.avalonia_version
    feed.mkdir(parents=True, exist_ok=True)
    if not args.graphics_only:
        native_root = ROOT / 'artifacts/avalonia-native' / args.avalonia_version
        for rid in ('osx-x64', 'osx-arm64'):
            native = native_root / rid / 'native'
            manifest = json.loads((native / 'avalonia-native-build.json').read_text())
            if manifest['source_commit'] != profile['avalonia_revision']:
                raise SystemExit('Avalonia.Native source does not match the official release')
            for filename in ('libAvaloniaNative.a', 'macos_font_preinit.o'):
                if not (native / filename).is_file():
                    raise SystemExit('Missing native archive: ' + filename)
        for previous in feed.glob('StaticLink.Avalonia.Native.*.nupkg'):
            if previous.name != 'StaticLink.Avalonia.Native.' + native_version + '.nupkg':
                previous.unlink()
        subprocess.run(['dotnet', 'pack', str(ROOT / 'NuGet/AvaloniaNative/StaticLink.Avalonia.Native.csproj'),
                        '-c', 'Release', '-bl:' + str(feed / 'pack-{}.binlog'), '-o', str(feed), '-p:PackageVersion=' + native_version,
                        '-p:StaticLinkAvaloniaNativeArchivesRoot=' + str(native_root)], check=True)
    config = ET.Element('configuration')
    sources = ET.SubElement(config, 'packageSources')
    ET.SubElement(sources, 'clear')
    ET.SubElement(sources, 'add', key='local-staticlink', value=str(feed))
    ET.SubElement(sources, 'add', key='nuget.org', value='https://api.nuget.org/v3/index.json')
    mapping = ET.SubElement(config, 'packageSourceMapping')
    local = ET.SubElement(mapping, 'packageSource', key='local-staticlink')
    ET.SubElement(local, 'package', pattern='StaticLink.Avalonia*')
    upstream = ET.SubElement(mapping, 'packageSource', key='nuget.org')
    ET.SubElement(upstream, 'package', pattern='*')
    config_path = feed / 'NuGet.config'
    ET.ElementTree(config).write(config_path, encoding='utf-8', xml_declaration=True)
    subprocess.run(['dotnet', 'pack', str(ROOT / 'NuGet/StaticGraphics/StaticLink.Avalonia.csproj'),
                    '-c', 'Release', '-bl:' + str(feed / 'pack-{}.binlog'), '-o', str(feed), '-p:PackageVersion=' + profile['package_version'],
                    '-p:StaticLinkSkiaSharpVersion=[' + profile['skiasharp_version'] + ']',
                    '-p:StaticLinkHarfBuzzSharpVersion=[' + profile['harfbuzzsharp_version'] + ']',
                    '-p:RestoreConfigFile=' + str(config_path),
                    '-p:RestoreForce=true',
                    '-p:StaticLinkNativeArchivesRoot=' + str((args.validation_dir / args.avalonia_version).resolve()),
                    '-p:StaticLinkSourceLockFile=' + str(profile_path)], check=True)
    package = feed / ('StaticLink.Avalonia.' + profile['package_version'] + '.nupkg')
    with zipfile.ZipFile(package) as archive:
        names = set(archive.namelist())
        if any('\\' in name for name in names):
            raise SystemExit('NuGet contains non-portable Windows paths')
        for rid in RIDS:
            if f'static/{rid}/native/zig-build.json' not in names:
                raise SystemExit('Packed candidate is missing target ' + rid)
        spec = ET.fromstring(archive.read(next(name for name in names if name.endswith('.nuspec'))))
        dependencies = [item for item in spec.iter() if item.tag.rsplit('}', 1)[-1] == 'dependency']
        if any(item.attrib.get('id', '').lower().startswith('avalonia') for item in dependencies):
            raise SystemExit('The graphics package must not select the consumer Avalonia version')
        if any(item.attrib.get('id') == 'StaticLink.Avalonia.Native' for item in dependencies):
            raise SystemExit('The graphics package must not depend on the separate macOS Native package')
    print('Complete stable candidate packed:', package)


if __name__ == '__main__':
    main()
