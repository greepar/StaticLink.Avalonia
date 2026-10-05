#!/usr/bin/env python3
"""Fetch pinned native cross-build dependencies without cloning Git history."""
import argparse
import ast
import json
import hashlib
from pathlib import Path
import re
import subprocess
import sys

# These dependencies correspond to features explicitly disabled by this recipe.
# Unknown/new dependencies stay enabled; do not infer a skip from their names.
DISABLED = {'dng_sdk', 'icu', 'dawn', 'angle2', 'swiftshader', 'emsdk'}


def evaluate(node, variables):
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Dict):
        return {evaluate(k, variables): evaluate(v, variables) for k, v in zip(node.keys, node.values)}
    if isinstance(node, (ast.List, ast.Tuple)):
        return [evaluate(n, variables) for n in node.elts]
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return evaluate(node.left, variables) + evaluate(node.right, variables)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'Var' and len(node.args) == 1:
        return variables[evaluate(node.args[0], variables)]
    raise ValueError('Unsupported DEPS expression: ' + ast.dump(node))


def dependencies(source):
    values = {}
    for node in ast.parse((source / 'DEPS').read_text()).body:
        if isinstance(node, ast.Assign):
            for name in node.targets:
                if isinstance(name, ast.Name) and name.id in ('vars', 'deps'):
                    values[name.id] = evaluate(node.value, values.get('vars', {}))
    if not values.get('deps'):
        raise ValueError('No dependency map in DEPS')
    return values['deps']


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--cache', type=Path, help='Immutable dependency checkouts shared across version profiles')
    p.add_argument('--no-fetch-gn', action='store_true', help='Use an existing verified GN for a local test')
    a = p.parse_args()
    source = a.source.resolve()
    records = {}
    for relative, value in dependencies(source).items():
        if not isinstance(value, str):
            continue  # GN/Ninja CIPD packages are handled by upstream fetch-gn.
        if Path(relative).name in DISABLED:
            continue
        if '..' in Path(relative).parts:
            raise ValueError('Dependency path escapes source: ' + relative)
        link = source / relative
        path = link.absolute()
        if not path.is_relative_to(source):
            raise ValueError('Dependency path escapes source: ' + relative)
        url, revision = value.rsplit('@', 1)
        if not re.fullmatch(r'[0-9a-f]{40}', revision):
            raise ValueError('Dependency is not commit-pinned: ' + value)
        if a.cache:
            key = hashlib.sha256((url + '@' + revision).encode()).hexdigest()
            cached = a.cache.resolve() / key
            if link.is_symlink():
                link.unlink()
            if not link.exists():
                link.parent.mkdir(parents=True, exist_ok=True)
                link.symlink_to(cached, target_is_directory=True)
                path = cached
        if not (path / '.git').exists():
            subprocess.run(['git', 'init', '-q', str(path)], check=True)
            subprocess.run(['git', '-C', str(path), 'remote', 'add', 'origin', url], check=True)
        current = subprocess.run(['git', '-C', str(path), 'rev-parse', 'HEAD'], capture_output=True, text=True)
        if current.stdout.strip() != revision:
            subprocess.run(['git', '-C', str(path), 'remote', 'set-url', 'origin', url], check=True)
            subprocess.run(['git', '-C', str(path), 'fetch', '--depth=1', 'origin', revision], check=True)
            subprocess.run(['git', '-C', str(path), 'checkout', '--detach', revision], check=True)
        records[relative] = revision
    if not a.no_fetch_gn:
        subprocess.run([sys.executable, str(source / 'bin/fetch-gn')], cwd=source, check=True)
    (source / 'native-cross-deps.json').write_text(json.dumps(records, indent=2) + '\n')


if __name__ == '__main__':
    main()
