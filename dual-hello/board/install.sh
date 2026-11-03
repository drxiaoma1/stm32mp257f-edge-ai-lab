#!/bin/sh
set -eu
cd "$(dirname "$0")"
test "$(id -u)" = 0
test "$(uname -r)" = 6.6.78-gkc-sdk
sha256sum -c SHA256SUMS
case "$(modinfo -F vermagic hello_kernel.ko)" in
  '6.6.78-gkc-sdk '*) ;;
  *) echo 'Module and running kernel do not match.' >&2;exit 1;;
esac
test -x /opt/hello-lab/hello_world
test -f /etc/systemd/system/c1-demo.service
backup=$(mktemp -d /home/root/dual-hello-backup.XXXXXX)
cp -p /opt/hello-lab/hello_world "$backup/hello_world.before"
systemctl cat hello-lab.service > "$backup/hello-lab.service.before"
sha256sum /opt/c1-lab/c1_capture /opt/c1-lab/c1_demo.py /opt/c1-lab/render_pointcloud.py /opt/c1-lab/start-demo.sh /etc/systemd/system/c1-demo.service > "$backup/c1-before.sha256"
for old in /etc/systemd/system/hello-lab.service.d/10-kernel-before-user.conf /etc/modules-load.d/hello-kernel.conf; do
    if [ -f "$old" ];then cp -p "$old" "$backup/";fi
done
systemctl stop c1-demo.service
install -d /lib/modules/6.6.78-gkc-sdk/extra /etc/systemd/system/hello-lab.service.d /etc/modules-load.d
install -m 644 hello_kernel.ko /lib/modules/6.6.78-gkc-sdk/extra/
install -m 755 hello_world /opt/hello-lab/hello_world
install -m 644 hello-kernel.conf /etc/modules-load.d/
install -m 644 10-kernel-before-user.conf /etc/systemd/system/hello-lab.service.d/
depmod -a
systemctl daemon-reload
systemctl restart hello-lab.service
systemctl enable hello-lab.service c1-demo.service
test -c /dev/hello_kernel
sha256sum -c "$backup/c1-before.sha256"
printf 'Installed. Backup: %s\n' "$backup"
printf 'Kernel message, read back from driver:\n'
cat /dev/hello_kernel
printf 'Start the existing display/scan sequence with: c1ctl start\n'
