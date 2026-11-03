#!/usr/bin/env bash
set -eo pipefail
lab=$(cd "$(dirname "$0")/.." && pwd)
sdk_env=${SDK_ENV:-$HOME/hello-lab-sdk/environment-setup-cortexa35-ostl-linux}
if [ ! -f "$sdk_env" ]; then echo "SDK environment not found: $sdk_env" >&2; exit 1; fi
source "$sdk_env"
set -u
case "$CC" in aarch64-ostl-linux-gcc*) ;; *) echo 'Use the official AArch64 OpenSTLinux SDK.' >&2; exit 1;; esac
work=$(mktemp -d "$HOME/.c1-build.XXXXXX")
trap 'rm -rf "$work"' EXIT
mkdir -p "$lab/output" "$work/sdk"
cp -R "$lab/vendor/rplidar_sdk/." "$work/sdk/"
rm -rf "$work/sdk/.git" "$work/sdk/obj" "$work/sdk/output"
{
  printf 'Compiler: %s\n' "$CXX"
  $CXX --version | sed -n '1p'
  cd "$work/sdk"
  # cross_compile.sh resets compiler variables: command-line make assignments
  # retain OpenSTLinux's target flags and --sysroot in all recursive make calls.
  CROSS_COMPILE_PREFIX=aarch64-ostl-linux sh ./cross_compile.sh -j4 \
    CC="$CC" CXX="$CXX" AR="$AR" LD="$LD" BUILD_TARGET_ARCH=aarch64 V=1
  cp output/Linux/Release/ultra_simple output/Linux/Release/simple_grabber \
     output/Linux/Release/libsl_lidar_sdk.a "$lab/output/"
  for program in c1_capture c1_live; do
    $CXX $CXXFLAGS -std=c++11 -Wall -Wextra -Werror -Wno-ignored-attributes -I sdk/include \
      "$lab/src/$program.cpp" output/Linux/Release/libsl_lidar_sdk.a \
      $LDFLAGS -lpthread -lrt -o "$lab/output/$program"
  done
  $READELF -h "$lab/output/ultra_simple"
  $READELF -d "$lab/output/ultra_simple"
  printf 'BUILD PASSED\n'
} 2>&1 | tee "$lab/output/build.log"
