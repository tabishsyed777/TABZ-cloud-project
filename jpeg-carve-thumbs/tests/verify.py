import hashlib, json, os, sys

OUT = "/app/recovered"
exp = json.load(open("/tests/expected.json"))
want = {f["sha256"] for f in exp["files"]}

def fail(msg):
    print("FAIL:", msg); sys.exit(1)

if not os.path.isdir(OUT):
    fail("/app/recovered does not exist")

names = sorted(os.listdir(OUT))
if any(not n.lower().endswith(".jpg") for n in names):
    fail("non-.jpg file present: " + str([n for n in names if not n.lower().endswith('.jpg')]))

got = {}
for n in names:
    p = os.path.join(OUT, n)
    if not os.path.isfile(p):
        fail(f"{n} is not a regular file")
    got.setdefault(hashlib.sha256(open(p, "rb").read()).hexdigest(), []).append(n)

extra = [h for h in got if h not in want]
if extra:
    fail(f"{len(extra)} output file(s) are not exact originals (junk, decoys, thumbnails or padded/truncated): "
         + str([got[h] for h in extra]))
dups = [v for v in got.values() if len(v) > 1]
if dups:
    fail("duplicate outputs: " + str(dups))
missing = want - set(got)
if missing:
    fail(f"{len(missing)} of {len(want)} photos not recovered")

# disk.img must be untouched
if hashlib.sha256(open("/app/disk.img", "rb").read()).hexdigest() != open("/tests/disk.sha256").read().strip():
    fail("disk.img was modified")

print("PASS: all", len(want), "photos recovered exactly")
