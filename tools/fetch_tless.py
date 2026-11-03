# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Download the minimal BOP T-LESS data used by ``poc_real_tless_6dof``.

The dataset is kept outside the repository.  By default it is stored in
``~/fullseye_data/tless``; set ``FULLSEYE_TLESS_DATA`` to use another
directory.  Every archive is checked against the SHA-256 advertised for the
corresponding LFS object in the official ``bop-benchmark/tless`` repository.

Dataset licence: Creative Commons Attribution 4.0 International (CC BY 4.0).
Primary source and download instructions: https://bop.felk.cvut.cz/datasets/
Files: https://huggingface.co/datasets/bop-benchmark/tless
Paper: Hodaň et al., "T-LESS: An RGB-D Dataset for 6D Pose Estimation of
Texture-less Objects", WACV 2017, https://doi.org/10.1109/WACV.2017.8

Usage::

    py -3.11 tools/fetch_tless.py
    py -3.11 tools/fetch_tless.py --verify-only
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import urllib.request
import zipfile


BASE_URL = "https://huggingface.co/datasets/bop-benchmark/tless/resolve/main"
DEFAULT_DIR = Path(os.environ.get("FULLSEYE_TLESS_DATA") or (Path.home() / "fullseye_data" / "tless"))
ARCHIVES = {
    "tless_base.zip": {
        "bytes": 49_597,
        "sha256": "dd70ca884b7c471a530a952f70c5ab2c212f3d2c2f371be86397442b97d70a7e",
        "extract": "parent",
    },
    "tless_models.zip": {
        "bytes": 33_468_762,
        "sha256": "6a29c59766b8d2af05e62e71739f0ca7243ad81bc3c7f9a24925504a8cb37928",
        "extract": "dataset",
    },
    "tless_test_primesense_bop19.zip": {
        "bytes": 825_276_992,
        "sha256": "1a18f6bbfb5ac4ced8529f7a35225adfed88c0f62ef38067933e2b541ef1d00b",
        "extract": "dataset",
    },
}

LICENCE_TEXT = """T-LESS dataset provenance and licence
=====================================

Licence: Creative Commons Attribution 4.0 International (CC BY 4.0)
Licence URL: https://creativecommons.org/licenses/by/4.0/
Primary licence statement: https://bop.felk.cvut.cz/datasets/ (T-LESS section)
Distribution: https://huggingface.co/datasets/bop-benchmark/tless

Required attribution / citation:
Hodaň, Tomáš; Haluza, Pavel; Obdržálek, Štěpán; Matas, Jiří; Lourakis,
Manolis; Zabulis, Xenophon. T-LESS: An RGB-D Dataset for 6D Pose Estimation
of Texture-less Objects. WACV 2017. https://doi.org/10.1109/WACV.2017.8

BOP format / benchmark citation:
Hodaň et al. BOP Challenge 2020 on 6D Object Localization.
https://doi.org/10.1007/978-3-030-68223-0_12
"""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _download(url: str, destination: Path, expected_bytes: int) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "Fullseye-TLESS-PoC/1.0"})
    with tempfile.NamedTemporaryFile(
            prefix=destination.name + ".", suffix=".part",
            dir=destination.parent, delete=False) as temp:
        temporary = Path(temp.name)
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                shutil.copyfileobj(response, temp, length=8 * 1024 * 1024)
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
    actual_bytes = temporary.stat().st_size
    if actual_bytes != expected_bytes:
        temporary.unlink(missing_ok=True)
        raise RuntimeError(
            f"downloaded size mismatch for {destination.name}: "
            f"{actual_bytes} != {expected_bytes}")
    temporary.replace(destination)


def _safe_extract(archive: Path, destination: Path) -> None:
    root = destination.resolve()
    with zipfile.ZipFile(archive) as zipped:
        for member in zipped.infolist():
            target = (destination / member.filename).resolve()
            if target != root and root not in target.parents:
                raise RuntimeError(f"unsafe archive path: {member.filename!r}")
        zipped.extractall(destination)


def fetch(root: Path, *, verify_only: bool = False, no_extract: bool = False) -> dict:
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    records = []
    for name, expected in ARCHIVES.items():
        path = root / name
        if not path.exists():
            if verify_only:
                raise FileNotFoundError(path)
            print(f"download {name} ({expected['bytes'] / 1e6:.1f} MB)", flush=True)
            _download(f"{BASE_URL}/{name}", path, int(expected["bytes"]))
        size = path.stat().st_size
        digest = _sha256(path)
        if size != expected["bytes"] or digest != expected["sha256"]:
            raise RuntimeError(
                f"archive verification failed: {name}: bytes={size}, sha256={digest}")
        print(f"verified {name}: {size} bytes sha256={digest}", flush=True)
        records.append({"file": name, "bytes": size, "sha256": digest,
                        "source": f"{BASE_URL}/{name}"})
        if not verify_only and not no_extract:
            destination = root.parent if expected["extract"] == "parent" else root
            print(f"extract {name} -> {destination}", flush=True)
            _safe_extract(path, destination)

    licence = root / "TLESS_LICENSE.txt"
    if not verify_only:
        licence.write_text(LICENCE_TEXT, encoding="utf-8", newline="\n")
        manifest = {
            "dataset": "BOP T-LESS",
            "licence": "CC BY 4.0",
            "licence_source": "https://bop.felk.cvut.cz/datasets/",
            "paper_doi": "https://doi.org/10.1109/WACV.2017.8",
            "archives": records,
        }
        (root / "fullseye_tless_manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8", newline="\n")
    return {"root": str(root), "archives": records}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-dir", type=Path,
        default=Path(os.environ.get("FULLSEYE_TLESS_DATA", DEFAULT_DIR)),
        help="external T-LESS cache (default: FULLSEYE_TLESS_DATA or %(default)s)")
    parser.add_argument("--verify-only", action="store_true",
                        help="do not download or extract; only verify cached archives")
    parser.add_argument("--no-extract", action="store_true",
                        help="download and verify archives without extracting them")
    args = parser.parse_args()
    result = fetch(args.data_dir, verify_only=args.verify_only,
                   no_extract=args.no_extract)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
