#!/usr/bin/env python3
"""Verify the exact graphics artifact from a completed runtime-validated daily run."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET
import zipfile

RIDS = ['win-x64', 'win-x86', 'win-arm64', 'linux-x64', 'linux-arm64',
        'linux-musl-x64', 'linux-musl-arm64', 'osx-x64', 'osx-arm64']


def api(path):
    return json.loads(subprocess.check_output(['gh', 'api', path], text=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--branch', choices=('skia3-daily', 'skia4-daily'), required=True)
    parser.add_argument('--package-dir', type=Path)
    args = parser.parse_args()
    if not args.run_id.isdigit():
        raise SystemExit('Expected a numeric source Actions run ID')
    repository = os.environ['GITHUB_REPOSITORY']
    endpoint = f'repos/{repository}/actions/runs/{args.run_id}'
    run = api(endpoint)
    if not (run['status'] == 'completed' and run['conclusion'] == 'success' and
            run['head_branch'] == args.branch and run['event'] == 'workflow_dispatch' and
            run['head_repository']['full_name'] == repository and
            run['path'] == '.github/workflows/nuget-static-graphics.yml'):
        raise SystemExit('Source must be a successful same-repository daily graphics validation')
    jobs = []
    page = 1
    while True:
        batch = api(endpoint + f'/jobs?filter=all&per_page=100&page={page}')['jobs']
        jobs.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    # A partial rerun may retain successful jobs from an older attempt.
    # Select the newest execution of each named job, ignoring obsolete failures.
    latest = {}
    for job in sorted(jobs, key=lambda item: item['id']):
        latest[job['name']] = job
    jobs = list(latest.values())
    required = ['pack', 'Require every Avalonia runtime test']
    required += ['Avalonia 12.1.4 / ' + rid for rid in RIDS]
    for name in required:
        matches = [job for job in jobs if job['name'] == name]
        if len(matches) != 1 or matches[0]['conclusion'] != 'success':
            raise SystemExit('Required source job did not succeed: ' + name)
    metal = [job for job in jobs if job['name'] == 'Avalonia 12.1.4 / Metal']
    if len(metal) != 1 or metal[0]['conclusion'] != 'success':
        raise SystemExit('Source must pass the real Metal validation')
    if args.package_dir is None:
        print('Verified complete runtime validation:', args.run_id, args.branch)
        return
    packages = list(args.package_dir.glob('*.nupkg'))
    if len(packages) != 1:
        raise SystemExit('Expected exactly one graphics NuGet package')
    package = packages[0]
    with zipfile.ZipFile(package) as archive:
        names = set(archive.namelist())
        spec = ET.fromstring(archive.read(next(n for n in names if n.endswith('.nuspec'))))
        values = {node.tag.rsplit('}', 1)[-1]: node.text for node in spec.iter()}
        profile = json.loads(archive.read('buildMetadata/sources.lock.json'))
        version = profile['package_version']
        prefix = profile['skiasharp_version'] + '-' + profile['angle_package_version'] + '.daily.'
        if (profile.get('release_channel') != 'daily' or profile.get('daily_validation_only') or
                profile['avalonia_version'] != '12.1.4' or
                not profile['skiasharp_version'].startswith(args.branch[4] + '.') or
                not re.fullmatch(re.escape(prefix) + str(run['run_number']) + r'\.[1-9]\d*', version) or
                values.get('id') != 'StaticLink.Avalonia' or values.get('version') != version or
                package.name != 'StaticLink.Avalonia.' + version + '.nupkg'):
            raise SystemExit('Candidate does not match the daily publication policy')
        repo = next(node.attrib for node in spec.iter() if node.tag.rsplit('}', 1)[-1] == 'repository')
        if repo.get('commit') != run['head_sha']:
            raise SystemExit('Package repository commit does not match the validated source run')
        dependencies = {node.attrib['id']: node.attrib['version'] for node in spec.iter()
                        if node.tag.rsplit('}', 1)[-1] == 'dependency'}
        expected = {'SkiaSharp': '[' + profile['skiasharp_version'] + ']',
                    'HarfBuzzSharp': '[' + profile['harfbuzzsharp_version'] + ']'}
        if dependencies != expected:
            raise SystemExit('Unexpected managed package dependencies')
        for rid in RIDS:
            manifest = json.loads(archive.read('static/' + rid + '/native/zig-build.json'))
            if manifest['sources'] != profile or not manifest['link_tests'].startswith('passed'):
                raise SystemExit('Native provenance mismatch: ' + rid)
    report = {'source_run': int(args.run_id), 'source_commit': run['head_sha'],
              'package': package.name, 'sha256': hashlib.sha256(package.read_bytes()).hexdigest()}
    (args.package_dir / 'verified-publication.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
