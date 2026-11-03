#!/bin/sh
set -eu
cd "$(dirname "$0")"
test "$(id -u)" = 0 || { echo 'Run on the board as root.' >&2; exit 1; }
test "$(uname -m)" = aarch64 || { echo 'This package is for the AArch64 board.' >&2; exit 1; }
grep -aq 'STM32MP257F-DK' /proc/device-tree/model || { echo 'Wrong board model.' >&2; exit 1; }
for cmd in systemctl sha256sum weston-terminal install; do command -v "$cmd" >/dev/null; done
id weston >/dev/null
systemctl cat weston-graphical-session.service >/dev/null
sha256sum -c SHA256SUMS

backup=$(mktemp -d /home/root/hello-lab-backup.XXXXXX)
if [ -d /opt/hello-lab ]; then cp -a /opt/hello-lab "$backup/"; fi
for unit in hello-lab.service hello-lab-screen.service; do
    if [ -f "/etc/systemd/system/$unit" ]; then
        cp -p "/etc/systemd/system/$unit" "$backup/"
        systemctl is-enabled "$unit" > "$backup/$unit.enabled" || true
        systemctl stop "$unit"
    fi
done
install -d -m 755 /opt/hello-lab
install -m 755 hello_world run-once.sh open-screen.sh view-output.sh /opt/hello-lab/
install -m 644 hello-lab.service hello-lab-screen.service /etc/systemd/system/
systemctl daemon-reload
# Show once immediately; enabling automatic startup is a separate manual step.
systemctl restart hello-lab.service
systemctl restart hello-lab-screen.service
systemctl show hello-lab.service -p Result -p ExecMainStatus
printf '\nInstalled. The HDMI window should appear after Weston is ready.\nBackup: %s\n' "$backup"
printf 'Enable at boot: systemctl enable hello-lab.service hello-lab-screen.service\n'
