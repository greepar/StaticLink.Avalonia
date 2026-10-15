#!/usr/bin/env python3
import json, os
from pathlib import Path
import xml.etree.ElementTree as ET
lock = json.loads(os.environ["SOURCE_LOCK_JSON"])
path = Path("build/linux-toolchain/release.lock.json")
path.write_text(json.dumps(lock, indent=2) + "\n")
project = Path("NuGet/StaticGraphics/StaticLink.Avalonia.csproj")
root = ET.parse(project)
root.find(".//Version").text = os.environ["PACKAGE_VERSION"]
for item in root.findall(".//PackageReference"):
    if item.attrib.get("Include") == "SkiaSharp":
        item.set("Version", "[" + lock["skiasharp_version"] + "]")
root.write(project, encoding="unicode")
