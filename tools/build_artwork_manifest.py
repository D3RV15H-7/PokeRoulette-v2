#!/usr/bin/env python3
"""Update the local artwork manifest from supplied, permitted scans.

Place named scans in images/delta-reign/001.webp ... 141.webp and run:
    python3 tools/build_artwork_manifest.py
Only verified Delta Reign numbers and names from the bundled English checklist
will enter the manifest. Existing non-Delta entries are preserved.
"""
from pathlib import Path
import json,re,sys
ROOT=Path(__file__).resolve().parents[1]
reference=json.loads((ROOT/'data/delta-reign-reference.json').read_text())
manifest_path=ROOT/'data/artwork-manifest.json'
manifest=json.loads(manifest_path.read_text())
assert reference['setId']=='me06' and len(reference['cards'])==141
assert manifest['version']==1 and isinstance(manifest['cards'],list)
scan_dir=ROOT/'images/delta-reign'
allowed={'.webp','.png','.jpg','.jpeg'}
entries=[];missing=[];bad=[]
for entry in reference['cards']:
    number=entry['number']; choices=[scan_dir/(number+ext) for ext in sorted(allowed)]
    supplied=[p for p in choices if p.is_file()]
    if len(supplied)>1: bad.append(f'{number}: multiple image formats'); continue
    if not supplied: missing.append(number);continue
    p=supplied[0]
    if p.stat().st_size<1024: bad.append(f'{number}: suspiciously small file');continue
    signature=p.read_bytes()[:12]
    good= (p.suffix=='.png' and signature.startswith(b'\x89PNG\r\n\x1a\n')) or (p.suffix in ('.jpg','.jpeg') and signature.startswith(b'\xff\xd8')) or (p.suffix=='.webp' and signature[:4]==b'RIFF' and signature[8:12]==b'WEBP')
    if not good: bad.append(f'{number}: file extension/signature mismatch');continue
    entries.append({'setId':'me06','number':number,'name':entry['name'],'folder':'delta-reign','file':f'images/delta-reign/{p.name}','source':'collector-supplied'})
if bad:
    print('Artwork validation failed:\n'+'\n'.join(bad),file=sys.stderr);sys.exit(1)
others=[e for e in manifest['cards'] if e.get('setId')!='me06']
manifest['cards']=others+entries
manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print(f'Delta Reign: {len(entries)}/141 local fronts, {len(missing)} still missing')
