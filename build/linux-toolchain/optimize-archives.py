#!/usr/bin/env python3
"""Remove debug sections and byte-identical ANGLE objects from release archives."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil
import subprocess


def members(path):
    data = path.read_bytes()
    if data[:8] != b'!<arch>\n':
        raise ValueError('Expected a regular archive: ' + str(path))
    at = 8
    while at < len(data):
        if at + 60 > len(data) or data[at + 58:at + 60] != b'`\n':
            raise ValueError('Invalid archive member: ' + str(path))
        name = data[at:at + 16].decode('ascii').strip()
        size = int(data[at + 48:at + 58])
        end = at + 60 + size
        if end > len(data):
            raise ValueError('Truncated archive member: ' + str(path))
        payload = data[at + 60:end]
        special = name in ('/', '/SYM64/', '//') or name.startswith('__.SYMDEF')
        if name.startswith('#1/'):
            length = int(name[3:])
            embedded_name = payload[:length].rstrip(b'\0')
            special = embedded_name.startswith(b'__.SYMDEF')
            payload = payload[length:]
        yield name, payload, data[at:end + size % 2], special
        at = end + size % 2


def optimize(directory, runtime=False):
    strip = shutil.which('llvm-strip-16') or shutil.which('llvm-strip')
    ar = shutil.which('llvm-ar') or shutil.which('llvm-ar-16')
    if not strip or not ar:
        raise RuntimeError('LLVM strip and ar are required')
    archives = sorted(p for p in directory.iterdir() if p.suffix in ('.a', '.lib'))
    before = {p.name: p.stat().st_size for p in archives}
    runtime_names = {'c++.lib', 'c++abi.lib', 'compiler_rt.lib', 'unwind.lib', 'libmingw32.lib', 'libc++.a', 'libc++abi.a', 'libcompiler_rt.a', 'libunwind.a'}
    for path in archives:
        if runtime and path.name not in runtime_names:
            continue  # Windows DLL import members are not strippable objects.
        subprocess.run([strip, '--strip-debug', str(path)], check=True)
    angle = directory / 'libANGLE.a'
    gles = directory / 'libGLESv2.a'
    removed = 0
    if angle.exists() and gles.exists():
        shared = Counter(hashlib.sha256(payload).digest() for _, payload, _, special in members(angle) if not special)
        records = []
        for name, payload, record, special in members(gles):
            if special and name != '//':
                continue  # llvm-ar rebuilds the symbol index for retained objects.
            digest = hashlib.sha256(payload).digest()
            if not special and shared[digest]:
                shared[digest] -= 1
                removed += 1
            else:
                records.append(record)
        if not removed:
            raise RuntimeError('Expected shared ANGLE objects; inspect the new archive layout')
        temporary = gles.with_suffix('.optimized.a')
        temporary.write_bytes(b'!<arch>\n' + b''.join(records))
        subprocess.run([ar, 's', str(temporary)], check=True)
        temporary.replace(gles)
    report = {'before_bytes': before,
              'after_bytes': {p.name: p.stat().st_size for p in archives},
              'gles_duplicate_objects_removed': removed}
    (directory / 'archive-size-report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report), flush=True)
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--directory', type=Path, required=True)
    p.add_argument('--runtime', action='store_true')
    args = p.parse_args()
    optimize(args.directory, args.runtime)
