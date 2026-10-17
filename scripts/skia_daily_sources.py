"""Resolve official ANGLE releases by publication date, not legacy version ordering."""
import gzip
import json
import re
import urllib.request
import xml.etree.ElementTree as ET

FEED = 'https://api.nuget.org/v3-flatcontainer'


def json_url(url):
    with urllib.request.urlopen(url, timeout=30) as response:
        data = response.read()
    if data.startswith(b'\x1f\x8b'):
        data = gzip.decompress(data)
    return json.loads(data)


def official_angle(version=''):
    url = 'https://api.nuget.org/v3/registration5-gz-semver2/avalonia.angle.windows.natives/index.json'
    releases = []
    for page in json_url(url)['items']:
        for item in page.get('items', []) or json_url(page['@id'])['items']:
            entry = item['catalogEntry']
            if (entry.get('listed', True) and
                    re.fullmatch(r'\d+\.\d+\.\d+(?:\.\d+)?', entry['version']) and
                    entry.get('published', '')[:4] > '1900'):
                releases.append(entry)
    if not releases:
        raise RuntimeError('No listed stable official ANGLE release was found')
    if version:
        matches = [entry for entry in releases if entry['version'] == version]
        if not matches:
            raise RuntimeError('Requested ANGLE version is not an official listed stable release')
        selected = matches[0]
    else:
        # The historical 2.2.0 package predates newer 2.1.* releases.
        selected = max(releases, key=lambda entry: entry['published'])
    version = selected['version']
    url = f'{FEED}/avalonia.angle.windows.natives/{version}/avalonia.angle.windows.natives.nuspec'
    with urllib.request.urlopen(url, timeout=30) as response:
        spec = ET.fromstring(response.read())
    repository = next((node.attrib for node in spec.iter()
                       if node.tag.rsplit('}', 1)[-1] == 'repository'), {})
    if not re.fullmatch('[0-9a-f]{40}', repository.get('commit', '')):
        raise RuntimeError('Official ANGLE package has no immutable source commit')
    if repository.get('url', '').rstrip('/').lower() != 'https://github.com/avaloniaui/angle':
        raise RuntimeError('Unexpected official ANGLE source repository')
    return {'version': version, 'revision': repository['commit'], 'published': selected['published']}
