# SDK method provenance

- Host: macOS Apple Silicon; Lima 2.2.1 Ubuntu 24.04 AArch64, 6 vCPU, 6 GiB RAM.
- Official SDK: MP2-DEV-Arm, STM32MP2Dev 6.1.0, v25.06.11. Downloaded through ST's approved license and guest email validation. No authentication tokens are included here.
- Installer result and environment: sdk-install.log and sdk-environment.txt. Compiler aarch64-ostl-linux-gcc 13.3.0; target sysroot cortexa35-ostl-linux.
- BSP source archive guest link returned HTTP 403. The WEEK7 PDF physical page 41, section 4.1, explicitly provides ST GitHub as an alternative source preparation method. We use this method with the same SDK.
- Linux official ST tag: https://github.com/STMicroelectronics/linux/tree/v6.6-stm32mp-r2
- Distribution recipe: https://github.com/STMicroelectronics/meta-st-stm32mp/tree/openstlinux-6.6-yocto-scarthgap-mpu-v25.06.11
- External DT revision from that recipe: ea2e971efac93f4644ceede7b997081ed49780ad, https://github.com/STMicroelectronics/dt-stm32mp
- GPU source revision from that recipe: 7c181cacf89f918039e64934fdc33fe817a052cd, https://github.com/STMicroelectronics/gcnano-binaries
- Source archives freshly extracted into ~/edge-ai-official/src; build outputs created in a new ~/edge-ai-official/build/kernel directory. Previous GNU build outputs were not reused.
- New local version: 6.6.78-gkc-sdk.
- All three compiled STM32MP257F-DK DTBs match their factory counterparts byte-for-byte; see config-dtb-comparison.txt.
- The user confirmed the teacher-linked download is FLASH (Starter), not SOURCES. FLASH remains valid for initial flashing/recovery. The completed SDK + official GitHub route does not require this separate SOURCES archive.
- SDK kernel physical power cycle: user confirmed power removed and restored. The first read-only SSH observation on 2026-10-25 21:32:55 +08:00 found boot ID 3c09cd7b-19c2-49df-a3f1-d332e1575a2e; hello-world had already executed at 11.416478 seconds since boot, Result=success, exit=0.
- Initial week6-* logs use the prior GNU baseline; sdk-kernel-week6-* logs record follow-up demonstrations on 6.6.78-gkc-sdk. Final manual screenshots are captured again on the SDK kernel.
- Screenshot collection uses a fresh directory each time. Sorting old board screenshots by filesystem date is unreliable because the RTC resets after power loss.
- Windows migration instructions are documented but not tested end-to-end on a Windows PC in this run.
