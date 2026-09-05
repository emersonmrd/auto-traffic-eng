#!/bin/bash

# Gera licenca Cisco IOU oficial automatica
python3 - << 'PYEOF'
import os
import struct
import hashlib

hostname = os.uname().nodename
try:
    hostid = int(os.popen("hostid").read().strip(), 16)
except Exception:
    hostid = 0

ioukey = int(hostid)
for x in hostname:
    ioukey = ((ioukey << 2) + ord(x)) & 0xFFFFFFFF

# Cisco IOU Secret Pad
ioupad = bytes.fromhex('4b582181567b0df321439b7eac1de68a')
key = hashlib.md5(struct.pack('!I', ioukey) + ioupad).hexdigest()[:16]

lic_content = f"[license]\n{hostname} = {key};\n"

# Grava nos locais padrao
for path in ['/tmp/iourc', '/root/.iourc', '/iol/.iourc', '/etc/iourc', '/etc/cisco/iourc']:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            f.write(lic_content)
    except Exception:
        pass
PYEOF

export IOURC=/tmp/iourc

echo "Launching Cisco IOL with PID" ${IOL_PID:-1}

# Clear ip addressing on eth0
ip addr flush dev eth0 2>/dev/null || true
ip -6 addr flush dev eth0 2>/dev/null || true

echo "Flushed eth0 addresses"

sleep 2

# Run IOUYAP
/usr/bin/iouyap 513 -q &

# Get highest eth interface
max_eth=$(ls /sys/class/net | grep eth | grep -o -E '[0-9]+' | sort -n | tail -1)
num_slots=$(( (max_eth + 4) / 4 ))

# Start Cisco IOL
exec /iol/iol.bin ${IOL_PID:-1} -e $num_slots -s 0 -c config.txt -n 1024
