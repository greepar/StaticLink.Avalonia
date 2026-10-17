#!/usr/bin/env python3
"""Dispatch a daily build only for an upstream SkiaSharp version not yet published."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

FEED = 'https://api.nuget.org/v3-flatcontainer'


def request(url, missing_ok=False):
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            return response.read()
    except urllib.error.HTTPError as error:
        if missing_ok and error.code == 404:
            return None
        raise


def published_package(version):
    payload = request(FEED + '/staticlink.avalonia/index.json', missing_ok=True)
    versions = json.loads(payload)['versions'] if payload is not None else []
    # A stable package also satisfies this check: rebuilding the same upstream
    # as a preview is unnecessary when its stable StaticLink package exists.
    pattern = re.compile(re.escape(version) + r'(?:\.[1-9]\d*)?(?:-[0-9A-Za-z.-]+)?')
    for candidate in reversed(versions):
        if not pattern.fullmatch(candidate):
            continue
        spec = ET.fromstring(request(f'{FEED}/staticlink.avalonia/{candidate}/staticlink.avalonia.nuspec'))
        for node in spec.iter():
            if (node.tag.rsplit('}', 1)[-1] == 'dependency' and
                    node.attrib.get('id', '').lower() == 'skiasharp' and
                    node.attrib.get('version') in (version, '[' + version + ']')):
                return candidate
    return None


def gh_json(endpoint):
    return json.loads(subprocess.check_output(['gh', 'api', endpoint], text=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--branch', choices=('skia3-daily', 'skia4-daily'), required=True)
    parser.add_argument('--publish-to-nuget', choices=('true', 'false'), default='false')
    parser.add_argument('--repository', default=os.environ.get('GITHUB_REPOSITORY', 'greepar/StaticLink.Avalonia'))
    parser.add_argument('--output', type=Path, default=Path('daily-plan.json'))
    parser.add_argument('--check-only', action='store_true', help='Resolve the decision without dispatching a build')
    args = parser.parse_args()
    major = int(args.branch[4])
    versions = json.loads(request(FEED + '/skiasharp/index.json'))['versions']
    releases = [v for v in versions if re.fullmatch(str(major) + r'\.\d+\.\d+', v)]
    if not releases:
        raise SystemExit('No stable upstream SkiaSharp release in this major line')
    version = max(releases, key=lambda v: tuple(map(int, v.split('.'))))
    existing = published_package(version)
    plan = {'branch': args.branch, 'skiasharp_version': version,
            'published_package': existing, 'publish_to_nuget': args.publish_to_nuget == 'true'}
    if existing:
        plan.update(action='skip', reason='This SkiaSharp version already has a published StaticLink package')
    else:
        runs = gh_json(f'repos/{args.repository}/actions/workflows/nuget-static-graphics.yml/runs?branch={args.branch}&per_page=100')['workflow_runs']
        active = [run['id'] for run in runs if run['status'] != 'completed']
        if active:
            plan.update(action='skip', reason='A build for this branch is already active', active_run_ids=active)
        else:
            plan.update(action='dispatch', reason='New upstream version has no published StaticLink package')
            if not args.check_only:
                payload = {'ref': args.branch, 'inputs': {
                    'avalonia_version': '12.1.4', 'skiasharp_version': version,
                    'publish_to_nuget': plan['publish_to_nuget'], 'publish_to_release': False}}
                subprocess.run(['gh', 'api', '--method', 'POST',
                                f'repos/{args.repository}/actions/workflows/nuget-static-graphics.yml/dispatches',
                                '--input', '-'], input=json.dumps(payload), text=True, check=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(plan, indent=2) + '\n')
    print(json.dumps(plan, indent=2))
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as output:
            output.write(f"{args.branch}: {version} — {plan['action']}: {plan['reason']}.\n")


if __name__ == '__main__':
    main()
