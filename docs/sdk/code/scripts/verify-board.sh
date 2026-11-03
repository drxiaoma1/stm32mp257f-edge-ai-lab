#!/bin/sh
# Run as root on the target after a reboot or a documented physical power cycle.
set -eu
expected=${EXPECTED_KERNEL:-6.6.78-gkc-sdk}
printf 'HOST: '; hostname
printf 'KERNEL: '; uname -r
test "$(uname -r)" = "$expected"
printf 'ARCHITECTURE: '; uname -m
printf 'BOOT_ID: '; cat /proc/sys/kernel/random/boot_id
printf 'UPTIME: '; cat /proc/uptime
printf '\nMANUAL PROGRAM RUN\n'
/usr/local/bin/hello_world
program_status=$?
printf 'PROGRAM_EXIT_STATUS: %s\n' "$program_status"
printf '\nBOOT SERVICE CONFIGURATION AND RESULT\n'
systemctl is-enabled hello-world.service
systemctl is-active hello-world.service
systemctl show hello-world.service -p Result -p ExecMainStatus -p ExecMainStartTimestampMonotonic
test "$(systemctl show hello-world.service -p Result --value)" = success
test "$(systemctl show hello-world.service -p ExecMainStatus --value)" = 0
printf '\nCURRENT BOOT SERVICE JOURNAL\n'
journalctl -b -u hello-world.service --no-pager -o cat
journalctl -b -u hello-world.service --no-pager -o cat | grep -F "Running kernel: $expected"
journalctl -b -u hello-world.service --no-pager -o cat | grep -F 'Student: mingkang ma'
journalctl -b -u hello-world.service --no-pager -o cat | grep -F 'Student ID: 523031910621'
printf '\nDISPLAY SESSION\n'
systemctl is-active weston-graphical-session.service
cat /sys/class/drm/card0-HDMI-A-1/modes
printf '\nVerification completed successfully.\n'
