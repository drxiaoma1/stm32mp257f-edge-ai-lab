#!/usr/bin/env bash
set -eo pipefail
lab=${LAB_ROOT:-"$HOME/edge-ai-official"}
project=${PROJECT_ROOT:-"$(cd "$(dirname "$0")/.." && pwd)"}
source "$lab/SDK/environment-setup-cortexa35-ostl-linux"
set -u
out="$lab/build/kernel"
release=$(make -s -C "$out" kernelrelease)
test "$release" = 6.6.78-gkc-sdk
mkdir -p "$lab/hello_world"
cp "$project/hello_world/hello_world.c" "$project/hello_world/Makefile" "$lab/hello_world/"
make -C "$lab/hello_world" clean all install
stage="$lab/package/gkc-sdk"
test ! -e "$stage"
mkdir -p "$stage/kernel" "$stage/hello_world" "$stage/systemd" "$stage/scripts"
cp -a "$out/install_artifact/." "$stage/kernel/"
# Kernel development symlinks point into the build host and are not deployed.
find "$stage/kernel/lib/modules" -type l -name build -delete
find "$stage/kernel/lib/modules" -type l -name source -delete
cp -a "$lab/hello_world/install_artifact" "$stage/hello_world/"
cp "$project/hello_world/hello_world.c" "$project/hello_world/Makefile" "$stage/hello_world/"
cp "$project/systemd/hello-world.service" "$stage/systemd/"
cp "$project/scripts/deploy-sdk-board.py" "$project/scripts/verify-board.sh" "$stage/scripts/"
cd "$stage"
find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS
mkdir -p "$project/delivery"
tar -czf "$project/delivery/gkc-sdk-6.6.78.tar.gz" -C "$lab/package" gkc-sdk
sha256sum "$project/delivery/gkc-sdk-6.6.78.tar.gz"
