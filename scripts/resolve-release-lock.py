#!/usr/bin/env python3
"""Resolve a published SkiaSharp tag and its Skia gitlink to immutable commits."""
import argparse, json, re, subprocess, tempfile
from pathlib import Path
import xml.etree.ElementTree as ET

def git(*args):
    return subprocess.check_output(["git", *args], text=True).strip()

p = argparse.ArgumentParser()
p.add_argument("--version", default="")
p.add_argument("--output", default="build/linux-toolchain/release.lock.json")
a = p.parse_args()
root = ET.parse("NuGet/StaticGraphics/StaticLink.Avalonia.csproj").getroot()
current = next(x.attrib["Version"] for x in root.findall(".//PackageReference") if x.attrib.get("Include") == "SkiaSharp")
version = a.version or current
if not re.fullmatch(r"\d+\.\d+\.\d+", version) or version.split(".")[0] != current.split(".")[0]:
    raise SystemExit("Only stable versions from this branch's SkiaSharp major are allowed")
if current.startswith("2.") and version != "2.88.9":
    raise SystemExit("SkiaSharp 2 is frozen at 2.88.9")
base, revision = root.findtext(".//Version").rsplit(".", 1)
angle = base.split("-", 1)[1]
# ANGLE remains fixed: changing SkiaSharp must not silently change its toolchain.
profile = json.loads(Path("build/linux-toolchain/sources.lock.json").read_text())
if profile["angle_branch"] != angle:
    raise SystemExit("ANGLE branch does not match the source lock")
remote = "https://github.com/mono/SkiaSharp.git"
refs = git("ls-remote", "--tags", remote, f"refs/tags/v{version}", f"refs/tags/v{version}^{{}}")
if not refs:
    raise SystemExit(f"No immutable upstream release tag for {version}; refusing a moving branch")
lines = refs.splitlines()
commit = next((x.split()[0] for x in lines if x.endswith("^{}")), lines[0].split()[0])
with tempfile.TemporaryDirectory() as tmp:
    git("init", "-q", tmp)
    git("-C", tmp, "fetch", "-q", "--depth=1", remote, commit)
    tree = git("-C", tmp, "ls-tree", "FETCH_HEAD", "externals/skia")
    mode, kind, skia, name = tree.split()
    if mode != "160000" or kind != "commit":
        raise SystemExit("Skia source is not a pinned git submodule")
profile.update(skiasharp_version=version, skiasharp_revision=commit, skia_revision=skia)
Path(a.output).write_text(json.dumps(profile, indent=2) + "\n")
package = f"{version}-{angle}.{revision}"
print(json.dumps({"skiasharp_version": version, "package_version": package, "lock": profile}))
