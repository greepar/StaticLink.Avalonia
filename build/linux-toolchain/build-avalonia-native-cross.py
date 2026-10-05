#!/usr/bin/env python3
"""Build Avalonia's pinned macOS native sources with Zig on Linux."""
import argparse,subprocess,re,json,os,hashlib
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--rid',choices=['osx-x64','osx-arm64'],required=True);p.add_argument('--sdk',type=Path,required=True);p.add_argument('--zig',default='zig');p.add_argument('--output',type=Path,required=True);p.add_argument('--work',type=Path,required=True);a=p.parse_args()
a.source=a.source.resolve();a.output=a.output.resolve();a.work=a.work.resolve();a.output.mkdir(parents=True,exist_ok=True);a.work.mkdir(parents=True,exist_ok=True)
repo=Path(__file__).resolve().parents[2]
tools=a.work/'tools'
subprocess.run(['python3',str(repo/'build/linux-toolchain/zig-cross.py'),'--zig',a.zig,'--target',a.rid,'--sdk',str(a.sdk),'--output',str(tools)],check=True)
descriptor=tools/'toolchain.json'
config=json.loads(descriptor.read_text());config['target']=config['target'].split('-macos.')[0]+'-macos.12.0.0';descriptor.write_text(json.dumps(config,indent=2)+'\n')
native=a.source/'native/Avalonia.Native';project=native/'src/OSX/Avalonia.Native.OSX.xcodeproj/project.pbxproj'
headers=native/'inc'
if not (headers/'avalonia-native.h').is_file():
 header_project=native/'Avalonia.Native.macOS.proj'
 if header_project.is_file():
  subprocess.run(['dotnet','build',str(header_project),'-t:GenerateMicroComItems'],cwd=a.source,check=True)
 else:
  subprocess.run(['bash',str(native/'generate-headers.sh')],cwd=a.source,check=True)
# Match the authoritative Xcode Sources build phases, rather than guessing every .mm in the repo.
project_text=project.read_text()
names=set(re.findall(r'/\* (.+?\.(?:mm|m|cpp|cc|c)) in Sources \*/',project_text))
file_flags={}
for name,flags in re.findall(r'/\* (.+?\.(?:mm|m|cpp|cc|c)) in Sources \*/[^\n]*COMPILER_FLAGS = \"([^\"]+)\"',project_text):
 import shlex
 file_flags[name]=shlex.split(flags)
if not names:raise SystemExit('No authoritative Xcode source list found')
objects=[];source_hashes={}
for name in sorted(names):
 matches=list(native.rglob(name))
 if len(matches)!=1:raise SystemExit('Ambiguous or missing Xcode source '+name+': '+str(matches))
 source=matches[0];obj=a.work/(hashlib.sha256(str(source.relative_to(native)).encode()).hexdigest()+'.o')
 command=[str(tools/('cc' if source.suffix in ('.c','.m') else 'cxx')),'-O2','-fPIC','-fblocks','-mmacosx-version-min=12.0','-I'+str(headers),'-I'+str(native/'src/OSX'),'-I'+str(native/'src'),'-c',str(source),'-o',str(obj)]
 if source.suffix in ('.mm','.m'):command+=['-fobjc-arc']
 if source.suffix in ('.mm','.cpp','.cc'):command+=['-std=c++17']
 command+=file_flags.get(name,[])
 subprocess.run(command,check=True);objects.append(obj);source_hashes[str(source.relative_to(native))]=hashlib.sha256(source.read_bytes()).hexdigest()
subprocess.run([str(tools/'ar'),'rcs',str(a.output/'libAvaloniaNative.a'),*map(str,objects)],check=True)
# The macOS font pre-initializer is compiled by the same cross compiler.
env=dict(os.environ,RID=a.rid,OUTPUT_DIR=str(a.output),CC=str(tools/'cc'),STATICLINK_ZIG_CROSS='1')
subprocess.run(['bash',str(repo/'scripts/build-macos-font-preinit.sh')],env=env,check=True)
commit=subprocess.check_output(['git','-C',str(a.source),'rev-parse','HEAD'],text=True).strip()
(a.output/'avalonia-native-build.json').write_text(json.dumps({'source_commit':commit,'rid':a.rid,'toolchain':json.loads((tools/'toolchain.json').read_text()),'sources':source_hashes,'validation':'compiled archive; macOS AOT/runtime validation runs separately'},indent=2)+'\n')
