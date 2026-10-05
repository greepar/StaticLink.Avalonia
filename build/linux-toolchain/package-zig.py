#!/usr/bin/env python3
"""Export verified Zig archives in the layout consumed by the NuGet package."""
import argparse,json,shutil,hashlib
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--rid',required=True)
a=p.parse_args();manifest=json.loads((a.input/'cross-build.json').read_text())
if manifest['target']!=a.rid or not manifest.get('link_tests','').startswith('passed'):
 raise SystemExit('Only successfully linked target archives may be packaged')
names={'libskia.a':'skia.lib','libSkiaSharp.a':'SkiaSharp.lib','libHarfBuzzSharp.a':'libHarfBuzzSharp.lib','libANGLE.a':'libANGLE_static.lib','libGLESv2.a':'libGLESv2_static.lib','libEGL.a':'libEGL_static.lib'} if a.rid.startswith('win') else {'libskia.a':'libskia.a','libSkiaSharp.a':'libSkiaSharp.a','libHarfBuzzSharp.a':'libHarfBuzzSharp.a','libANGLE.a':'libANGLE_static.a','libGLESv2.a':'libGLESv2_static.a','libEGL.a':'libEGL_static.a'}
a.output.mkdir(parents=True,exist_ok=True)
for source,destination in names.items():
 path=a.input/source
 if hashlib.sha256(path.read_bytes()).hexdigest()!=manifest['archives'][source]:raise SystemExit('Archive checksum mismatch: '+source)
 shutil.copy2(path,a.output/destination)
runtime=a.input/'zig-runtime'
if not runtime.is_dir() or not [p for p in runtime.iterdir() if p.suffix in ('.a','.lib')]:raise SystemExit('Zig C++/compiler runtime archives were not captured')
(a.output/'zig-runtime').mkdir(exist_ok=True)
for path in runtime.iterdir():
 if path.suffix not in ('.a','.lib'):continue
 dest=path.stem+'.lib' if a.rid.startswith('win') else path.name
 shutil.copy2(path,a.output/'zig-runtime'/dest)
if a.rid=='win-x86':
 path=a.input/'skia_x86_stdcall_thunks.lib'
 if not path.is_file():raise SystemExit('x86 stdcall thunks are required')
 shutil.copy2(path,a.output/path.name)
shutil.copy2(a.input/'cross-build.json',a.output/'zig-build.json')
print('Packaged',a.rid)
