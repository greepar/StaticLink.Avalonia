#!/usr/bin/env python3
"""Fetch a pinned, previously validated macOS Native package for smoke tests only."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
import zipfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--avalonia-version', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--artifact-archive', type=Path,
                        help='Verify an already downloaded artifact instead of fetching it')
    args = parser.parse_args()
    dependencies = json.loads((ROOT / 'build/avalonia-native-smoke-dependencies.json').read_text())
    if args.avalonia_version not in dependencies:
        raise SystemExit('No validated macOS Native smoke dependency for Avalonia ' + args.avalonia_version +
                         '; validate it independently, then update the pinned dependency manifest.')
    dependency = dependencies[args.avalonia_version]
    filename = 'StaticLink.Avalonia.Native.' + dependency['package_version'] + '.nupkg'
    with tempfile.TemporaryDirectory(prefix='staticlink-native-smoke-') as tmp:
        artifact = args.artifact_archive or Path(tmp) / 'artifact.zip'
        if args.artifact_archive is None:
            endpoint = ('repos/' + dependency['repository'] + '/actions/artifacts/' +
                        str(dependency['artifact_id']) + '/zip')
            with artifact.open('wb') as stream:
                subprocess.run(['gh', 'api', endpoint], stdout=stream, check=True)
        with zipfile.ZipFile(artifact) as archive:
            payload = archive.read(filename)
        if hashlib.sha256(payload).hexdigest() != dependency['package_sha256']:
            raise SystemExit('Independent Native smoke dependency SHA256 mismatch')
        with zipfile.ZipFile(io.BytesIO(payload)) as package:
            spec = ET.fromstring(package.read(next(name for name in package.namelist()
                                                  if name.endswith('.nuspec'))))
            values = {node.tag.rsplit('}', 1)[-1]: node.text for node in spec.iter()}
            if values.get('id') != 'StaticLink.Avalonia.Native' or values.get('version') != dependency['package_version']:
                raise SystemExit('Unexpected Native package identity')
            for rid in ('osx-x64', 'osx-arm64'):
                if not any(name.endswith('/' + rid + '/native/libAvaloniaNative.a')
                           for name in package.namelist()):
                    raise SystemExit('Native smoke dependency is missing ' + rid)
        args.output.mkdir(parents=True, exist_ok=True)
        target = args.output / filename
        pending = args.output / (filename + '.partial')
        pending.write_bytes(payload)
        pending.replace(target)
        print('Verified independent macOS Native smoke dependency:', target)
        print('Source run:', dependency['run_id'])


if __name__ == '__main__':
    main()
