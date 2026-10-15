#!/usr/bin/env python3
"""Validate an official Avalonia lock and expose matching workflow inputs."""
import argparse
import json
import os
from pathlib import Path
import re
from avalonia_package_versions import native_package_version

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--avalonia-version', required=True)
    parser.add_argument('--github-output', action='store_true')
    parser.add_argument('--release-lock', action='store_true')
    args = parser.parse_args()
    if not re.fullmatch(r'(11|12)\.\d+\.\d+', args.avalonia_version):
        parser.error('Use a stable Avalonia 11 or 12 version')
    path = ROOT / 'build/avalonia-profiles' / (args.avalonia_version + '.json')
    lock = json.loads(path.read_text())
    if lock['avalonia_version'] != args.avalonia_version or not re.fullmatch(
            re.escape(args.avalonia_version) + r'\.[1-9]\d*', lock['package_version']):
        raise SystemExit('Profile and stable package version do not match')
    for key in ('avalonia_revision', 'skiasharp_revision', 'skia_revision',
                'harfbuzz_revision', 'harfbuzzsharp_revision', 'angle_revision'):
        if not re.fullmatch(r'[0-9a-f]{40}', lock[key]):
            raise SystemExit('Missing immutable source commit: ' + key)
    if lock['angle_repository'] != 'https://github.com/AvaloniaUI/angle.git' or lock['angle_project_patch'] is not None:
        raise SystemExit('Official profiles must use the corresponding Avalonia ANGLE source')
    if os.environ.get('GITHUB_REF_TYPE') == 'tag' and os.environ.get('GITHUB_REF_NAME') != 'staticlink-avalonia-v' + lock['package_version']:
        raise SystemExit('Release tag does not match the official package version')
    if args.release_lock:
        (ROOT / 'build/linux-toolchain/release.lock.json').write_text(json.dumps(lock, indent=2) + '\n')
    if args.github_output:
        with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
            output.write('source_lock=' + json.dumps(lock, separators=(',', ':')) + '\n')
            for key in ('package_version', 'skiasharp_version', 'angle_branch', 'avalonia_version', 'harfbuzzsharp_version'):
                output.write(key + '=' + lock[key] + '\n')
            output.write('native_package_version=' + native_package_version(lock) + '\n')
    print(json.dumps(lock, indent=2))


if __name__ == '__main__':
    main()
