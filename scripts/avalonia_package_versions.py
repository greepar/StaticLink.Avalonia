"""Deployment versions are separate from the immutable native source recipe."""
import json
from pathlib import Path
import re


def native_package_version(profile):
    root = Path(__file__).resolve().parents[1]
    versions = json.loads((root / 'build/avalonia-native-package-versions.json').read_text())
    version = versions.get(profile['avalonia_version'], profile['avalonia_version'] + '.1')
    if not re.fullmatch(re.escape(profile['avalonia_version']) + r'\.[1-9]\d*', version):
        raise ValueError('Native package must match the official Avalonia version')
    return version
