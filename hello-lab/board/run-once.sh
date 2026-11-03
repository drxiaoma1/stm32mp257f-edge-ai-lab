#!/bin/sh
set -eu
umask 022
mkdir -p /run/hello-lab
status=0
/opt/hello-lab/hello_world > /run/hello-lab/output.tmp 2>&1 || status=$?
printf '\nExit status: %s\n' "$status" >> /run/hello-lab/output.tmp
chmod 644 /run/hello-lab/output.tmp
mv /run/hello-lab/output.tmp /run/hello-lab/output.txt
cat /run/hello-lab/output.txt
exit "$status"
