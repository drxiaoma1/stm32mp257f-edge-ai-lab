#!/usr/bin/env python3
"""Build the small offline board installer with checksums and SDK licenses."""
from pathlib import Path
import hashlib,shutil,tarfile
root=Path(__file__).resolve().parent
stage=root/'output/c1-boot-demo-live';stage.mkdir(parents=True,exist_ok=True)
for file in (root/'board').iterdir():
    if file.is_file():shutil.copy2(file,stage/file.name)
for name in ['c1_capture','c1_live','cp210x.ko','usbserial.ko']:
    shutil.copy2(root/'output'/name,stage/name)
shutil.copy2(root.parent/'LICENSE.txt',stage/'LICENSE.txt')
shutil.copy2(root.parent/'vendor/rplidar_sdk/LICENSE',stage/'RPLIDAR-SDK-LICENSE.txt') if (root.parent/'vendor/rplidar_sdk/LICENSE').exists() else shutil.copy2(root.parent/'vendor/rplidar_sdk/LICENSE.txt',stage/'RPLIDAR-SDK-LICENSE.txt')
if (root/'README.md').exists():shutil.copy2(root/'README.md',stage/'README.md')
files=sorted(p for p in stage.rglob('*') if p.is_file() and p.name!='SHA256SUMS')
(stage/'SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+str(p.relative_to(stage))+'\n' for p in files))
archive=root/'output/c1-boot-demo.tar.gz'
with tarfile.open(archive,'w:gz') as tar:tar.add(stage,arcname="c1-boot-demo")
archive.with_suffix('.gz.sha256').write_text(hashlib.sha256(archive.read_bytes()).hexdigest()+'  '+archive.name+'\n')
print(archive,archive.stat().st_size)
