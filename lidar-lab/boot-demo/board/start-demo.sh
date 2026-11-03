#!/bin/sh
set -eu
export XDG_RUNTIME_DIR=/run/user/$(id -u)
export WAYLAND_DISPLAY=wayland-0
export DBUS_SESSION_BUS_ADDRESS=unix:path=$XDG_RUNTIME_DIR/bus
count=0
while [ ! -S "$XDG_RUNTIME_DIR/$WAYLAND_DISPLAY" ]; do
    count=$((count+1));test "$count" -lt 90 || exit 1
    sleep 1
done
# Allow ST's demo launcher to finish opening before taking the foreground.
sleep 12
exec /usr/bin/python3 /opt/c1-lab/c1_demo.py
