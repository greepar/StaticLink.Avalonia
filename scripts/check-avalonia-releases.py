#!/usr/bin/env python3
"""Select the latest official stable Avalonia release in one supported version line."""
import argparse
import json
from pathlib import Path
import re
import urllib.request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--major', choices=('11', '12'), required=True)
    parser.add_argument('--output', type=Path, default=Path('release-plan.json'))
    args = parser.parse_args()
    with urllib.request.urlopen('https://api.nuget.org/v3-flatcontainer/avalonia/index.json', timeout=30) as response:
        versions = json.load(response)['versions']
    candidates = [version for version in versions if re.fullmatch(re.escape(args.major) + r'\.\d+\.\d+', version)]
    if not candidates:
        raise SystemExit('No stable official Avalonia release for version line ' + args.major)
    version = max(candidates, key=lambda item: tuple(map(int, item.split('.'))))
    plan = {'avalonia_version': version, 'package_version': version + '.1'}
    args.output.write_text(json.dumps(plan, indent=2) + '\n')
    print(json.dumps(plan))


if __name__ == '__main__':
    main()
