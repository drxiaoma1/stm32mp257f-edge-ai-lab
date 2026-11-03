#!/bin/sh
# ST's launcher destroys its temporary modal backdrop after this script exits.
# Activate afterward so that backdrop teardown cannot cover the live window.
(
    sleep 1
    exec /opt/c1-lab/open-c1-app.sh --manual
) </dev/null >/dev/null 2>&1 &
exit 0
