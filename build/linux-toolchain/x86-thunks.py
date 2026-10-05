#!/usr/bin/env python3
"""Generate cdecl -> stdcall adapters using the pinned managed P/Invoke ABI."""
import argparse,re,subprocess,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--toolchain',type=Path,required=True);p.add_argument('--libraries',type=Path,required=True);a=p.parse_args()
files=[a.source/'binding/SkiaSharp/SkiaApi.generated.cs',a.source/'binding/HarfBuzzSharp/HarfBuzzApi.generated.cs']
text='\n'.join(x.read_text() if x.is_file() else subprocess.check_output(['git','-C',str(a.source),'show','HEAD:'+str(x.relative_to(a.source))],text=True) for x in files)
structs={}
# Generated structs use public fields; omit properties and methods.
for match in re.finditer(r'\bstruct\s+(\w+)\s*\{',text):
 pos=match.end();depth=1;end=pos
 while depth:
  if text[end]=='{':depth+=1
  if text[end]=='}':depth-=1
  end+=1
 block=text[pos:end-1]
 structs[match[1]]=[m[1].strip() for m in re.finditer(r'^\s*public\s+(.+?)\s+\w+;\s*$',block,re.M)]
sizes={}
def layout(t):
 t=re.sub(r'\b(?:ref|out|in|readonly)\b','',t).strip()
 if '*' in t or t.endswith(('[]','Delegate')):return 4,4
 if t in sizes:return sizes[t],4
 if t in structs:raise KeyError(t)
 if t in ['Int64','UInt64','long','ulong','Double','double']:return 8,4
 if t in ['Int16','UInt16','short','ushort']:return 2,2
 if t in ['Byte','SByte','byte','sbyte','Boolean','bool']:return 1,1
 return 4,4  # enums and generated opaque pointer aliases
pending=set(structs)
while pending:
 done=set()
 for name in sorted(pending):
  offset=0;align=1
  try:
   for t in structs[name]:
    n,k=layout(t);offset=(offset+k-1)//k*k+n;align=max(align,k)
  except KeyError:continue
  sizes[name]=(offset+align-1)//align*align;done.add(name)
 if not done:raise SystemExit('Unresolved managed struct layout: '+str(pending))
 pending-=done
symbols=set()
for path in a.libraries.glob('lib*.a'):
 result=subprocess.run(['nm','--defined-only',str(path)],capture_output=True,text=True,check=True)
 symbols.update(re.findall(r'\bT\s+(_(?:sk|gr|hb)_\w+)\s*$',result.stdout,re.M))
thunks={}
def parameters(s):
 result=[];depth=0;start=0
 for i,c in enumerate(s):
  if c in '[<(':depth+=1
  elif c in ']> )'.replace(' ',''):depth-=1
  elif c==',' and depth==0:result.append(s[start:i]);start=i+1
 result.append(s[start:]);return [v.strip() for v in result if v.strip()]
for m in re.finditer(r'internal static (?:extern|partial)\s+.+?\s+((?:sk|gr|hb)_\w+)\s*\((.*?)\);',text,re.S):
 symbol='_'+m[1]
 if symbol not in symbols:continue
 count=0
 for param in parameters(m[2]):
  param=re.sub(r'/\*.*?\*/|\[[^\]]+\]','',param).strip();typ=param.rsplit(' ',1)[0]
  n,_=layout(typ);count+=(n+3)//4*4
 thunks[symbol+'@'+str(count)]=(symbol,count)
if not thunks:raise SystemExit('No x86 exported APIs matched pinned managed bindings')
assembly=['.text','.set "@feat.00", 1']
for name,(symbol,count) in sorted(thunks.items()):
 assembly+=['.globl "'+name+'"','"'+name+'":']+['pushl '+str(count)+'(%esp)']*(count//4)
 assembly+=['calll '+symbol,'addl $'+str(count)+', %esp','retl $'+str(count)]
path=a.libraries/'skia_x86_stdcall_thunks.s';path.write_text('\n'.join(assembly)+'\n');obj=path.with_suffix('.o')
subprocess.run([str(a.toolchain/'cc'),'-c',str(path),'-o',str(obj)],check=True)
subprocess.run([str(a.toolchain/'ar'),'rcs',str(a.libraries/'skia_x86_stdcall_thunks.lib'),str(obj)],check=True)
(a.libraries/'x86-thunks.json').write_text(json.dumps({'count':len(thunks),'layouts':sizes,'thunks':thunks},indent=2)+'\n')
print('Generated',len(thunks),'x86 stdcall thunks')
