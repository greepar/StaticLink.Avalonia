#!/usr/bin/env python3
"""Reject the known Win8 direct imports behind the Win7 startup regression.

This is a narrow regression guard, not a complete Windows API compatibility
database. A rendered-frame test on Windows 7 is still required.
"""
import argparse
from pathlib import Path
import re
import shutil
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('executables', nargs='+', type=Path)
    parser.add_argument('--objdump', default=shutil.which('llvm-objdump') or shutil.which('objdump'))
    args = parser.parse_args()
    if not args.objdump:
        parser.error('Install LLVM objdump or specify --objdump')
    blocked = {'GetSystemTimePreciseAsFileTime', 'WaitOnAddress', 'WakeByAddressSingle', 'WakeByAddressAll'}
    failed = False
    for path in args.executables:
        output = subprocess.check_output([args.objdump, '-p', str(path)], text=True)
        imports = set(re.findall(r'^\s+\d+\s+(\w+)\s*$', output, re.MULTILINE))
        if 'DLL Name:' not in output or not imports:
            raise SystemExit('Could not read PE imports: ' + str(path))
        found = sorted(imports & blocked)
        failed |= bool(found)
        print(str(path) + ': ' + ('FAIL: ' + ', '.join(found) if found else 'PASS: no known Win8 regression imports'))
    raise SystemExit(1 if failed else 0)


if __name__ == '__main__':
    main()
