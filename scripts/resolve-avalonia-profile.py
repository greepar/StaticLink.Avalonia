#!/usr/bin/env python3
"""Lock the actual native dependencies shipped by a stable Avalonia release."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import re
import subprocess
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def github(path):
    return json.loads(subprocess.check_output(['gh', 'api', path], text=True))


def nuspec(package, version):
    package = package.lower()
    cache = ROOT / 'artifacts/official-nuget'
    cache.mkdir(parents=True, exist_ok=True)
    filename = f'{package}.{version}.nupkg'
    path = cache / filename
    if not path.exists():
        urllib.request.urlretrieve(f'https://api.nuget.org/v3-flatcontainer/{package}/{version}/{filename}', path)
    with zipfile.ZipFile(path) as archive:
        xml = archive.read(next(n for n in archive.namelist() if n.endswith('.nuspec')))
    root = ET.fromstring(xml)
    dependencies = {}
    repository = None
    for item in root.iter():
        name = item.tag.rsplit('}', 1)[-1]
        if name == 'dependency':
            version_range = item.attrib['version']
            match = re.match(r'^\[?(\d+\.\d+\.\d+(?:\.\d+)?)(?:[\],]|$)', version_range)
            if not match:
                raise RuntimeError(f'Unsupported dependency range: {package}: {item.attrib}')
            value = match[1]
            previous = dependencies.setdefault(item.attrib['id'], value)
            if previous != value:
                raise RuntimeError('Framework-specific native dependency versions require explicit profiles')
        if name == 'repository':
            repository = dict(item.attrib)
    return dependencies, repository, hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--avalonia-version', required=True)
    parser.add_argument('--revision', type=int, default=1)
    args = parser.parse_args()
    if not re.fullmatch(r'(11|12)\.\d+\.\d+', args.avalonia_version) or args.revision < 1:
        parser.error('A stable Avalonia 11/12 version and positive package revision are required')
    version = args.avalonia_version
    skia_deps, _, _ = nuspec('Avalonia.Skia', version)
    win_deps, _, _ = nuspec('Avalonia.Win32', version)
    skia = skia_deps['SkiaSharp']
    hb = skia_deps['HarfBuzzSharp']
    angle = win_deps['Avalonia.Angle.Windows.Natives']
    _, skia_repo, skia_hash = nuspec('SkiaSharp', skia)
    _, hb_repo, hb_hash = nuspec('HarfBuzzSharp.NativeAssets.Win32', hb)
    _, hb_managed_repo, hb_managed_hash = nuspec('HarfBuzzSharp', hb)
    _, angle_repo, angle_hash = nuspec('Avalonia.Angle.Windows.Natives', angle)
    for repository in (skia_repo, hb_repo, hb_managed_repo, angle_repo):
        if not repository or not re.fullmatch('[0-9a-f]{40}', repository.get('commit', '')):
            raise RuntimeError('Official package is missing exact source provenance')
    skia_commit = github(f"repos/mono/SkiaSharp/contents/externals/skia?ref={skia_repo['commit']}")['sha']
    hb_skia_commit = github(f"repos/mono/SkiaSharp/contents/externals/skia?ref={hb_repo['commit']}")['sha']
    hb_deps = github(f'repos/mono/skia/contents/DEPS?ref={hb_skia_commit}')
    hb_deps = base64.b64decode(hb_deps['content']).decode()
    hb_revision = re.search(r'"third_party/externals/harfbuzz"\s*:\s*"[^"@]+@([0-9a-f]{40})"', hb_deps)[1]
    avalonia = github(f'repos/AvaloniaUI/Avalonia/git/ref/tags/{version}')['object']
    while avalonia['type'] == 'tag':
        avalonia = github(f"repos/AvaloniaUI/Avalonia/git/tags/{avalonia['sha']}")['object']
    profile = {
        'avalonia_version': version, 'avalonia_revision': avalonia['sha'],
        'package_version': f'{skia}.{args.revision}',
        'skiasharp_version': skia, 'skiasharp_revision': skia_repo['commit'],
        'skia_revision': skia_commit, 'harfbuzzsharp_version': hb,
        'harfbuzz_revision': hb_revision, 'harfbuzzsharp_revision': hb_managed_repo['commit'],
        'angle_package_version': angle, 'angle_branch': 'avalonia-' + version,
        'angle_repository': 'https://github.com/AvaloniaUI/angle.git',
        'angle_revision': angle_repo['commit'], 'angle_project_patch': None,
        'official_package_sha256': {'skiasharp': skia_hash, 'harfbuzz': hb_hash, 'harfbuzz_managed': hb_managed_hash, 'angle': angle_hash},
    }
    path = ROOT / 'build/avalonia-profiles' / (version + '.json')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(profile, indent=2) + '\n')
    print(json.dumps(profile, indent=2))


if __name__ == '__main__':
    main()
