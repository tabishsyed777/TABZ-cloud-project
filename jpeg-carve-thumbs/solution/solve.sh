#!/bin/bash
set -euo pipefail
python3 - <<'PY'
import os

DISK = "/app/disk.img"
OUT = "/app/recovered"
os.makedirs(OUT, exist_ok=True)
data = open(DISK, "rb").read()
n = len(data)

def parse_jpeg(buf, start):
    """Walk JPEG markers from `start`; return end offset (exclusive) or None if invalid/truncated."""
    i = start
    if buf[i:i+2] != b"\xff\xd8":
        return None
    i += 2
    while True:
        if i + 4 > len(buf) or buf[i] != 0xFF:
            return None
        m = buf[i + 1]
        if m == 0xFF:            # fill byte
            i += 1
            continue
        if m == 0xDA:            # SOS: header then entropy-coded data
            seglen = int.from_bytes(buf[i+2:i+4], "big")
            i += 2 + seglen
            while True:          # scan entropy data for next real marker
                j = buf.find(b"\xff", i)
                if j == -1 or j + 1 >= len(buf):
                    return None
                nxt = buf[j + 1]
                if nxt == 0x00 or 0xD0 <= nxt <= 0xD7:
                    i = j + 2    # stuffed byte or restart marker
                elif nxt == 0xD9:
                    return j + 2
                elif nxt == 0xFF:
                    i = j + 1
                else:
                    i = j        # another segment (progressive JPEG): parse it
                    break
            continue
        if m in (0xD8, 0x01) or 0xD0 <= m <= 0xD7:
            i += 2
            continue
        seglen = int.from_bytes(buf[i+2:i+4], "big")
        if seglen < 2:
            return None
        i += 2 + seglen          # skips APP1/EXIF whole, including embedded thumbnail

count = 0
pos = 0
while True:
    s = data.find(b"\xff\xd8\xff", pos)
    if s == -1:
        break
    if s % 512 == 0:
        e = parse_jpeg(data, s)
        if e is not None:
            count += 1
            open(f"{OUT}/photo_{count:02d}.jpg", "wb").write(data[s:e])
            pos = e
            continue
    pos = s + 1
print("recovered", count)
PY
