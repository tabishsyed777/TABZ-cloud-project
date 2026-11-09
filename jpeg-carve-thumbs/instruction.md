# Recover photos from a damaged disk image

A print shop's storage card was wiped by accident. A raw dump of it is at `/app/disk.img`. The filesystem is gone, but several JPEG photos are still sitting in the raw bytes between unrelated data.

Recover the photos and write each one as a separate file into `/app/recovered/` (create the directory). Use any file names you like, as long as they end in `.jpg`.

Requirements:

- Recover every photo that is fully intact.
- Each recovered file must be byte-for-byte identical to the original photo: it starts at the photo's first byte (`FF D8`) and ends at its last byte (`FF D9`), with no leading or trailing padding or junk.
- Some photos were partly overwritten and cannot be recovered. Do not output those, and do not output anything else that is not a complete photo.
- Do not modify `/app/disk.img`.

Be careful: the disk contains random data that happens to look like the start of a JPEG, and some photos contain smaller JPEGs inside them (embedded preview thumbnails).
