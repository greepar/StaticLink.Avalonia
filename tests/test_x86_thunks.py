"""Exercise binding discovery and x86 stack sizes without native dependencies."""
import json
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'build/linux-toolchain/x86-thunks.py'


class ThunksTests(unittest.TestCase):
    def generate(self, source):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            libraries = root / 'libraries'
            libraries.mkdir()
            (libraries / 'libskia.a').touch()
            real_run = subprocess.run

            def run(command, **kwargs):
                if command[0] == 'nm':
                    return subprocess.CompletedProcess(
                        command, 0, '0000 T _sk_color\n0000 T _hb_test\n', '')
                if Path(command[0]).name in ('cc', 'ar'):
                    return subprocess.CompletedProcess(command, 0)
                return real_run(command, **kwargs)

            argv = [str(SCRIPT), '--source', str(source), '--libraries', str(libraries), '--toolchain', str(root)]
            with patch.object(sys, 'argv', argv), patch('subprocess.run', side_effect=run):
                runpy.run_path(str(SCRIPT), run_name='__main__')
            report = json.loads((libraries / 'x86-thunks.json').read_text())
            self.assertEqual(report['layouts']['Color'], 16)
            self.assertEqual(report['thunks']['_sk_color@20'], ['_sk_color', 20])
            self.assertEqual(report['thunks']['_hb_test@8'], ['_hb_test', 8])
            self.assertIn('retl $20', (libraries / 'skia_x86_stdcall_thunks.s').read_text())

    def check_format(self, split):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            subprocess.run(['git', 'init', '-q', directory], check=True)
            struct = ('public readonly partial struct Color : IEquatable<Color> {\n'
                      'private readonly Single r;\nprivate readonly Single g;\n'
                      'private readonly Single b;\nprivate readonly Single a;\n'
                      'public Single Red => r;\n}\n') if split else (
                      'public struct Color {\npublic Single r;\npublic Single g;\n'
                      'public Single b;\npublic Single a;\n}\n')
            for component, api in [('Skia', 'internal static extern void sk_color (IntPtr canvas, Color color);'),
                                   ('HarfBuzz', 'internal static partial void hb_test (UInt64 value);')]:
                root = source / 'binding' / (component + 'Sharp')
                root.mkdir(parents=True)
                if split:
                    root = root / 'Generated'
                    root.mkdir()
                    (root / (component + 'Api_header.generated.cs')).write_text(api)
                    if component == 'Skia':
                        (root / 'Color.generated.cs').write_text(struct)
                else:
                    (root / (component + 'Api.generated.cs')).write_text(api + '\n' + (struct if component == 'Skia' else ''))
            subprocess.run(['git', '-C', directory, 'add', '.'], check=True)
            subprocess.run(['git', '-C', directory, '-c', 'user.name=Test', '-c', 'user.email=test@example.com',
                            'commit', '-qm', 'bindings'], check=True)
            self.generate(source)

    def test_legacy(self):
        self.check_format(False)

    def test_split(self):
        self.check_format(True)


if __name__ == '__main__':
    unittest.main()
