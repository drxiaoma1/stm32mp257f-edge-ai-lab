# C1 touch application — current revision (2026-11-03)

The kernel provides `usbserial`, `cp210x`, and the separate `hello_kernel` greeting module. Both LiDAR acquisition modes run in user space on Linux `6.6.78-gkc-sdk`.

1. After boot, the screen shows the kernel and user Hello World messages and the demonstration identity.
2. One automatic scan collects for 10 seconds and stops. Initialization and rendering add approximately 5 seconds.
3. Tap **Home** to return to the application home page.
4. Tap **Start scanning**, or the **C1 Lidar / Live scan** icon on the ST launcher, for continuous scanning. The newest measured revolution is displayed about once per second.
5. Tap **Stop** to stop and preserve the final image. Tap **Home** afterward, or **Desktop** to return to the ST launcher.

An empty revolution is displayed as having no valid returns; it does not terminate a live session. Serial transport failures still produce an error and release the device. Synthetic regression-test input is never shown as sensor measurements.

Automatic scans save the complete CSV. Continuous sessions retain the latest eight displayed revolutions, a final CSV/PNG, and whole-session counters in `session.json`; they do not archive an unbounded stream. Automatic and manual collectors share a serial lock. Restarting the application in the same boot does not repeat the boot scan or Hello World.

## Build and installation

Use the official OpenSTLinux SDK and the matched completed kernel build. See the repository's English README for the full environment, kernel, Hello World, `insmod`, build and deployment procedure. `package.py` creates the board archive from `board/` and the compiled programs/modules in `output/`.

The final submission ZIP includes `install-board.sh`, matching kernel images, greeting binaries, C1 binaries, source, Makefiles and deployment packages. The standalone C1 installer expects the Hello World executable and matching kernel modules to be present; the submission installer handles their order.

## Commands

```sh
c1ctl home       # show the application home page
c1ctl scan       # begin continuous live acquisition
c1ctl status     # inspect the service and latest completed result
c1ctl result     # print the latest completed result directory
c1ctl stop       # stop the application and any active acquisition
c1ctl start      # reopen the service; same-boot startup is not repeated
```

Raw results are under `/var/lib/c1-lab/boots/<boot-id>/automatic/` and `/var/lib/c1-lab/runs/`. The `latest` symlink changes only after a successful completed scan.

## Verification boundary

Current evidence is under `evidence/touch-app/`. It records the two greeting contexts, real `insmod`, software-reboot automatic scanning, touch navigation, continuous scanning, and the reported empty-frame failure followed by its regression fix. A physical cold-power-cycle test of this exact revision is still separate from software-reboot verification. The board wall clock is unsynchronized; use boot IDs and monotonic uptime.

Earlier Chinese guides and 2026-10-27 captures describe the previous interface. This revision supersedes their one-shot manual behavior.
