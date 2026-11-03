#!/bin/sh
export SYSTEMD_PAGER=cat SYSTEMD_COLORS=0
printf '\033[2J\033[H'
printf 'STM32MP257F-DK | COLD BOOT AUTOSTART EVIDENCE\n\n'
printf 'Kernel: '; uname -r
printf 'Boot ID: '; cat /proc/sys/kernel/random/boot_id
printf '\n$ systemctl is-enabled hello-world\n'
systemctl is-enabled hello-world
printf '\n$ systemctl show hello-world -p Result -p ExecMainStatus\n'
systemctl show hello-world --no-pager -p Result -p ExecMainStatus
printf '\n$ journalctl -b -u hello-world -o cat\n'
journalctl -b -u hello-world --no-pager -o cat
read -r unused
