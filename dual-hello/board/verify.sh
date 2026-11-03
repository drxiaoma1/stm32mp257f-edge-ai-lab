#!/bin/sh
set -eu
out=/home/root/dual-hello-evidence
mkdir -p "$out"
cat /proc/sys/kernel/random/boot_id > "$out/boot-id.txt"
journalctl -b -k --no-pager -o json | python3 -c 'import sys,json; [print(line,end="") for line in sys.stdin if "[kernel] hello, world" in json.loads(line).get("MESSAGE","")]' > "$out/kernel.jsonl"
journalctl -b -u c1-demo --no-pager -o json | python3 -c 'import sys,json; [print(line,end="") for line in sys.stdin if json.loads(line).get("MESSAGE","").startswith("[user] hello, world")]' > "$out/user.jsonl"
cp /var/lib/c1-lab/latest/hello.txt "$out/hello.txt"
cp /var/lib/c1-lab/latest/state.json "$out/state.json"
{
    uname -a
    modinfo hello_kernel
    ls -l /dev/hello_kernel
    systemctl is-enabled hello-lab.service c1-demo.service
    systemctl show hello-lab.service -p ExecStart -p Result
    modinfo -F vermagic cp210x
    lsmod | grep -E "hello_kernel|cp210x|usbserial"
} > "$out/system.txt"
python3 - <<'PY'
import json,re
from pathlib import Path
p=Path('/home/root/dual-hello-evidence')
k=[json.loads(x) for x in (p/'kernel.jsonl').read_text().splitlines()]
u=[json.loads(x) for x in (p/'user.jsonl').read_text().splitlines()]
assert len(k)==len(u)==1,(len(k),len(u))
assert k[0]['_TRANSPORT']=='kernel'
assert u[0]['_TRANSPORT']=='stdout' and u[0]['_UID']=='1000'
assert int(k[0]['__MONOTONIC_TIMESTAMP'])<int(u[0]['__MONOTONIC_TIMESTAMP'])
s=json.loads((p/'state.json').read_text())
assert s['boot_id']==(p/'boot-id.txt').read_text().strip()
assert s['hello_exit_status']==0
assert s['student_name']=='mingkang ma' and s['student_id']=='523031910621'
text=(p/'hello.txt').read_text()
assert '[kernel] hello, world' in text and '[user] hello, world' in text
user_pid=re.search(r'User process PID: (\d+)',text)[1]
assert u[0]['MESSAGE'] in text
result={'boot_id':s['boot_id'],'kernel':s['kernel'],'kernel_transport':k[0]['_TRANSPORT'],
 'kernel_print_count':len(k),'kernel_print_uptime_s':int(k[0]['__MONOTONIC_TIMESTAMP'])/1e6,
 'user_transport':u[0]['_TRANSPORT'],'user_print_count':len(u),
 'user_print_uptime_s':int(u[0]['__MONOTONIC_TIMESTAMP'])/1e6,'user_pid':user_pid,'stdout_collector_pid':u[0]['_PID'],
 'user_uid':u[0]['_UID'],'hello_exit_status':s['hello_exit_status'],
 'lidar_phase':s['phase'],'lidar_error':s.get('error'),'hello_two_contexts_passed':True}
(p/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
PY
