#!/usr/bin/env bash
# WEEK7: source the official SDK, configure ST fragments, build outside source.
set -eo pipefail
lab=${LAB_ROOT:-"$HOME/edge-ai-official"}
source "$lab/SDK/environment-setup-cortexa35-ostl-linux"
set -u
test "$CROSS_COMPILE" = aarch64-ostl-linux-
test "$ARCH" = arm64
src=${KERNEL_SRC:-"$lab/src/linux"}
meta="$lab/src/meta-st"
out="$lab/build/kernel"
extdt=${EXTDT_LINUX:-"$lab/src/external-dt/stm32mp2/a35-td/linux"}
mkdir -p "$out"
printf 'SDK: %s\nCROSS_COMPILE: %s\n' "$OECORE_SDK_VERSION" "$CROSS_COMPILE"
"${CROSS_COMPILE}gcc" --version
cd "$src"
make O="$out" defconfig
scripts/kconfig/merge_config.sh -m -r -O "$out" "$out/.config" \
 arch/arm64/configs/fragment-01-defconfig-cleanup.config \
 arch/arm64/configs/fragment-02-defconfig-addons.config \
 "$meta/recipes-kernel/linux/linux-stm32mp/6.6/fragment-03-systemd.config" \
 "$meta/recipes-kernel/linux/linux-stm32mp/6.6/fragment-04-modules.config"
scripts/config --file "$out/.config" --set-str LOCALVERSION '-gkc-sdk' --disable LOCALVERSION_AUTO
make O="$out" olddefconfig
make O="$out" -j"${JOBS:-6}" Image.gz vmlinux modules dtbs KBUILD_EXTDTS="$extdt"
make O="$out" INSTALL_MOD_PATH="$out/install_artifact" INSTALL_MOD_STRIP=1 modules_install
mkdir -p "$out/install_artifact/boot"
cp "$out/arch/arm64/boot/Image.gz" "$out/install_artifact/boot/"
find "$out/arch/arm64/boot/dts" -name 'stm32mp257f-dk*.dtb' -exec cp {} "$out/install_artifact/boot/" \;
cp "$out/.config" "$out/install_artifact/boot/config-gkc-sdk"
make -s O="$out" kernelrelease
