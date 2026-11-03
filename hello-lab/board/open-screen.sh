#!/bin/sh
set -eu
export XDG_RUNTIME_DIR="/run/user/$(id -u)"
export WAYLAND_DISPLAY=wayland-0
count=0
while [ ! -S "$XDG_RUNTIME_DIR/$WAYLAND_DISPLAY" ] || [ ! -r /run/hello-lab/output.txt ]; do
    count=$((count + 1))
    if [ "$count" -ge 90 ]; then
        echo 'Weston socket or Hello World output was not ready within 90 seconds.' >&2
        exit 1
    fi
    sleep 1
done
# The ST demo launcher appears shortly after the compositor starts. Let it settle
# before opening the result window so it does not cover the Hello World output.
sleep 12
exec weston-terminal --maximized --font-size=18 --shell=/opt/hello-lab/view-output.sh
