#!/usr/bin/env python3
"""Run the CI native build and executable-link gates in one immutable Docker image."""
import argparse
import datetime
import hashlib
import json
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parent.parent
RIDS = ['osx-arm64', 'osx-x64', 'linux-x64', 'linux-arm64', 'linux-musl-x64',
        'linux-musl-arm64', 'win-x64', 'win-x86', 'win-arm64']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', required=True, help='Same ghcr.io/...@sha256:... reference as CI')
    parser.add_argument('--versions', nargs='+', default=['3.119.4', '4.153.1', '3.119.1', '3.119.2', '4.152.3', '4.153.0'])
    parser.add_argument('--rids', nargs='+', choices=RIDS, default=RIDS)
    parser.add_argument('--jobs', type=int, default=4)
    parser.add_argument('--proxy', default='', help='Optional host network proxy URL, e.g. http://host.docker.internal:7897')
    parser.add_argument('--volume', default='staticlink-container-validation-work')
    args = parser.parse_args()
    if '@sha256:' not in args.image or args.jobs < 1:
        parser.error('An immutable image digest and positive job count are required')
    for version in args.versions:
        profile = ROOT / 'build/linux-toolchain/versions' / (version + '.json')
        if not profile.is_file() or json.loads(profile.read_text())['skiasharp_version'] != version:
            parser.error('Missing or inconsistent version lock: ' + version)
    output = ROOT / 'artifacts/container-validation'
    output.mkdir(parents=True, exist_ok=True)
    report_path = output / 'matrix.json'
    report = json.loads(report_path.read_text()) if report_path.exists() else {}
    if report and report['image'] != args.image:
        parser.error('Existing report belongs to another image; move it before changing the image')
    recipe = hashlib.sha256()
    inputs = list((ROOT / 'build/linux-toolchain').rglob('*')) + list((ROOT / 'scripts').glob('*.sh'))
    for path in sorted(inputs):
        if path.is_file() and path.suffix in ('.py', '.sh', '.in', '.patch', '.json', '.c'):
            recipe.update(str(path.relative_to(ROOT)).encode())
            recipe.update(path.read_bytes())
    recipe_hash = recipe.hexdigest()
    if report.get('recipe_sha256') != recipe_hash:
        report['builds'] = {}
    report['recipe_sha256'] = recipe_hash
    report.update(image=args.image, versions=args.versions, rids=args.rids, runtime_validated=False)
    report.setdefault('builds', {})
    def save():
        report['updated_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        temporary = report_path.with_suffix('.tmp')
        temporary.write_text(json.dumps(report, indent=2) + '\n')
        temporary.replace(report_path)
    common_git = pathlib.Path(subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', '--git-common-dir'], text=True).strip())
    if not common_git.is_absolute():
        common_git = (ROOT / common_git).resolve()
    docker = ['docker', 'run', '--rm', '--platform', 'linux/amd64',
              '-v', str(ROOT) + ':/src', '-v', str(common_git) + ':' + str(common_git) + ':ro', '-v', args.volume + ':/src/External/NativeStatic/.work',
              '-w', '/src', '-e', 'DEPOT_TOOLS_METRICS=0', '-e', 'HOME=/src/External/NativeStatic/.work/home',
              '-e', 'CCACHE_DIR=/src/External/NativeStatic/.work/ccache', '-e', 'CCACHE_MAXSIZE=20G',
              '-e', 'CCACHE_BASEDIR=/src/External/NativeStatic/.work', '-e', 'CCACHE_COMPILERCHECK=content',
              '-e', 'ZIG_GLOBAL_CACHE_DIR=/src/External/NativeStatic/.work/zig-global',
              '--entrypoint', 'bash', args.image, '-c']
    if args.proxy:
        docker[2:2] = ['-e', 'HTTP_PROXY=' + args.proxy, '-e', 'HTTPS_PROXY=' + args.proxy, '-e', 'http_proxy=' + args.proxy, '-e', 'https_proxy=' + args.proxy]
    with (output / 'environment.log').open('w') as log:
        code = subprocess.call(docker + ['mkdir -p "$HOME"; python3 /src/build/linux-toolchain/validate-toolchain.py --output /src/artifacts/container-validation/environment'], stdout=log, stderr=subprocess.STDOUT)
    report['environment_exit_code'] = code
    save()
    if code:
        raise SystemExit(code)
    for version in args.versions:
        print('Preparing locked sources:', version, flush=True)
        with (output / (version + '-sources.log')).open('a') as log:
            command = 'export SOURCE_LOCK="/src/build/linux-toolchain/versions/$1.json"; source scripts/prepare-cross-sources.sh'
            code = subprocess.call(docker + [command, 'prepare', version], stdout=log, stderr=subprocess.STDOUT)
        report['builds'][version + '/sources'] = {'exit_code': code, 'status': 'passed' if code == 0 else 'failed'}
        save()
        if code:
            continue
        for rid in args.rids:
            key = version + '/' + rid
            if report['builds'].get(key, {}).get('exit_code') == 0:
                print('Already passed:', key, flush=True)
                continue
            print('Building:', key, flush=True)
            report['builds'][key] = {'status': 'running'}
            save()
            command = '''set -euo pipefail
export SOURCE_LOCK="/src/build/linux-toolchain/versions/$1.json"
work="/src/External/NativeStatic/.work/zig-sources/$1-$(sha256sum "$SOURCE_LOCK" | cut -c1-16)"
output="/src/artifacts/container-validation/$1/$2"
python3 build/linux-toolchain/build-cross.py --target "$2" --sources-manifest "$work/cross-sources.json" --work /src/External/NativeStatic/.work/toolchains --output "$output/build" --jobs "$3"
python3 build/linux-toolchain/package-zig.py --rid "$2" --input "$output/build" --output "$output/native"
'''
            with (output / (version + '-' + rid + '.log')).open('a') as log:
                code = subprocess.call(docker + [command, 'build', version, rid, str(args.jobs)], stdout=log, stderr=subprocess.STDOUT)
            report['builds'][key] = {'exit_code': code, 'status': 'passed' if code == 0 else 'failed'}
            save()
            print(key, report['builds'][key]['status'], flush=True)
    raise SystemExit(0 if all(report['builds'].get(v + '/' + r, {}).get('exit_code') == 0 for v in args.versions for r in args.rids) else 1)


if __name__ == '__main__':
    main()
