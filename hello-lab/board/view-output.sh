#!/bin/sh
printf '\033[2J\033[H\033[1;36mHELLO WORLD | MY STM32MP257F-DK\033[0m\n\n'
cat /run/hello-lab/output.txt
printf '\nThis window displays the program result from this boot.\n'
printf 'Close this window or press Enter to return to the desktop.\n'
read -r unused || true
