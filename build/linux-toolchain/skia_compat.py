"""Discover Skia GN capabilities; keep version policy out of the build driver."""
import json
from pathlib import Path
import re
import subprocess


def repair_xps(source):
    path = source / 'src/xps/SkXPSDevice.cpp'
    header = source / 'src/xps/SkXPSDevice.h'
    if not path.exists() or not header.exists():
        return 'absent'
    text = path.read_text()
    if not re.search(r'friend\s+HRESULT\s+subset_typeface\s*\(', header.read_text()):
        return 'not-needed'
    text, count = re.subn(r'(?m)^static HRESULT (subset_typeface\s*\()', r'HRESULT \1', text)
    if count > 1:
        raise RuntimeError('Ambiguous XPS helper declarations; inspect the new source layout')
    if count:
        path.write_text(text)
    return 'repaired' if count else 'already-compatible'


def repair_skcms(source):
    repaired = []
    for relative in ('third_party/skcms/skcms.cc', 'modules/skcms/skcms.cc'):
        path = source / relative
        if not path.is_file():
            continue
        text = path.read_text()
        def replace(match):
            features = match[2]
            if 'avx512f' in features.split(',') and 'evex512' not in features.split(','):
                return match[1] + features + ',evex512' + match[3]
            return match[0]
        updated = re.sub(r'(#pragma clang attribute push\(__attribute__\(\(target\(")([^"]+)("\)\)\))', replace, text)
        if updated != text:
            path.write_text(updated)
            repaired.append(relative)
    # This changes only the AVX512-dispatched functions' Clang target attribute;
    # the baseline CPU path and runtime dispatch remain unchanged.
    return repaired


def configure(source, out, desired, gn, env):
    # GN itself resolves imports, defaults and conditional declarations. Text
    # searches alone can incorrectly report an option from an inactive branch.
    # Apply the feature policy during discovery too: Skia's default tools build
    # can otherwise demand test-only dependencies before we can list options.
    bootstrap = dict(desired)
    out.mkdir(parents=True, exist_ok=True)
    def write(values):
        (out / 'args.gn').write_text(''.join(f'{key} = {value}\n' for key, value in values.items()))
    write(bootstrap)
    subprocess.run([str(gn), 'gen', str(out.relative_to(source))],
                   cwd=source, env=env, check=True)
    command = [str(gn), 'args', str(out.relative_to(source)), '--list', '--json']
    result = subprocess.run(command, cwd=source, env=env, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError('Cannot discover Skia build arguments:\n' + result.stdout + result.stderr)
    # Older GN emits warnings before the JSON array for unsupported bootstrap args.
    match = re.search(r'(?m)^\[\s*\{', result.stdout)
    if not match:
        raise RuntimeError('GN did not return an argument list:\n' + result.stdout)
    arguments = json.loads(result.stdout[match.start():])
    available = {entry['name'] for entry in arguments}
    values = {key: value for key, value in desired.items() if key in available}
    if 'skia_enable_ganesh' in available:
        values['skia_enable_ganesh'] = 'true'
    elif 'skia_enable_gpu' in available:
        values['skia_enable_gpu'] = 'true'
    else:
        raise RuntimeError('No known Skia GPU switch; refusing to silently change the graphics feature set')
    required = {'target_os', 'target_cpu', 'is_static_skiasharp', 'extra_cflags', 'extra_cflags_cc'}
    required |= {key for key in ('skia_use_metal', 'skia_use_xps') if desired.get(key) == 'true'}
    if desired.get('third_party_isystem') == 'false':
        required.add('third_party_isystem')
    missing = required - available
    if missing:
        raise RuntimeError('Skia source lacks required build capabilities: ' + ', '.join(sorted(missing)))
    write(values)
    subprocess.run([str(gn), 'gen', str(out.relative_to(source)), '--fail-on-unused-args'],
                   cwd=source, env=env, check=True)
    report = {'available_arguments': sorted(available), 'selected_arguments': values,
              'omitted_obsolete_arguments': sorted(set(desired) - available)}
    (out / 'skia-capabilities.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def parse_args(text):
    # Values can include multiline lists, as used by the native Linux recipe.
    assignments = list(re.finditer(r'(?m)^[ \t]*([A-Za-z_]\w*)[ \t]*=', text))
    if not assignments:
        raise ValueError('No GN assignments in build recipe')
    return {match[1]: text[match.end():assignments[index + 1].start()
            if index + 1 < len(assignments) else len(text)].strip()
            for index, match in enumerate(assignments)}


def archive(source, name):
    candidates = [source / (name + '.lib'), source / ('lib' + name + '.a'),
                  source / 'obj' / (name + '.lib'), source / 'obj' / ('lib' + name + '.a')]
    matches = [path for path in candidates if path.is_file()]
    if len(matches) != 1:
        raise RuntimeError(f'Expected one archive for {name}; found {matches}')
    return matches[0]


if __name__ == '__main__':
    import argparse
    import os
    p = argparse.ArgumentParser(description='Configure native or cross Skia using its actual GN capabilities')
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    source, out = a.source.resolve(), a.out.resolve()
    gn = source / ('bin/gn.exe' if os.name == 'nt' else 'bin/gn')
    repair_xps(source)
    desired = parse_args((out / 'args.gn').read_text())
    compiler = desired.get('cc', 'clang-cl' if os.name == 'nt' else 'clang').strip('"')
    version = subprocess.run([compiler, '--version'], capture_output=True, text=True, check=True)
    match = re.search(r'clang version (\d+)', version.stdout)
    if match and int(match[1]) >= 19:
        repair_skcms(source)
    configure(source, out, desired, gn, os.environ.copy())
