#!/usr/bin/env python3
"""Build verified local card-front manifest from numbered descriptive files.

For Delta Reign, names such as 001-Heracross-Delta-Reign.jpg are supported.
This tool preserves verified manifest records for other sets. Run from anywhere:
    python3 tools/build_artwork_manifest.py
"""
from pathlib import Path
import json
import re
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / 'data/delta-reign-reference.json'
MANIFEST = ROOT / 'data/artwork-manifest.json'
ARTWORK = ROOT / 'images/delta-reign'
FORMATS = {'.jpg', '.jpeg', '.png', '.webp'}


def name_key(value):
    clean = unicodedata.normalize('NFKD', str(value)).casefold()
    return ''.join(ch for ch in clean if ch.isalnum() and not unicodedata.combining(ch))


def english_file_name_key(value):
    """Accept only a handful of verified differences from the English checklist."""
    return name_key(value)


# Names used in collector-supplied scans differ from abbreviated set checklist.
VERIFIED_FILENAME_ALIASES = {
    '102': {'tateandlizastraining'},
    '130': {'tateandlizastraining'},
    '132': {'bubblywaterenergy'},
    '133': {'growinggrassenergy'},
    '134': {'nitrofireenergy'},
}


def valid_signature(path):
    if path.stat().st_size < 1024:
        return False
    sig = path.open('rb').read(12)
    ext = path.suffix.lower()
    return (
        (ext == '.png' and sig.startswith(b'\x89PNG\r\n\x1a\n'))
        or (ext in ('.jpg', '.jpeg') and sig.startswith(b'\xff\xd8'))
        or (ext == '.webp' and sig[:4] == b'RIFF' and sig[8:12] == b'WEBP')
    )


def main():
    reference = json.loads(REFERENCE.read_text(encoding='utf-8'))
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    if reference.get('setId') != 'me06' or len(reference.get('cards', [])) != 141:
        raise ValueError('Expected Delta Reign English 141-card reference')
    if manifest.get('version') != 1 or not isinstance(manifest.get('cards'), list):
        raise ValueError('Unsupported artwork manifest')

    by_number = {}
    errors = []
    for file in ARTWORK.iterdir() if ARTWORK.is_dir() else []:
        if not file.is_file() or file.suffix.lower() not in FORMATS:
            continue
        match = re.fullmatch(r'(\d{3})(?:-(.*))?', file.stem)
        if not match:
            errors.append(f'{file.name}: filename must start with a three-digit card number')
            continue
        number = match.group(1)
        by_number.setdefault(number, []).append((file, match.group(2)))

    new_entries = []
    missing = []
    for card in reference['cards']:
        number = card['number']
        options = by_number.pop(number, [])
        if not options:
            missing.append(number)
            continue
        if len(options) != 1:
            errors.append(f'{number}: multiple artwork files')
            continue
        file, suffix = options[0]
        if suffix:
            # Allow the descriptive filename, the standard Delta-Reign tail,
            # and a numbered download suffix (e.g. 'Delta-Reign 2').
            label = re.sub(r'-Delta-Reign(?:\s+\d+)?$', '', suffix, flags=re.I)
            found = english_file_name_key(label)
            expected = name_key(card['name'])
            if found != expected and found not in VERIFIED_FILENAME_ALIASES.get(number, set()):
                errors.append(f'{file.name}: name does not match #{number} {card["name"]}')
                continue
        if not valid_signature(file):
            errors.append(f'{file.name}: invalid or unusually small image')
            continue
        new_entries.append({
            'setId': 'me06', 'number': number, 'name': card['name'],
            'folder': 'delta-reign', 'file': f'images/delta-reign/{file.name}',
            'source': 'collector-supplied'
        })

    for number, leftovers in sorted(by_number.items()):
        errors.append(f'{number}: unknown Delta Reign card number')
    if errors:
        raise ValueError('Artwork validation failed:\n' + '\n'.join(errors))

    existing = [e for e in manifest['cards'] if e.get('setId') != 'me06']
    manifest['cards'] = existing + new_entries
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Delta Reign local artwork: {len(new_entries)}/141 matched, {len(missing)} missing')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
