#!/bin/sh
printf '\033[2J\033[H'
printf 'STM32MP257F-DK | LIVE BOARD VERIFICATION\n\n'
printf '$ uname -r\n'
uname -r
printf '\n$ /usr/local/bin/hello_world\n'
/usr/local/bin/hello_world
status=$?
printf '\nProgram exit status: %s\n' "$status"
printf '\n$ systemctl is-active weston-graphical-session\n'
systemctl is-active weston-graphical-session
printf '\nThis output is running on the physical board.\n'
read -r unused
