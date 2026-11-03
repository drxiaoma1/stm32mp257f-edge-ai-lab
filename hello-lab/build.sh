#!/usr/bin/env bash
set -eo pipefail
source "$(dirname "$0")/common.sh"
set -u
load_lab_sdk
mkdir -p "$lab_dir/output"
# Keep compilation on the Linux filesystem even when the input is shared from Windows.
work=$(mktemp -d "$HOME/.hello-lab-build.XXXXXX")
trap 'rm -rf "$work"' EXIT
cp "$lab_dir/src/hello_world.c" "$lab_dir/src/Makefile" "$work/"
{
    printf 'Compiler: %s\n' "$CC"
    make -C "$work" clean all
    $READELF -h "$work/hello_world" | sed -n '1,20p'
} 2>&1 | tee "$lab_dir/output/build.log"
$READELF -h "$work/hello_world" | grep -q 'Machine:.*AArch64'
stage="$work/hello-lab-deploy"
mkdir -p "$stage"
cp "$work/hello_world" "$stage/"
cp "$lab_dir/board/"* "$stage/"
chmod 755 "$stage/"*.sh "$stage/hello_world"
(
    cd "$stage"
    sha256sum hello_world *.sh *.service > SHA256SUMS
)
tar -czf "$lab_dir/output/hello-lab-deploy.tar.gz" -C "$work" hello-lab-deploy
cp "$work/hello_world" "$lab_dir/output/hello_world"
printf '\nBuild succeeded: %s/output/hello-lab-deploy.tar.gz\n' "$lab_dir"
printf 'Next: transfer this file from the host computer to the board.\n'
