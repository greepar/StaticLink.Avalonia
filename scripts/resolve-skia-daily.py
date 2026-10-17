#!/usr/bin/env python3
"""Lock the latest stable SkiaSharp release in this daily branch's major line."""
import argparse
import base64
from datetime import datetime, timezone
import json
import importlib.util
import os
from pathlib import Path
import re
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("avalonia_profile", ROOT / "scripts/resolve-avalonia-profile.py")
_profile_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_profile_module)
github, nuspec = _profile_module.github, _profile_module.nuspec


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', default='')
    args = parser.parse_args()
    config = json.loads((ROOT / 'build/skia-daily.json').read_text())
    major = config['skiasharp_major']
    if major not in (3, 4):
        raise SystemExit('Daily builds support only SkiaSharp 3 and 4')
    if os.environ.get('GITHUB_ACTIONS') == 'true':
        if os.environ.get('GITHUB_REF') != f'refs/heads/skia{major}-daily':
            raise SystemExit('Daily publication must run from its matching daily branch')
    with urllib.request.urlopen('https://api.nuget.org/v3-flatcontainer/skiasharp/index.json', timeout=30) as response:
        versions = json.load(response)['versions']
    releases = [v for v in versions if re.fullmatch(str(major) + r'\.\d+\.\d+', v)]
    if not releases:
        raise SystemExit('No published stable SkiaSharp release in this major line')
    version = args.version or max(releases, key=lambda v: tuple(map(int, v.split('.'))))
    if version not in releases:
        raise SystemExit('Requested SkiaSharp must be a published stable release in this branch major')
    avalonia = config['avalonia_version']
    path = ROOT / 'build/avalonia-profiles' / (avalonia + '.json')
    profile = json.loads(path.read_text())
    if profile['avalonia_version'] != avalonia:
        raise SystemExit('Unexpected Avalonia runtime baseline')
    # Keep the baseline's official ANGLE, but follow SkiaSharp's own HarfBuzz package.
    _, skia_repo, skia_hash = nuspec('SkiaSharp', version)
    deps, _, bridge_hash = nuspec('SkiaSharp.HarfBuzz', version)
    hb = deps['HarfBuzzSharp']
    _, hb_native_repo, hb_hash = nuspec('HarfBuzzSharp.NativeAssets.Win32', hb)
    _, hb_repo, hb_managed_hash = nuspec('HarfBuzzSharp', hb)
    for repo in (skia_repo, hb_native_repo, hb_repo):
        if not repo or not re.fullmatch('[0-9a-f]{40}', repo.get('commit', '')):
            raise SystemExit('Upstream NuGet package is missing immutable source provenance')
    if hb_native_repo['commit'] != hb_repo['commit']:
        raise SystemExit('HarfBuzz managed and native sources differ; explicit support is required')
    skia_revision = github(f"repos/mono/SkiaSharp/contents/externals/skia?ref={skia_repo['commit']}")['sha']
    hb_skia = github(f"repos/mono/SkiaSharp/contents/externals/skia?ref={hb_native_repo['commit']}")['sha']
    deps_file = github(f'repos/mono/skia/contents/DEPS?ref={hb_skia}')
    text = base64.b64decode(deps_file['content']).decode()
    match = re.search(r'"third_party/externals/harfbuzz"\s*:\s*"[^"@]+@([0-9a-f]{40})"', text)
    if not match:
        raise SystemExit('Cannot resolve the exact HarfBuzz source commit')
    # The common GN graph builds the HarfBuzz wrapper from the SkiaSharp checkout.
    # Do not combine a wrapper from one release with a managed ABI from another.
    if skia_repo['commit'] != hb_repo['commit']:
        raise SystemExit('SkiaSharp and HarfBuzz wrapper commits differ; explicit support is required')
    day = datetime.now(timezone.utc).strftime('%Y%m%d')
    run = os.environ.get('GITHUB_RUN_ID', '0')
    attempt = os.environ.get('GITHUB_RUN_ATTEMPT', '1')
    if not run.isdigit() or not attempt.isdigit():
        raise SystemExit('Invalid daily run identity')
    profile.update(
        package_version=f'{version}-preview.{day}.{run}.{attempt}',
        skiasharp_version=version, skiasharp_revision=skia_repo['commit'],
        skia_revision=skia_revision, harfbuzzsharp_version=hb,
        harfbuzzsharp_revision=hb_repo['commit'], harfbuzz_revision=match[1],
        release_channel='daily', skiasharp_major=major,
    )
    profile['official_package_sha256'].update(skiasharp=skia_hash, harfbuzz=hb_hash, harfbuzz_managed=hb_managed_hash, skiasharp_harfbuzz=bridge_hash)
    path.write_text(json.dumps(profile, indent=2) + '\n')
    print(json.dumps(profile, indent=2))


if __name__ == '__main__':
    main()
