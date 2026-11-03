# STM32MP257F-DK 边缘 AI 实验记录

mingkang ma · 523031910621

记录板卡刷机准备完成后的实验：终端控制、官方 OpenSTLinux SDK 交叉编译、自编译 Linux 内核与驱动、用户空间 Hello World、开机显示、C1 激光采集与点云显示。主线系统为 OpenSTLinux v25.06.11，自编译内核为 `6.6.78-gkc-sdk`。

## 阅读顺序

1. [SDK、Linux 内核与终端实验](docs/sdk/实验全流程.md)：从已刷好的板卡开始，配置 Linux 开发环境，使用官方 SDK 编译内核与用户程序，完成 WEEK6 终端演示。
2. [个人 Hello World 快速指导](hello-lab/快速实验指导.md)：修改姓名学号，经 Makefile 编译、部署，在屏幕显示并配置自启动。
3. [C1 SDK 和点云实验](lidar-lab/实验指导.md)：识别 CP210x 串口，交叉编译官方 SDK，使用命令控制 C1、采集并保存二维点云。
4. [Hello World → 10 秒扫描 → 点云屏幕显示](lidar-lab/boot-demo/README.md)：系统驱动安装、连续演示与开机服务。
5. `dual-hello/`：2026-11-03 新增的内核驱动打印与用户空间打印。源码已使用官方 SDK 编译，已在板卡分别运行；正在验证自动启动。实验者确认后再更新推荐手册。

## 目录

- `docs/sdk/`：完整历史手册、内核配置、构建日志、截图。
- `hello-lab/src/`、`hello-lab/board/`：可修改的 Hello World、Makefile、部署与启动脚本。
- `scripts/`：官方 SDK 内核、GPU 和 WEEK6 构建/演示脚本。
- `lidar-lab/src/`：支持按圈数和按时间采集的 C1 用户程序。
- `lidar-lab/vendor/rplidar_sdk/`：官方 RPLIDAR SDK 源码，保留原许可证。
- `lidar-lab/data/`、`lidar-lab/runs/`：真实测量数据与分析结果。
- `lidar-lab/boot-demo/board/`：板卡本地绘图、屏幕显示和 systemd 配置。
- `dual-hello/kernel/`、`dual-hello/user/`：分别在内核空间、用户空间打印的新增代码。

## 使用边界与验收状态

仓库保存源码、脚本、手册和关键实验记录；不提交账号凭据、ST 邮件下载链接、原课件或大型 SDK 安装器。文档中的离线压缩包指此前单独交付的实验包，不作为 Git 仓库内文件；在这里复现应先依照手册安装官方 SDK 并编译源码。

macOS 使用 ARM Ubuntu 虚拟机和 ARM 主机版 SDK；Windows 的 x86_64 Ubuntu 使用 x86 主机版 SDK。目标均为板卡 AArch64。Windows 完整流程尚未在该系统实机逐步验证。

早期 Hello World 已完成真实断电上电验证。C1 连续显示已通过软件重启和指令运行，但物理断电上电验收在 2026-10-27 按实验者要求暂缓。具体证据和限制见各阶段的验收记录，不能互相替代。

本仓库在 2026-11-03 从已有实验文件整理建立；Git 提交时间是整理时间，原实验发生时间以原始日志、启动编号和记录说明为准。
