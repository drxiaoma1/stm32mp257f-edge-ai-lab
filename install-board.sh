#!/bin/sh
# Install the current assessed application on the already rebuilt kernel.
set -eu
cd "$(dirname "$0")"
test "$(id -u)" = 0 || { echo 'Run as root on the board.' >&2; exit 1; }
test "$(uname -r)" = 6.6.78-gkc-sdk || { echo 'Deploy and boot the matching kernel first.' >&2; exit 1; }
sha256sum -c SHA256SUMS
backup=$(mktemp -d /home/root/midterm-install-backup.XXXXXX)
for path in /opt/hello-lab/hello_world /etc/systemd/system/hello-lab.service; do
    if [ -f "$path" ]; then cp -p "$path" "$backup/"; fi
done
systemctl stop c1-demo.service 2>/dev/null || true
systemctl disable --now hello-world.service hello-lab-screen.service 2>/dev/null || true
install -d /opt/hello-lab
install -m 755 artifacts/hello/hello_world /opt/hello-lab/hello_world
cat > /etc/systemd/system/hello-lab.service <<'UNIT'
[Unit]
Description=Load kernel greeting before the user-space touch application
After=systemd-modules-load.service
[Service]
Type=oneshot
ExecStart=/sbin/modprobe hello_kernel
ExecStart=/bin/sh -c 'test -c /dev/hello_kernel'
RemainAfterExit=yes
[Install]
WantedBy=multi-user.target
UNIT
stage=$(mktemp -d /home/root/midterm-install.XXXXXX)
tar -xzf packages/c1-boot-demo.tar.gz -C "$stage"
tar -xzf packages/dual-hello-deploy.tar.gz -C "$stage"
sh "$stage/c1-boot-demo/install.sh"
sh "$stage/dual-hello-deploy/install.sh"
sync
printf 'Installed. Backup: %s\nReboot to run the complete startup sequence.\n' "$backup"
