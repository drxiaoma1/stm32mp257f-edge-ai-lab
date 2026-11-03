#!/usr/bin/env bash
set -eo pipefail
root=$(cd "$(dirname "$0")" && pwd)
sdk_env=${SDK_ENV:-$HOME/edge-ai-official/SDK/environment-setup-cortexa35-ostl-linux}
kernel_source=${KERNEL_SOURCE:-$HOME/edge-ai-official/src/linux}
kernel_build=${KERNEL_BUILD:-$HOME/edge-ai-official/build/kernel}
source "$sdk_env"
set -u
test -s "$kernel_build/Module.symvers"
test "$(make -s -C "$kernel_source" O="$kernel_build" kernelrelease)" = 6.6.78-gkc-sdk
work=$(mktemp -d "$HOME/.dual-hello-build.XXXXXX")
trap 'rm -rf "$work"' EXIT
mkdir -p "$root/output" "$root/evidence" "$work/kernel" "$work/user"
cp "$root/kernel/"* "$work/kernel/"
cp "$root/user/"* "$work/user/"
{
    "$CROSS_COMPILE"gcc --version | head -1
    make -C "$kernel_source" O="$kernel_build" M="$work/kernel" -j4 modules
    ${CROSS_COMPILE}strip --strip-debug "$work/kernel/hello_kernel.ko"
    make -C "$work/user" clean all
    cp "$work/kernel/hello_kernel.ko" "$work/user/hello_world" "$root/output/"
    modinfo "$root/output/hello_kernel.ko"
    $READELF -h "$root/output/hello_world"
    sha256sum "$root/output/hello_kernel.ko" "$root/output/hello_world"
} 2>&1 | tee "$root/evidence/build.txt"
