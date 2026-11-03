#!/usr/bin/env python3
"""Validate a GKC package and optionally install it on the observed STM32MP257F-DK."""
import argparse
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time

RELEASE = "6.6.78-gkc-sdk"


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def run(*args):
    subprocess.run(args, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    package = args.package.resolve()
    if os.geteuid() != 0:
        raise RuntimeError("Run on the board as root")
    model = Path("/proc/device-tree/model").read_bytes().rstrip(b"\0").decode()
    if "STM32MP257F-DK" not in model:
        raise RuntimeError("Unexpected board: " + model)
    running = os.uname().release
    if running not in {"6.6.78", "6.6.78-gkc-midterm"}:
        raise RuntimeError("Expected a known v25.06.11 baseline; got " + running)

    count = 0
    for line in (package / "SHA256SUMS").read_text().splitlines():
        expected, name = line.split("  ", 1)
        path = (package / name).resolve()
        if package not in path.parents or not path.is_file():
            raise RuntimeError("Invalid manifest entry: " + name)
        if digest(path) != expected:
            raise RuntimeError("Checksum mismatch: " + name)
        count += 1
    if not count:
        raise RuntimeError("Empty package manifest")

    image = package / "kernel/boot/Image.gz"
    modules = package / "kernel/lib/modules" / RELEASE
    hello = package / "hello_world/install_artifact/usr/local/bin/hello_world"
    service = package / "systemd/hello-world.service"
    config = (package / "kernel/boot/config-gkc-sdk").read_text()
    if 'CONFIG_LOCALVERSION="-gkc-sdk"' not in config or not modules.is_dir():
        raise RuntimeError("Wrong kernel release or missing modules")
    run("gzip", "-t", str(image))
    gpu_modules = list(modules.rglob("galcore.ko"))
    if len(gpu_modules) != 1:
        raise RuntimeError("Exactly one matching GPU module is required")
    vermagic = subprocess.check_output(["modinfo", "-F", "vermagic", str(gpu_modules[0])], text=True).strip()
    if vermagic.split()[0] != RELEASE:
        raise RuntimeError("GPU module version mismatch: " + vermagic)
    dtb_files = sorted((package / "kernel/boot").glob("stm32mp257f-dk*.dtb"))
    required_dtbs = {p.name for p in Path("/boot").glob("stm32mp257f-dk*.dtb")}
    if not required_dtbs or not required_dtbs.issubset({p.name for p in dtb_files}):
        raise RuntimeError("Package does not contain all current board DTB names")
    if not shutil.which("depmod"):
        raise RuntimeError("depmod is required on the board")
    if not os.path.ismount("/boot"):
        raise RuntimeError("/boot must be the mounted boot partition")
    if shutil.disk_usage("/boot").free < image.stat().st_size + sum(p.stat().st_size for p in dtb_files) + 4 * 1024**2:
        raise RuntimeError("Insufficient free space on /boot")
    if shutil.disk_usage("/").free < 160 * 1024**2:
        raise RuntimeError("Insufficient free space on root filesystem")

    rootarg = next(item for item in Path("/proc/cmdline").read_text().split()
                   if item.startswith("root=PARTUUID="))
    candidates = []
    for boot_config in Path("/boot").glob("*_extlinux/extlinux.conf"):
        content = boot_config.read_text()
        if rootarg in content:
            candidates.append((boot_config, content))
    if len(candidates) != 1:
        raise RuntimeError("Cannot uniquely match boot configuration to " + rootarg)
    boot_config, original = candidates[0]
    if boot_config != Path("/boot/mmc0_extlinux/extlinux.conf"):
        raise RuntimeError("Boot configuration differs from the inspected SD-card configuration")
    if re.search(r"^LABEL\s+gkc-sdk\s*$", original, re.M):
        raise RuntimeError("A gkc-sdk boot entry already exists; inspect it before redeploying")
    entries = re.split(r"(?=^LABEL\s+)", original, flags=re.M)
    matching = [entry for entry in entries[1:]
                if rootarg in entry and re.search(r"^\s*KERNEL\s+/Image\.gz\s*$", entry, re.M)]
    if len(matching) != 1:
        raise RuntimeError("Cannot identify the original factory boot entry")
    if not Path("/boot/Image.gz").is_file():
        raise RuntimeError("Factory image is missing")
    image_target = Path("/boot") / ("Image-" + RELEASE + ".gz")
    modules_target = Path("/lib/modules") / RELEASE
    if image_target.exists() or modules_target.exists() or Path("/boot/gkc-sdk").exists():
        raise RuntimeError("A previous installation exists; inspect before retrying")

    new_entry = re.sub(r"^LABEL\s+[^\n]+", "LABEL gkc-sdk", matching[0], count=1)
    new_entry = re.sub(r"^(\s*KERNEL\s+)/Image\.gz\s*$",
                       lambda m: m[1] + "/" + image_target.name, new_entry, flags=re.M)
    new_entry = re.sub(r"^\s*MENU LABEL[^\n]*\n?", "", new_entry, flags=re.M)
    new_entry = re.sub(r"^(\s*FDTDIR\s+)/\s*$", lambda m: m[1] + "/gkc-sdk/", new_entry, flags=re.M)
    updated = re.sub(r"^\s*DEFAULT[^\n]*\n?", "", original, flags=re.M)
    updated = re.sub(r"^TIMEOUT\s+\d+\s*$", "TIMEOUT 100", updated, flags=re.M)
    updated = "DEFAULT gkc-sdk\n" + updated.rstrip() + "\n\n" + new_entry.rstrip() + "\n"
    print("Board:", model, flush=True)
    print("Running kernel:", running, flush=True)
    print("Verified package files:", count, flush=True)
    print("New kernel SHA-256:", digest(image), flush=True)
    print("Boot configuration:", boot_config, flush=True)
    print("Existing boot entries are retained; this entry uses new SDK-built DTBs.", flush=True)
    print("Proposed boot configuration:\n" + updated, flush=True)
    if not args.apply:
        print("Validation completed. No files changed.")
        return

    backup = Path("/home/root") / ("gkc-sdk-backup-" + str(time.time_ns()))
    backup.mkdir()
    shutil.copy2(boot_config, backup / "extlinux.conf")
    shutil.copy2("/boot/Image.gz", backup / "Image.gz")
    for dtb in Path("/boot").glob("stm32mp257f-dk*.dtb"):
        shutil.copy2(dtb, backup / dtb.name)
    for source, name in [(Path("/usr/local/bin/hello_world"), "hello_world.previous"),
                         (Path("/etc/systemd/system/hello-world.service"), "hello-world.service.previous")]:
        if source.exists():
            shutil.copy2(source, backup / name)
    (backup / "boot-config-path.txt").write_text(str(boot_config) + "\n")
    (backup / "rollback.sh").write_text(
        "#!/bin/sh\nset -eu\ncp '" + str(backup / "extlinux.conf") + "' '" + str(boot_config)
        + "'\nsync\necho 'Previous boot configuration restored; reboot when ready.'\n")
    (backup / "rollback.sh").chmod(0o700)
    (backup / "proposed-extlinux.conf").write_text(updated)

    module_stage = Path(tempfile.mkdtemp(prefix=".gkc-staging-", dir="/lib/modules"))
    shutil.copytree(modules, module_stage, dirs_exist_ok=True)
    module_stage.rename(modules_target)
    run("depmod", RELEASE)
    if not list(modules_target.rglob("galcore.ko")):
        raise RuntimeError("Matching GPU module missing; boot config is unchanged")
    temporary_image = image_target.with_suffix(".gz.partial")
    shutil.copyfile(image, temporary_image)
    temporary_image.chmod(0o644)
    if digest(temporary_image) != digest(image):
        raise RuntimeError("Installed image checksum mismatch; original boot entry is unchanged")
    temporary_image.rename(image_target)
    dtbs = sorted((package / "kernel/boot").glob("stm32mp257f-dk*.dtb"))
    if not dtbs:
        raise RuntimeError("SDK-built board DTBs missing; boot config is unchanged")
    dtb_target = Path("/boot/gkc-sdk")
    dtb_target.mkdir(exist_ok=False)
    for dtb in dtbs:
        shutil.copy2(dtb, dtb_target / dtb.name)
        if digest(dtb) != digest(dtb_target / dtb.name):
            raise RuntimeError("DTB copy checksum mismatch")
    shutil.copy2(package / "kernel/boot/config-gkc-sdk", backup / ("config-" + RELEASE))
    Path("/usr/local/bin").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(hello, "/usr/local/bin/hello_world")
    Path("/usr/local/bin/hello_world").chmod(0o755)
    shutil.copyfile(service, "/etc/systemd/system/hello-world.service")
    Path("/etc/systemd/system/hello-world.service").chmod(0o644)
    run("systemctl", "daemon-reload")
    run("systemctl", "enable", "hello-world.service")
    os.sync()
    pending_config = boot_config.with_name("extlinux.conf.gkc-new")
    pending_config.write_text(updated)
    pending_config.chmod(0o644)
    os.sync()
    pending_config.replace(boot_config)
    os.sync()
    print("Installation complete. Backup:", backup, flush=True)
    print("Reboot separately, then verify uname -r and the current boot's hello-world journal.", flush=True)


if __name__ == "__main__":
    main()
