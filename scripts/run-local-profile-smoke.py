#!/usr/bin/env python3
"""Publish and execute the existing Avalonia smoke app against local stable packages."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--avalonia-version', required=True)
    parser.add_argument('--rid', choices=['linux-x64', 'osx-x64'], required=True)
    parser.add_argument('--lima', default='debian')
    parser.add_argument('--image', required=True)
    parser.add_argument('--repeat', type=int, default=2)
    parser.add_argument('--nuget-source', type=Path, help='An isolated local feed under the repository')
    parser.add_argument('--output-dir', type=Path, help='An isolated smoke result directory under the repository')
    args = parser.parse_args()
    if args.repeat < 1 or '@sha256:' not in args.image:
        parser.error('An immutable image and positive repeat count are required')
    profile = json.loads((ROOT / 'build/avalonia-profiles' / (args.avalonia_version + '.json')).read_text())
    feed = (args.nuget_source or ROOT / 'artifacts/avalonia-packages' / args.avalonia_version).resolve()
    package = feed / ('StaticLink.Avalonia.' + profile['package_version'] + '.nupkg')
    if not package.is_file():
        raise SystemExit('Pack the complete candidate first')
    output = (args.output_dir or ROOT / 'artifacts/local-smoke' / args.avalonia_version / args.rid).resolve()
    if not feed.is_relative_to(ROOT) or not output.is_relative_to(ROOT):
        parser.error('The local feed and smoke results must be under the mounted repository')
    project = output / 'src'
    publish = output / 'publish'
    output.mkdir(parents=True, exist_ok=True)
    subprocess.run(['pwsh', str(ROOT / 'scripts/create-avalonia-smoke.ps1'),
                    '-ProjectDir', str(project), '-NuGetSource', str(feed),
                    '-StaticLinkVersion', profile['package_version'],
                    '-AvaloniaVersion', args.avalonia_version,
                    '-StaticLinkNativeVersion', profile['package_version'] if args.rid.startswith('osx') else ''], check=True)
    config_path = project / 'NuGet.config'
    config = ET.parse(config_path)
    mapping = ET.SubElement(config.getroot(), 'packageSourceMapping')
    local = ET.SubElement(mapping, 'packageSource', key='local-staticlink')
    ET.SubElement(local, 'package', pattern='StaticLink.Avalonia*')
    upstream = ET.SubElement(mapping, 'packageSource', key='nuget.org')
    ET.SubElement(upstream, 'package', pattern='*')
    config.write(config_path, encoding='utf-8', xml_declaration=True)
    guest = ['limactl', 'shell', args.lima, '--']
    command = ['dotnet', 'publish', str(project / 'AvaloniaStaticLinkSmoke.csproj'),
               '-c', 'Release', '-r', args.rid, '--configfile', str(config_path),
               '-p:PublishAot=true', '-p:SelfContained=true', '-p:PublishSingleFile=true',
               '-p:StripSymbols=true', '-p:PublishDir=' + str(publish) + '/']
    environment = dict(os.environ)
    cache = output / 'nuget-cache'
    # A candidate can be repacked at the same local version while fixing it.
    # Force each invocation to restore the selected feed's current packages.
    for directory in (project / 'bin', project / 'obj', publish,
                      cache / 'staticlink.avalonia', cache / 'staticlink.avalonia.native'):
        if directory.exists():
            shutil.rmtree(directory)
    environment['NUGET_PACKAGES'] = str(cache)
    if args.rid == 'linux-x64':
        command = guest + ['podman', 'run', '--rm', '--platform', 'linux/amd64',
                           '-v', str(ROOT) + ':' + str(ROOT), '-w', str(ROOT),
                           '-e', 'NUGET_PACKAGES=' + str(cache), '--entrypoint', 'dotnet', args.image] + command[1:]
    with (output / 'publish.log').open('w') as log:
        result = subprocess.run(command, env=environment, stdout=log, stderr=subprocess.STDOUT)
    if result.returncode:
        print((output / 'publish.log').read_text()[-12000:])
        raise SystemExit(result.returncode)
    blocked = {'libSkiaSharp.so', 'libHarfBuzzSharp.so', 'libSkiaSharp.dylib',
               'libHarfBuzzSharp.dylib', 'libAvaloniaNative.dylib', 'av_libglesv2.dll'}
    if any(path.name in blocked for path in publish.rglob('*')):
        raise SystemExit('Dynamic native library remains in the AOT candidate')
    app = publish / 'AvaloniaStaticLinkSmoke'
    renderers = ['opengl'] if args.rid == 'linux-x64' or args.avalonia_version.startswith('11.') else ['default', 'metal']
    report = {'profile': profile, 'rid': args.rid, 'runs': [], 'passed': False}
    report_path = output / 'runtime-validation.json'
    try:
        for attempt in range(1, args.repeat + 1):
            for renderer in renderers:
                env = dict(environment, STATICLINK_SMOKE_AUTOCLOSE='1', STATICLINK_MAC_RENDERER=renderer)
                run_command = [str(app)]
                if args.rid == 'linux-x64':
                    run_command = guest + ['env', 'STATICLINK_SMOKE_AUTOCLOSE=1',
                                            'STATICLINK_MAC_RENDERER=' + renderer,
                                            'timeout', '60s', 'xvfb-run', '-a', str(app)]
                result = subprocess.run(run_command, env=env, stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT, text=True, timeout=75)
                log = output / f'runtime-{attempt}-{renderer}.log'
                log.write_text(result.stdout)
                markers = re.findall(r'STATICLINK_SMOKE_READY=([^;]+);BACKEND=([^\s]+)', result.stdout)
                passed = result.returncode == 0 and any(r == renderer and (renderer != 'metal' or b == 'Metal') for r, b in markers)
                report['runs'].append({'attempt': attempt, 'renderer': renderer,
                                       'exit_code': result.returncode, 'markers': markers, 'passed': passed})
                print(f'{args.avalonia_version}/{args.rid}/{renderer}/{attempt}: {markers}, exit={result.returncode}', flush=True)
                if not passed:
                    raise RuntimeError('Avalonia did not render and exit normally; see ' + str(log))
        report['passed'] = True
    finally:
        report_path.write_text(json.dumps(report, indent=2) + '\n')
    print('Local runtime validation passed:', report_path)


if __name__ == '__main__':
    main()
