#!/usr/bin/env python3
"""Build the entire official native matrix, pack locally, then run Avalonia twice."""
import argparse
import datetime
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profiles', nargs='+', default=['11.3.22', '12.1.4'])
    parser.add_argument('--image', required=True)
    parser.add_argument('--lima', default='debian')
    parser.add_argument('--work-dir', default='/var/tmp/staticlink-avalonia-work')
    parser.add_argument('--jobs', type=int, default=12)
    parser.add_argument('--repeat', type=int, default=2)
    args = parser.parse_args()
    if '@sha256:' not in args.image or args.jobs < 1 or args.repeat < 2:
        parser.error('Use an immutable image, positive jobs, and at least two runtime attempts')
    for version in args.profiles:
        profile = ROOT / 'build/avalonia-profiles' / (version + '.json')
        if not profile.is_file() or json.loads(profile.read_text())['avalonia_version'] != version:
            parser.error('Missing or inconsistent official version profile: ' + version)
    output = ROOT / 'artifacts/local-profile-validation'
    output.mkdir(parents=True, exist_ok=True)
    report_path = output / 'pipeline.json'
    report = {'profiles': args.profiles, 'image': args.image, 'stages': [], 'passed': False}

    def save():
        report['updated_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        temporary = report_path.with_suffix('.tmp')
        temporary.write_text(json.dumps(report, indent=2) + '\n')
        temporary.replace(report_path)

    def run(stage, command):
        print('Running:', stage, flush=True)
        entry = {'name': stage, 'status': 'running'}
        report['stages'].append(entry)
        save()
        with (output / (stage + '.log')).open('w') as log:
            result = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        entry.update(exit_code=result.returncode, status='passed' if result.returncode == 0 else 'failed')
        save()
        if result.returncode:
            raise SystemExit('Validation stopped at ' + stage + '; see ' + str(output / (stage + '.log')))

    guest = ['limactl', 'shell', args.lima, '--']
    run('native-matrix', guest + ['python3', str(ROOT / 'scripts/validate-container-matrix.py'),
                                 '--engine', 'podman', '--profiles', *args.profiles,
                                 '--image', args.image, '--work-dir', args.work_dir,
                                 '--cache-size', '2G', '--output-dir', str(ROOT / 'artifacts/avalonia-validation'),
                                 '--jobs', str(args.jobs)])
    for version in args.profiles:
        run('avalonia-native-' + version, guest + ['podman', 'run', '--rm', '--platform', 'linux/amd64',
            '-v', str(ROOT) + ':/src', '-v', args.work_dir + ':/src/External/NativeStatic/.work', '-w', '/src',
            '-e', 'AVALONIA_PROFILE=/src/build/avalonia-profiles/' + version + '.json',
            '-e', 'ZIG_GLOBAL_CACHE_DIR=/src/External/NativeStatic/.work/zig-global',
            '-e', 'GIT_CONFIG_COUNT=1', '-e', 'GIT_CONFIG_KEY_0=safe.directory', '-e', 'GIT_CONFIG_VALUE_0=*',
            '--entrypoint', 'bash', args.image, 'scripts/build-avalonia-profile-native.sh'])
        run('pack-' + version, [sys.executable, str(ROOT / 'scripts/pack-avalonia-profile.py'),
                                '--avalonia-version', version])
        for rid in ('osx-x64', 'linux-x64'):
            run('runtime-' + version + '-' + rid,
                [sys.executable, str(ROOT / 'scripts/run-local-profile-smoke.py'),
                 '--avalonia-version', version, '--rid', rid, '--image', args.image,
                 '--lima', args.lima, '--repeat', str(args.repeat)])
    report['passed'] = True
    # This is a local verification report. Windows, macOS ARM64, and other Linux
    # runtime targets still require their existing CI runners before publication.
    report['all_target_runtime_validation_complete'] = False
    save()
    print('Local build, package, and runtime validation passed:', report_path)


if __name__ == '__main__':
    main()
