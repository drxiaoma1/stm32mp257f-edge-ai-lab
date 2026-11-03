#!/usr/bin/env python3
from pathlib import Path
import hashlib,shutil,tarfile
root=Path(__file__).resolve().parent
stage=root/'output/dual-hello-deploy';stage.mkdir(exist_ok=True)
for f in (root/'board').iterdir():
    if f.is_file():shutil.copy2(f,stage/f.name)
for name in ['hello_kernel.ko','hello_world']:shutil.copy2(root/'output'/name,stage/name)
files=sorted(p for p in stage.iterdir() if p.is_file() and p.name!='SHA256SUMS')
(stage/'SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in files))
archive=root/'output/dual-hello-deploy.tar.gz'
with tarfile.open(archive,'w:gz') as t:t.add(stage,arcname=stage.name)
print(archive,archive.stat().st_size)
