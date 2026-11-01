"""Create, inspect, and safely extract small deterministic archives."""
from __future__ import annotations

import hashlib
import io
import tarfile
import tempfile
import zipfile
from pathlib import Path

import fullseye as fs


def main():
    truth = {"measurements/run.txt": b"x_mm,y_mm\n1.25,-0.50\n",
             "readme.txt": "Fullseye archive round-trip\n".encode()}
    measured = []
    for fmt in ("zip", "tar", "tar.gz", "tar.xz"):
        first = fs.archive_create(truth, fmt, deterministic=True)
        second = fs.archive_create(truth, fmt, deterministic=True)
        assert hashlib.sha256(first).digest() == hashlib.sha256(second).digest()
        assert fs.archive_probe(first) == fmt
        rows = fs.archive_list(first)
        assert {row["name"] for row in rows} == set(truth)

        # Independent standard-library readers verify the bytes, not Fullseye itself.
        if fmt == "zip":
            with zipfile.ZipFile(io.BytesIO(first)) as archive:
                independent = {name: archive.read(name) for name in archive.namelist()}
        else:
            with tarfile.open(fileobj=io.BytesIO(first), mode="r:*") as archive:
                independent = {member.name: archive.extractfile(member).read()
                               for member in archive.getmembers() if member.isfile()}
        assert independent == truth

        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "out"
            extracted = fs.archive_extract(first, output)
            assert set(extracted) == set(truth)
            assert {name: (output / name).read_bytes() for name in extracted} == truth
        measured.append(f"{fmt}={len(first)} bytes")
    print("PASS: deterministic create -> independent read -> safe extract; " + ", ".join(measured))


if __name__ == "__main__":
    main()
