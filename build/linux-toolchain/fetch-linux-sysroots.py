#!/usr/bin/env python3
"""Materialize target SDK libraries from immutable, checksum-locked packages."""
import argparse,json,hashlib,urllib.request,tarfile,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--locks',type=Path,nargs='+',required=True);a=p.parse_args()
for lock in a.locks:
 for rid,packages in json.loads(lock.read_text()).items():
  dest=a.output/rid;dest.mkdir(parents=True,exist_ok=True)
  for package in packages:
   with urllib.request.urlopen(package['url'],timeout=90) as response:data=response.read()
   if hashlib.sha256(data).hexdigest()!=package['sha256']:raise SystemExit('SDK checksum mismatch: '+package['name'])
   path=a.output/(rid+'-'+Path(package['url']).name);path.write_bytes(data)
   if path.suffix=='.deb':subprocess.run(['dpkg-deb','--extract',str(path),str(dest)],check=True)
   else:
    with tarfile.open(path,mode='r:gz',ignore_zeros=True) as tar:
     members=[m for m in tar.getmembers() if m.name.startswith(('lib/','usr/lib/','usr/include/','etc/fonts/'))]
     for m in members:
      if m.issym() and m.linkname.startswith('/'):
       import posixpath
       m.linkname=posixpath.relpath(m.linkname.lstrip('/'),posixpath.dirname(m.name))
     # Debian 12's pinned Python 3.11 has no extraction-filter API.
     # Validate paths and links explicitly before extracting locked APK files.
     root=dest.resolve()
     for m in members:
      target=(root/m.name).resolve()
      if not target.is_relative_to(root):raise SystemExit('Unsafe SDK archive path: '+m.name)
      if not (m.isfile() or m.isdir() or m.issym() or m.islnk()):raise SystemExit('Unsupported SDK archive entry: '+m.name)
      if m.issym() or m.islnk():
       link=(target.parent/m.linkname if m.issym() else root/m.linkname).resolve()
       if not link.is_relative_to(root):raise SystemExit('Unsafe SDK archive link: '+m.name)
     tar.extractall(dest,members=members)
   path.unlink()
   print(rid,package['name'],package['version'],flush=True)
# Copy only platform headers; never replace Zig's target libc headers with the host's.
import shutil
headers=a.output.parent/'staticlink/linux-headers';headers.mkdir(parents=True,exist_ok=True)
for name in ('fontconfig','X11','xcb','GL','KHR','EGL','freetype2','libdrm'):
 src=a.output/'linux-x64/usr/include'/name
 if src.is_dir():shutil.copytree(src,headers/name,dirs_exist_ok=True,symlinks=True)
