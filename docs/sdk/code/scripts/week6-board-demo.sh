#!/bin/sh
# Run through SSH on the board; collect genuine compositor screenshots.
set -eu
work=/home/root/gkc-week6
mkdir -p "$work"
cp -p /etc/default/weston "$work/weston-default.before"
demo_pid=
restore() {
    if [ -n "$demo_pid" ]; then kill "$demo_pid" 2>/dev/null || true; fi
    cp -p "$work/weston-default.before" /etc/default/weston
    systemctl restart weston-graphical-session
}
trap restore EXIT HUP INT TERM
set -x
uname -a
ip -4 addr show usb0
systemctl stop weston-graphical-session
systemctl is-active weston-graphical-session || true
systemctl start weston-graphical-session
systemctl is-active weston-graphical-session
set +x
# Preserve any existing Weston options while temporarily allowing screenshots.
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
    cp "$2" "$work/$1.png"
    rm "$2"
    rmdir "$capture_dir"
}
set -x
weston-image /home/root/week6-test-pattern.png >"$work/image.log" 2>&1 &
demo_pid=$!
sleep 3
capture image
kill "$demo_pid"
wait "$demo_pid" || true
demo_pid=
if [ "${WEEK6_SCOPE:-all}" = image ]; then
    printf 'WEEK6 image demonstration completed.\n'
    exit 0
fi
weston-simple-egl -f >"$work/egl.log" 2>&1 &
demo_pid=$!
sleep 6
capture egl
sleep 2
capture egl-second-frame
kill -INT "$demo_pid"
wait "$demo_pid" || true
demo_pid=
su -s /bin/sh weston -c 'timeout -s INT 14 gst-play-1.0 /usr/local/demo/media/ST2297_visionv3.webm --audiosink="fakesink sync=true" --no-interactive' >"$work/video.log" 2>&1 &
demo_pid=$!
sleep 7
capture video
sleep 5
# The timeout sends SIGINT to this test's player after fourteen seconds.
video_status=0
wait "$demo_pid" || video_status=$?
printf 'Video test exit status: %s (124 means the planned timeout)\n' "$video_status"
demo_pid=
cat "$work/egl.log"
tr '\r' '\n' < "$work/video.log" | tail -12
set +x
printf 'WEEK6 image, GPU, video, service control and screenshot demonstration completed.\n'
