#!/usr/bin/env python3
"""Audit the final assessment files without touching a connected board (stdlib only)."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import struct
import tarfile

ROOT = Path(__file__).resolve().parents[1]
RELEASE = '6.6.78-gkc-sdk'
REQUIRED = {
    '1_environment': [
        'README.md', 'README.zh-CN.md', 'readme.txt',
        'evidence/sdk-environment.txt', 'scripts/build-sdk-kernel.sh',
        'scripts/build-sdk-gpu.sh'],
    '2_kernel': [
        'artifacts/kernel/Image', 'artifacts/kernel/Image.gz',
        'artifacts/kernel/.config', 'artifacts/kernel/Module.symvers',
        'artifacts/kernel/stm32mp257f-dk.dtb',
        'artifacts/kernel/stm32mp257f-dk-ca35tdcid-ostl.dtb',
        'artifacts/kernel/stm32mp257f-dk-ca35tdcid-ostl-m33-examples.dtb',
        'artifacts/drivers/galcore.ko', 'packages/gkc-kernel-6.6.78.tar.gz',
        'scripts/deploy-sdk-board.py', 'evidence/kernel-build.log',
        'evidence/final-system.txt'],
    '3_hello_world': [
        'dual-hello/user/hello_world.c', 'dual-hello/user/Makefile',
        'artifacts/hello/hello_world.c', 'artifacts/hello/Makefile',
        'artifacts/hello/hello_world', 'dual-hello/kernel/hello_kernel.c',
        'dual-hello/kernel/Makefile', 'artifacts/drivers/hello_kernel.ko',
        'dual-hello/build.sh', 'dual-hello/board/verify.sh',
        'packages/dual-hello-deploy.tar.gz',
        'evidence/dual-greeting-final/verification.json'],
    '4_c1_kernel_driver': [
        'artifacts/drivers/usbserial.ko', 'artifacts/drivers/cp210x.ko',
        'lidar-lab/boot-demo/board/c1-lidar.conf',
        'lidar-lab/boot-demo/board/99-c1-lidar.rules',
        'evidence/driver-insertion.txt'],
    '5_c1_application': [
        'lidar-lab/src/c1_capture.cpp', 'lidar-lab/src/c1_live.cpp',
        'lidar-lab/src/scan_validity.h', 'lidar-lab/Makefile',
        'lidar-lab/scripts/build.sh', 'lidar-lab/vendor/rplidar_sdk/LICENSE',
        'lidar-lab/vendor/rplidar_sdk/sdk/include/sl_lidar.h',
        'artifacts/lidar/c1_capture', 'artifacts/lidar/c1_live',
        'lidar-lab/boot-demo/board/c1_demo.py',
        'lidar-lab/boot-demo/board/render_pointcloud.py',
        'lidar-lab/boot-demo/board/c1-demo.service',
        'lidar-lab/boot-demo/board/start-live.sh',
        'lidar-lab/boot-demo/board/050-c1-lidar.yaml',
        'install-board.sh', 'packages/c1-boot-demo.tar.gz',
        'evidence/automatic-final/scan.csv',
        'evidence/automatic-final/scan.csv.json',
        'evidence/automatic-final/state.json',
        'evidence/continuous-fixed/session/session.json',
        'evidence/continuous-fixed/session/scan.csv',
        'evidence/boot-hello.png', 'evidence/boot-result.png',
        'evidence/home.png', 'evidence/live.png', 'evidence/launcher.png'],
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def elf_aarch64(data, label):
    require(data[:6] == b'\x7fELF\x02\x01', label + ': not ELF64 little-endian')
    require(struct.unpack_from('<H', data, 18)[0] == 183, label + ': not AArch64')


def module(data, label):
    elf_aarch64(data, label)
    found = re.search(rb'vermagic=([^\x00]+)', data)
    require(found and found[1].startswith(RELEASE.encode() + b' '),
            label + ': kernel version mismatch')


def tar_contents(path):
    data = {}
    with tarfile.open(path) as archive:
        for item in archive.getmembers():
            name = PurePosixPath(item.name)
            require(not name.is_absolute() and '..' not in name.parts,
                    'Unsafe archive path: ' + item.name)
            require(item.isdir() or item.isfile(), 'Unexpected archive link: ' + item.name)
            if item.isfile():
                require(item.name not in data, 'Duplicate archive entry: ' + item.name)
                data[item.name] = archive.extractfile(item).read()
    manifests = [name for name in data if name.endswith('/SHA256SUMS')]
    require(len(manifests) == 1, str(path) + ': expected one manifest')
    base = manifests[0].rsplit('/', 1)[0]
    listed = set()
    for line in data[manifests[0]].decode().splitlines():
        expected, relative = line.split('  ', 1)
        full = base + '/' + relative
        require(full in data and sha(data[full]) == expected, 'Archive checksum: ' + full)
        listed.add(full)
    require(listed == set(data) - set(manifests), 'Unlisted archive payload: ' + str(path))
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-report', action='store_true',
                        help='Write SUBMISSION-AUDIT.json before generating SHA256SUMS')
    args = parser.parse_args()
    report = {'audit_date': '2026-11-10', 'kernel_release': RELEASE,
              'scope': 'Static final-deliverable audit; no new hardware run',
              'requirements': {}, 'checks': [], 'artifacts': {}}
    for group, paths in REQUIRED.items():
        for name in paths:
            require((ROOT / name).is_file() and (ROOT / name).stat().st_size > 0,
                    'Missing/empty required file: ' + name)
        report['requirements'][group] = {'status': 'present', 'files': paths}
    for name in ['hello_world.c', 'Makefile']:
        require((ROOT / 'dual-hello/user' / name).read_bytes() ==
                (ROOT / 'artifacts/hello' / name).read_bytes(), 'Hello source copy mismatch')
    for name in ['artifacts/hello/hello_world', 'artifacts/lidar/c1_capture', 'artifacts/lidar/c1_live']:
        elf_aarch64((ROOT / name).read_bytes(), name)
    for path in (ROOT / 'artifacts/drivers').glob('*.ko'):
        module(path.read_bytes(), path.name)
    image = (ROOT / 'artifacts/kernel/Image').read_bytes()
    require(image[56:60] == b'ARM\x64', 'Invalid ARM64 Image magic')
    require(gzip.decompress((ROOT / 'artifacts/kernel/Image.gz').read_bytes()) == image,
            'Image.gz does not expand to Image')
    config = (ROOT / 'artifacts/kernel/.config').read_text()
    for setting in ['CONFIG_LOCALVERSION="-gkc-sdk"', 'CONFIG_USB_SERIAL=m', 'CONFIG_USB_SERIAL_CP210X=m']:
        require(setting in config.splitlines(), 'Missing kernel config: ' + setting)
    report['checks'].append('Required files, exact Hello source/Makefile copies, AArch64 ELF/module versions and kernel image verified')

    # Compare submitted executable bytes with the final running-board records.
    observations = (ROOT / 'evidence/final-system.txt').read_text() + '\n' + (ROOT / 'evidence/final-installed-hashes.txt').read_text()
    recorded = dict((name, digest) for digest, name in re.findall(r'^([0-9a-f]{64})\s+(\S+)$', observations, re.M))
    for local, remote in {
        'artifacts/kernel/Image.gz': '/boot/Image-6.6.78-gkc-sdk.gz',
        'artifacts/hello/hello_world': '/opt/hello-lab/hello_world',
        'artifacts/lidar/c1_capture': '/opt/c1-lab/c1_capture',
        'artifacts/lidar/c1_live': '/opt/c1-lab/c1_live',
        'lidar-lab/boot-demo/board/start-live.sh': '/usr/local/demo/application/c1-lidar/start-live.sh',
    }.items():
        require(sha((ROOT / local).read_bytes()) == recorded[remote], 'Final hardware hash mismatch: ' + local)
    report['checks'].append('Kernel, Hello, C1 executables and launcher match final running-board hashes')

    kernel = tar_contents(ROOT / 'packages/gkc-kernel-6.6.78.tar.gz')
    require(all(n == 'gkc-kernel/SHA256SUMS' or n.startswith(('gkc-kernel/kernel/', 'gkc-kernel/scripts/')) for n in kernel),
            'Kernel package contains non-kernel application files')
    require(kernel['gkc-kernel/scripts/deploy-sdk-board.py'] == (ROOT / 'scripts/deploy-sdk-board.py').read_bytes(), 'Kernel installer copy mismatch')
    require(kernel['gkc-kernel/kernel/boot/Image.gz'] == (ROOT / 'artifacts/kernel/Image.gz').read_bytes(), 'Kernel archive image mismatch')
    module_names = [n for n in kernel if n.endswith('.ko')]
    require(len(module_names) == 1044, 'Incomplete matched kernel module tree')
    for name in module_names:
        module(kernel[name], name)
    for name in ['cp210x.ko', 'usbserial.ko', 'galcore.ko']:
        matches = [n for n in module_names if n.endswith('/' + name)]
        require(len(matches) == 1 and kernel[matches[0]] == (ROOT / 'artifacts/drivers' / name).read_bytes(), 'Driver archive mismatch: ' + name)
    for path in (ROOT / 'artifacts/kernel').glob('*.dtb'):
        require(kernel['gkc-kernel/kernel/boot/' + path.name] == path.read_bytes(), 'DTB mismatch')
    require(kernel['gkc-kernel/kernel/boot/config-gkc-sdk'] == (ROOT / 'artifacts/kernel/.config').read_bytes(), 'Kernel config mismatch')
    report['checks'].append('Kernel-only package contains the exact image, DTBs and all 1044 matched modules, including galcore')

    for folder, archive_name, prefix, binaries in [
        ('dual-hello', 'dual-hello-deploy.tar.gz', 'dual-hello-deploy',
         {'hello_world': 'artifacts/hello/hello_world', 'hello_kernel.ko': 'artifacts/drivers/hello_kernel.ko'}),
        ('lidar-lab/boot-demo', 'c1-boot-demo.tar.gz', 'c1-boot-demo',
         {'c1_capture': 'artifacts/lidar/c1_capture', 'c1_live': 'artifacts/lidar/c1_live',
          'cp210x.ko': 'artifacts/drivers/cp210x.ko', 'usbserial.ko': 'artifacts/drivers/usbserial.ko'}),
    ]:
        data = tar_contents(ROOT / 'packages' / archive_name)
        expected = {p.name: p.read_bytes() for p in (ROOT / folder / 'board').iterdir() if p.is_file()}
        expected.update({n: (ROOT / path).read_bytes() for n, path in binaries.items()})
        if prefix == 'c1-boot-demo':
            expected.update({'README.md': (ROOT / folder / 'README.md').read_bytes(),
                             'LICENSE.txt': (ROOT / 'lidar-lab/LICENSE.txt').read_bytes(),
                             'RPLIDAR-SDK-LICENSE.txt': (ROOT / 'lidar-lab/vendor/rplidar_sdk/LICENSE').read_bytes()})
        require(set(data) == {prefix + '/' + n for n in expected} | {prefix + '/SHA256SUMS'}, 'Unexpected/missing final installer payload')
        for name, content in expected.items():
            require(data[prefix + '/' + name] == content, 'Installer source/binary mismatch: ' + name)
    report['checks'].append('Greeting and C1 packages contain only their exact final sources and binaries')
    for path in sorted((ROOT / 'artifacts').rglob('*')) + sorted((ROOT / 'packages').glob('*.tar.gz')):
        if path.is_file():
            report['artifacts'][str(path.relative_to(ROOT))] = {'bytes': path.stat().st_size, 'sha256': sha(path.read_bytes())}
    final = json.loads((ROOT / 'evidence/dual-greeting-final/verification.json').read_text())
    auto = json.loads((ROOT / 'evidence/automatic-final/state.json').read_text())
    live = json.loads((ROOT / 'evidence/continuous-fixed/session/session.json').read_text())
    require(final['hello_two_contexts_passed'] and final['kernel_print_count'] == final['user_print_count'] == 1, 'Missing two-context greeting evidence')
    require(auto['boot_id'] == final['boot_id'] and auto['phase'] == 'complete', 'Final automatic run mismatch')
    require(live['elapsed_seconds'] > 180 and live['stop_requested'] and live['stop_command_ok'], 'Continuous scan/stop evidence missing')
    report['checks'].append('Final two-context greeting, software-boot automatic scan and continuous Stop evidence verified')
    report['result'] = 'PASS'
    report['remaining_human_fields'] = ['Project name', 'Group number', 'Confirmed student author names and order']
    report['verification_limits'] = ['No new hardware test during this packaging audit',
        'Latest runtime evidence covers software reboot, not a new physical power cycle',
        'Physical USB unplug/replug recovery and full Windows reproduction were not tested',
        'Kernel-only deployment wrapper was statically checked; its application-install section was removed without reflashing the board']
    if args.write_report:
        (ROOT / 'SUBMISSION-AUDIT.json').write_text(json.dumps(report, indent=2) + '\n')
    else:
        manifest = ROOT / 'SHA256SUMS'
        require(manifest.is_file(), 'Missing SHA256SUMS')
        for line in manifest.read_text().splitlines():
            expected, name = line.split('  ', 1)
            path = (ROOT / name).resolve()
            require(ROOT in path.parents and path.is_file() and sha(path.read_bytes()) == expected, 'Submission checksum mismatch: ' + name)
        report['checks'].append('Submission SHA256SUMS verified')
    print(json.dumps({'result': report['result'], 'requirements': len(REQUIRED),
                      'artifact_files': len(report['artifacts']), 'checks': report['checks']}, indent=2))


if __name__ == '__main__':
    main()
