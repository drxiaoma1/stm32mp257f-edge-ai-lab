#!/usr/bin/env python3
from pathlib import Path
import hashlib, zipfile
lab=Path(__file__).resolve().parents[1]
destination=lab.parent/'delivery/C1激光点云实验与复现资料.zip'
def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
    return h.hexdigest()
manifest=lab/'SHA256SUMS'
files=[p for p in sorted(lab.rglob('*')) if p.is_file() and not any(v in {'.git','__pycache__','.DS_Store'} for v in p.relative_to(lab).parts) and p!=manifest]
manifest.write_text(''.join(f'{digest(p)}  {p.relative_to(lab).as_posix()}\n' for p in files))
files.append(manifest)
with zipfile.ZipFile(destination,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in files:z.write(p,Path('lidar-lab')/p.relative_to(lab))
with zipfile.ZipFile(destination) as z:
    assert z.testzip() is None
destination.with_suffix('.zip.sha256').write_text(f'{digest(destination)}  {destination.name}\n')
print(destination)
print(f'{destination.stat().st_size:,} bytes; {len(files)} files; CRC verified.')
