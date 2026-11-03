#!/bin/sh
set -eu
test "$(uname -r)" = "${EXPECTED_KERNEL:-6.6.78-gkc-sdk}"
evidence=/home/root/gkc-evidence
mkdir -p "$evidence"
cp -p /etc/default/weston "$evidence/weston-default.before"
restore() {
    cp -p "$evidence/weston-default.before" /etc/default/weston
    systemctl restart weston-graphical-session
}
trap restore EXIT
. /etc/default/weston
printf '\nOPTARGS="%s --debug"\n' "${OPTARGS:-}" >> /etc/default/weston
systemctl restart weston-graphical-session
sleep 12
export XDG_RUNTIME_DIR=/run/user/1000 WAYLAND_DISPLAY=wayland-0
capture() {
    # A fresh directory avoids selecting an older file when the RTC resets.
    capture_dir=$(mktemp -d /home/weston/gkc-capture.XXXXXX)
    chown weston:weston "$capture_dir"
    su -s /bin/sh weston -c "cd '$capture_dir'; XDG_RUNTIME_DIR=/run/user/1000 WAYLAND_DISPLAY=wayland-0 weston-screenshooter"
    set -- "$1" "$capture_dir"/wayland-screenshot-*.png
    test "$#" = 2
    test -f "$2"
    cp "$2" "$evidence/$1.png"
    rm "$2"
    rmdir "$capture_dir"
}
capture desktop
chmod 755 /home/root/display-hello-demo.sh /home/root/display-autostart-demo.sh
weston-terminal --maximized --font-size=15 --shell=/home/root/display-hello-demo.sh >"$evidence/terminal-hello.log" 2>&1 &
terminal_pid=$!
sleep 7
capture hello-screen
kill "$terminal_pid"
sleep 1
weston-terminal --maximized --font-size=13 --shell=/home/root/display-autostart-demo.sh >"$evidence/terminal-autostart.log" 2>&1 &
terminal_pid=$!
sleep 3
capture autostart-screen
kill "$terminal_pid"
printf 'Captured desktop, hello-screen, autostart-screen.\n'
