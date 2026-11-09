# JPEG Carving with Embedded Thumbnails

Terminal-Bench 3 / Harbor task prototype for recovering intact JPEGs from a raw disk image. The environment contains a deterministic, 1.3 MB disk image; the reference solution and exact-output verifier are included for maintainers.

## Task design

The image contains eight intact JPEG photos, random bytes with fake JPEG start markers, embedded EXIF thumbnails, and one truncated photo. Correct output must preserve exact original bytes, include no thumbnails or decoys, and leave the source image unchanged.

The oracle solution completed the included verifier in a local scratch run: it recovered all eight expected JPEGs and the disk hash remained unchanged. This was not a Harbor run. Harbor and Docker were unavailable in the authoring environment.

## Run with Harbor

From the task directory, after installing Harbor and Docker:

```bash
harbor check . -m anthropic/claude-opus-4-7
harbor run -p . --agent oracle
harbor run -p . --agent nop
```

The oracle should earn reward `1.0`; the no-op agent should earn `0.0`. Run at least one current frontier model and inspect the trajectory before claiming benchmark difficulty. Terminal-Bench 3 expects tasks to be meaningfully challenging, and this synthetic carving task may need a harder dataset or additional forensic requirements after calibration.

## Before contributing

- Set `metadata.author_email` in `task.toml` to the email you want associated with the submission.
- Confirm the task idea with Terminal-Bench maintainers before investing in a contribution.
- Run the repository's static checks, Harbor quality review, oracle run, and no-op run.
- Review the exact Terminal-Bench 3 template and rubric for changes before submission.

## Structure

- `instruction.md` — agent-facing task request
- `environment/` — Docker image definition and source disk image
- `solution/` — reference/oracle solution
- `tests/` — deterministic output and source-integrity verifier
- `generator/` — deterministic dataset generator for maintainers; it is not copied into the agent environment
- `task.toml` — Harbor runtime settings and task metadata

To rebuild the fixture from the task root, install `generator/requirements.txt` and run `python3 generator/make_disk.py`. Image encoding can vary across library versions, so compare the generated disk and expected hashes with the checked-in fixtures before replacing them.
