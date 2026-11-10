# Final assessment submission checklist

[English guide](README.md) | [中文指南](README.zh-CN.md)

Audit date: **2026-11-10**. Runtime: **Linux 6.6.78-gkc-sdk** on STM32MP257F-DK.

**All five required deliverable groups are present.** The files below are included directly in this repository and in the [final release ZIP](https://github.com/drxiaoma1/stm32mp257f-edge-ai-lab/releases/tag/v1.2-final). The ZIP is an installable project bundle, not a complete SD-card image.

| Teacher's requirement | Submitted files | Final verification evidence |
|---|---|---|
| 1. Environment setup | [English report](readme.txt), [SDK/kernel build script](scripts/build-sdk-kernel.sh), [GPU build script](scripts/build-sdk-gpu.sh). The guide distinguishes macOS ARM64 Ubuntu from Windows x86_64 Ubuntu and selects the matching official SDK. | [Official SDK environment](evidence/sdk-environment.txt), [kernel build log](evidence/kernel-build.log) |
| 2. Kernel recompilation, including generated Image | [Image](artifacts/kernel/Image), [Image.gz](artifacts/kernel/Image.gz), [.config](artifacts/kernel/.config), [Module.symvers](artifacts/kernel/Module.symvers), and all three DK device trees in [artifacts/kernel](artifacts/kernel). The [kernel-only deployment package](packages/gkc-kernel-6.6.78.tar.gz) includes **1,044 matching modules**, including the display driver [galcore.ko](artifacts/drivers/galcore.ko). | [Final running kernel and hashes](evidence/final-system.txt); the uncompressed image equals the decompressed Image.gz |
| 3. Hello World user program, Makefile and executable | [hello_world.c](artifacts/hello/hello_world.c), [Makefile](artifacts/hello/Makefile), [hello_world executable](artifacts/hello/hello_world). The distinct kernel greeting is supplied as [hello_kernel.c](dual-hello/kernel/hello_kernel.c), [module Makefile](dual-hello/kernel/Makefile) and [hello_kernel.ko](artifacts/drivers/hello_kernel.ko). | [Build output](evidence/build-hello.txt), [two-context verification](evidence/dual-greeting-final/verification.json), [greeting screenshot](evidence/boot-hello.png) |
| 4. C1 driver module insertion with insmod | [usbserial.ko](artifacts/drivers/usbserial.ko), [cp210x.ko](artifacts/drivers/cp210x.ko), [boot module configuration](lidar-lab/boot-demo/board/c1-lidar.conf), [stable-device udev rule](lidar-lab/boot-demo/board/99-c1-lidar.rules). STEP 3 gives the exact dependency-ordered insmod commands. | [Actual driver insertion excerpt](evidence/driver-insertion.txt); both modules match the submitted kernel |
| 5. LiDAR acquisition application and operation report | [c1_capture.cpp](lidar-lab/src/c1_capture.cpp), [c1_live.cpp](lidar-lab/src/c1_live.cpp), [Makefile](lidar-lab/Makefile), [official SDK source](lidar-lab/vendor/rplidar_sdk), [c1_capture executable](artifacts/lidar/c1_capture), [c1_live executable](artifacts/lidar/c1_live), and [touchscreen/startup files](lidar-lab/boot-demo/board). | [Automatic scan data](evidence/automatic-final), [continuous session data](evidence/continuous-fixed/session), [automatic image](evidence/boot-result.png), [live image](evidence/live.png), [launcher image](evidence/launcher.png) |

## Complete final behavior

1. The `hello_kernel` module executes `pr_info` in kernel space during startup.
2. The user-space `hello_world` executable runs once and prints the student's name and ID. The screen also reads back the earlier kernel message.
3. C1 automatically acquires data for 10 seconds and displays its measured point cloud. Initialization and rendering add time to the full screen sequence.
4. Home and the ST desktop icon provide the manual interface. Manual acquisition runs continuously, refreshes the image about once per second and stops only on Stop or a genuine transport failure. The user can then return Home/Desktop.
5. USB serial communication is provided by kernel modules; C1 protocol commands, acquisition and plotting execute in user space.

The final records show one greeting in each context, a **10.000975-second** automatic scan with **28,230 valid points**, and a **189.800798-second** continuous session with **798,803 valid points**, stopped successfully by the user interface.

## Install and audit

- [install-board.sh](install-board.sh) installs the complete application on a board already running the matched kernel. It uses the [greeting package](packages/dual-hello-deploy.tar.gz) and [C1 package](packages/c1-boot-demo.tar.gz).
- [scripts/deploy-sdk-board.py](scripts/deploy-sdk-board.py), also included in the kernel package, validates/installs only the kernel, device trees and full module tree on the matching factory baseline. Use STEP 1 before the application installer when necessary. Extract the inner kernel archive on Linux/the board; its module filenames are case-sensitive.
- [SHA256SUMS](SHA256SUMS) covers the submitted files. The inner packages also contain complete checksum manifests.
- [SUBMISSION-AUDIT.json](SUBMISSION-AUDIT.json) lists the five requirement groups and the SHA-256/size of every compiled artifact and deployment package.

Run from the repository or extracted final ZIP:

```sh
sha256sum -c SHA256SUMS
python3 scripts/verify-submission.py
```

The verifier checks file presence, AArch64 ELF types, module/kernel versions, image compression, all 1,044 runtime modules, exact package/source correspondence, and recorded final board hashes. It performs no deployment and does not control connected hardware.

## Scope of the recorded verification

The final application has software-reboot, touch-control and continuous-scan evidence. The experimenter confirmed successful hands-on operation. This file audit did not rerun hardware tests or flash the board. Physical USB unplug/replug recovery, a new cold power cycle of the exact final runtime, and the full Windows reproduction were not separately tested. The kernel-only deployment wrapper was statically checked during packaging; the matched kernel/module bytes and application executables are unchanged from the recorded tested build.

The official OpenSTLinux SDK installer is a separately licensed build prerequisite, not one of the required submission binaries. The report provides its exact version and host-architecture selection. The original RPLIDAR SDK sources and their license notices are included under `lidar-lab/vendor/`.

## Project and authors

- **Project:** stm32mp257f-edge-ai-lab
- **Group:** 1
- **Student author order:** Mingkang Ma, Yuhao Zhang, Shuhan Ge, Yu Zhou, Mingyang Sun.
- **AI contributor:** Codex (OpenAI), credited separately.

The roster follows the order supplied by the project owner. The program's demonstration identity remains **mingkang ma / 523031910621**.

The first greeting is recorded as a kernel-origin journal entry. The GTK screen and compact evidence file show the selected greeting, not a complete boot transcript. See STEP 2 in the README for unfiltered kernel-log inspection. Native HDMI scrolling kernel boot text has not been configured; this documentation update does not change the programs or console settings.
