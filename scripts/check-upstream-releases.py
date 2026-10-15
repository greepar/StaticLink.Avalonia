#!/usr/bin/env python3
"""Plan stable releases. HTTP/network errors fail closed; only 404 means absent."""
import argparse, json, re, urllib.request, urllib.error
from pathlib import Path

def get(url):
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=45) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code == 404:
                return None
            if error.code < 500 and error.code != 429:
                raise
            if attempt == 2:
                raise
        except (OSError, TimeoutError):
            if attempt == 2:
                raise
    raise RuntimeError("Unreachable")

def plan(config, upstream, published, force=False):
    result = []
    published_versions = {v.lower() for v in published}
    for entry in config["branches"]:
        major = entry["major"]
        candidates = [v for v in upstream if re.fullmatch(r"\d+\.\d+\.\d+", v)
                      and int(v.split(".")[0]) == major]
        version = entry.get("fixed_version") or max(candidates, key=lambda v: tuple(map(int, v.split("."))))
        package = f"{version}-{entry['angle_branch']}.{entry['revision']}"
        # A repair revision is a deliberate release, not an upstream update.
        # Daily checks skip this upstream/ANGLE pair if any revision exists.
        prefix = f"{version}-{entry['angle_branch']}.".lower()
        already_published = any(
            value.startswith(prefix) and value[len(prefix):].isdigit()
            for value in published_versions
        )
        if entry.get("daily", True) and (force or not already_published):
            result.append({"ref": entry["ref"], "skiasharp_version": version, "package_version": package})
    return result

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="build/release-tracks.json")
    parser.add_argument("--output", default="release-plan.json")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    upstream = get("https://api.nuget.org/v3-flatcontainer/skiasharp/index.json")
    published = get("https://api.nuget.org/v3-flatcontainer/staticlink.avalonia/index.json")
    if upstream is None:
        raise SystemExit("SkiaSharp package index is missing")
    result = plan(json.loads(Path(args.config).read_text()), upstream["versions"], (published or {}).get("versions", []), force=args.force)
    Path(args.output).write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))
