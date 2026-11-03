#!/usr/bin/env bash
set -eo pipefail
lab=${LAB_ROOT:-"$HOME/edge-ai-official"}
source "$lab/SDK/environment-setup-cortexa35-ostl-linux"
set -u
test "$CROSS_COMPILE" = aarch64-ostl-linux-
src=${GPU_SRC:-"$lab/src/gcnano/gcnano-driver-stm32mp"}
out="$lab/build/kernel"
make -j"${JOBS:-6}" -C "$out" M="$src" AQROOT="$src" SOC_PLATFORM=st-mp2 DEBUG=0 modules
make -C "$out" M="$src" AQROOT="$src" SOC_PLATFORM=st-mp2 DEBUG=0 INSTALL_MOD_PATH="$out/install_artifact" INSTALL_MOD_STRIP=1 modules_install
