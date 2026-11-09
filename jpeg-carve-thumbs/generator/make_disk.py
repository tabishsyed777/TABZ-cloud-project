"""Deterministically builds environment/disk.img and tests/expected.json.
Not shipped to the agent. Run from the task root: python3 generator/make_disk.py"""
import io, json, hashlib, random
import numpy as np
from PIL import Image
import piexif

SEED = 20261109
rng = random.Random(SEED)
nrng = np.random.default_rng(SEED)
SECTOR = 512

def synth(w, h):
    y, x = np.mgrid[0:h, 0:w]
    base = np.stack([
        128 + 100*np.sin(x / rng.uniform(15, 40) + rng.random()*6),
        128 + 100*np.sin(y / rng.uniform(15, 40) + rng.random()*6),
        128 + 100*np.sin((x + y) / rng.uniform(20, 50)),
    ], -1)
    base += nrng.normal(0, 18, base.shape)
    return Image.fromarray(np.clip(base, 0, 255).astype("uint8"))

def make_jpeg(w, h, with_thumb):
    im = synth(w, h)
    kw = dict(format="JPEG", quality=rng.choice([80, 85, 90]))
    if with_thumb:
        t = im.copy(); t.thumbnail((160, 120))
        tb = io.BytesIO(); t.save(tb, "JPEG", quality=70)
        kw["exif"] = piexif.dump({"0th": {}, "Exif": {}, "GPS": {},
                                  "1st": {piexif.ImageIFD.Compression: 6},
                                  "thumbnail": tb.getvalue()})
    buf = io.BytesIO()
    im.save(buf, **kw)
    return buf.getvalue()

def junk(n, decoys=0):
    b = bytearray(nrng.integers(0, 256, n, dtype="uint8").tobytes())
    for _ in range(decoys):  # fake SOI markers that are NOT real files
        p = rng.randrange(0, max(1, n - 64))
        b[p:p+4] = b"\xff\xd8\xff\xe0"
    return bytes(b)

def pad(b):
    return b + b"\x00" * (-len(b) % SECTOR)

sizes = [(640, 480), (800, 600), (320, 240), (1024, 768),
         (480, 640), (700, 500), (900, 600), (400, 400)]
thumbs = [True, True, False, True, True, False, True, True]
files = [make_jpeg(w, h, t) for (w, h), t in zip(sizes, thumbs)]

# Decoy: a JPEG cut off mid-scan and overwritten (unrecoverable, must NOT be output)
full = make_jpeg(800, 600, True)
decoy = full[: len(full) // 2]

parts = [junk(SECTOR * rng.randint(4, 20), decoys=3)]
order = list(range(len(files)))
rng.shuffle(order)
expected = []
for k, idx in enumerate(order):
    if k == 3:
        parts += [pad(decoy), junk(SECTOR * rng.randint(2, 12), decoys=2)]
    data = files[idx]
    expected.append({"sha256": hashlib.sha256(data).hexdigest(), "size": len(data)})
    parts += [pad(data), junk(SECTOR * rng.randint(2, 30), decoys=2)]

img = b"".join(parts)
open("environment/disk.img", "wb").write(img)
json.dump({"count": len(expected), "files": expected},
          open("tests/expected.json", "w"), indent=2)
print("disk.img", len(img), "bytes;", len(expected), "files")
