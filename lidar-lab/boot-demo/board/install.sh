#!/bin/sh
set -eu
cd "$(dirname "$0")"
test "$(id -u)" = 0 || { echo 'Run as root on the board.' >&2;exit 1; }
test "$(uname -r)" = 6.6.78-gkc-sdk || { echo 'These kernel modules require 6.6.78-gkc-sdk.' >&2;exit 1; }
test -x /opt/hello-lab/hello_world
id weston >/dev/null
python3 -c 'import cairo,gi;gi.require_version("Gtk","3.0");from gi.repository import Gtk'
sha256sum -c SHA256SUMS
for module in cp210x.ko usbserial.ko; do
    case "$(modinfo -F vermagic "$module")" in '6.6.78-gkc-sdk '*) ;; *) echo 'Module/kernel mismatch' >&2;exit 1;; esac
done
backup=$(mktemp -d /home/root/c1-demo-backup.XXXXXX)
systemctl is-enabled hello-lab-screen.service > "$backup/hello-screen.enabled" || true
systemctl is-enabled c1-demo.service > "$backup/c1-demo.enabled" || true
if [ -d /opt/c1-lab ]; then cp -a /opt/c1-lab "$backup/"; fi
for path in /etc/systemd/system/c1-demo.service /etc/udev/rules.d/99-c1-lidar.rules /etc/modules-load.d/c1-lidar.conf; do
    if [ -f "$path" ]; then cp -p "$path" "$backup/"; fi
done
systemctl stop c1-demo.service 2>/dev/null || true
systemctl disable --now hello-lab-screen.service 2>/dev/null || true
install -d /opt/c1-lab /etc/modules-load.d /etc/udev/rules.d
install -m 755 c1_capture c1_live c1_demo.py render_pointcloud.py start-demo.sh open-c1-app.sh /opt/c1-lab/
install -m 644 style.css c1-icon.png /opt/c1-lab/
install -d /usr/local/demo/application/c1-lidar /usr/share/applications
install -m 644 c1-icon.png /usr/local/demo/application/c1-lidar/
install -m 755 start-live.sh /usr/local/demo/application/c1-lidar/
install -m 644 050-c1-lidar.yaml /usr/local/demo/gtk-application/
install -m 644 c1-lidar.desktop /usr/share/applications/
install -m 755 c1ctl /usr/bin/c1ctl
install -m 644 c1-demo.service /etc/systemd/system/
install -m 644 c1-lidar.conf /etc/modules-load.d/
install -m 644 99-c1-lidar.rules /etc/udev/rules.d/
if [ -n "${C1_USB_SERIAL:-}" ]; then
    case "$C1_USB_SERIAL" in *[!a-zA-Z0-9_-]*) echo 'Invalid C1_USB_SERIAL' >&2;exit 1;; esac
    sed "s/ATTRS{serial}==\"[^\"]*\"/ATTRS{serial}==\"$C1_USB_SERIAL\"/" 99-c1-lidar.rules > /etc/udev/rules.d/99-c1-lidar.rules
fi
module_dir=/lib/modules/6.6.78-gkc-sdk/kernel/drivers/usb/serial
cp -p "$module_dir/cp210x.ko" "$module_dir/usbserial.ko" "$backup/"
install -m 644 cp210x.ko usbserial.ko "$module_dir/"
depmod -a
modprobe cp210x
udevadm control --reload-rules
udevadm trigger --subsystem-match=tty --action=add
udevadm settle
test -c /dev/c1lidar
systemctl daemon-reload
systemctl enable hello-lab.service c1-demo.service
printf 'Installed. Backup: %s\n' "$backup"
printf 'Driver: ';modinfo -F vermagic cp210x
printf 'C1: ';ls -l /dev/c1lidar
printf 'Start now: c1ctl start\n'
