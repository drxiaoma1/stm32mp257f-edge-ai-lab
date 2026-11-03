#!/bin/sh
set -eu
export XDG_RUNTIME_DIR=/run/user/$(id -u)
export WAYLAND_DISPLAY=wayland-0
export DBUS_SESSION_BUS_ADDRESS=unix:path=$XDG_RUNTIME_DIR/bus
if [ "$#" = 0 ]; then set -- --home; fi
exec /usr/bin/python3 /opt/c1-lab/c1_demo.py "$@"
