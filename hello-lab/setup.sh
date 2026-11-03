#!/usr/bin/env bash
set -eo pipefail
source "$(dirname "$0")/common.sh"
set -u
[[ $(uname -m) == x86_64 ]] || { echo 'This offline package is for x86_64 Ubuntu.' >&2; exit 1; }
. /etc/os-release
[[ $ID == ubuntu && ( $VERSION_ID == 22.04 || $VERSION_ID == 24.04 ) ]] || {
    echo 'Use x86_64 Ubuntu 22.04 or 24.04 for this package.' >&2; exit 1;
}
for cmd in python3 dpkg-deb tar gzip sed grep find xargs which; do
    command -v "$cmd" >/dev/null || { echo "Ubuntu base tool missing: $cmd" >&2; exit 1; }
done
sdk_env="$HOME/hello-lab-sdk/environment-setup-cortexa35-ostl-linux"
if [[ ! -f "$sdk_env" && ! -f "$lab_dir/sdk/SHA256SUMS" ]]; then
    echo 'The x86 SDK is not included yet. This is a preparation bundle, not the complete offline bundle.' >&2
    echo 'Ask the package maintainer for the completed offline ZIP before running setup.' >&2
    exit 1
fi
(
    cd "$lab_dir/offline-debs"
    sha256sum -c SHA256SUMS
)
mkdir -p "$host_tools/root" "$host_tools/bin"
for package in "$lab_dir/offline-debs/"*.deb; do
    dpkg-deb -x "$package" "$host_tools/root"
done
cat > "$host_tools/bin/tool-wrapper" <<'WRAPPER'
#!/bin/sh
tool=$(basename "$0")
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
# make needs only Ubuntu's libc. Keep host-library paths out of SDK compiler children.
if [ "$tool" != make ]; then
    export LD_LIBRARY_PATH="$root/root/lib/x86_64-linux-gnu:$root/root/usr/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
fi
if [ "$tool" = file ]; then export MAGIC="$root/root/usr/lib/file/magic.mgc"; fi
exec "$root/root/usr/bin/$tool" "$@"
WRAPPER
chmod 755 "$host_tools/bin/tool-wrapper"
for tool in make file xz; do ln -sf tool-wrapper "$host_tools/bin/$tool"; done
export PATH="$host_tools/bin:$PATH"
make --version | sed -n '1p'
file --version | sed -n '1p'
xz --version | sed -n '1p'

if [[ -f "$sdk_env" ]]; then
    load_lab_sdk
    echo 'The SDK is already installed. Next: edit src/hello_world.c and run bash build.sh.'
    exit 0
fi
if [[ -e "$HOME/hello-lab-sdk" ]]; then
    echo 'An incomplete SDK directory exists. Rename ~/hello-lab-sdk, then run setup again.' >&2
    exit 1
fi
(
    cd "$lab_dir/sdk"
    sha256sum -c SHA256SUMS
)
shopt -s nullglob
archives=("$lab_dir/sdk/"*.tar.gz "$lab_dir/sdk/"*.tar)
[[ ${#archives[@]} == 1 ]] || { echo 'Exactly one official SDK archive must be in sdk/.' >&2; exit 1; }
free_kb=$(df -Pk "$HOME" | awk 'NR==2 { print $4 }')
[[ $free_kb -ge 10485760 ]] || { echo 'At least 10 GiB free space is required in the Ubuntu home filesystem.' >&2; exit 1; }
work=$(mktemp -d "$HOME/.hello-lab-sdk-install.XXXXXX")
trap 'rm -rf "$work"' EXIT
tar -xf "${archives[0]}" -C "$work"
mapfile -t installers < <(find "$work" -type f -name '*toolchain*.sh')
[[ ${#installers[@]} == 1 ]] || { echo 'Cannot identify the SDK installer.' >&2; exit 1; }
mkdir -p "$lab_dir/output"
# Interactive official installer: the recipient sees its prompt; no automatic acceptance.
bash "${installers[0]}" -d "$HOME/hello-lab-sdk" 2>&1 | tee "$lab_dir/output/sdk-install.log"
load_lab_sdk
printf '\nSDK ready. Next: edit src/hello_world.c and run bash build.sh.\n'
