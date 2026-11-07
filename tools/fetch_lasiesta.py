# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""LASIESTA(固定カメラの実写動画と画素ごとの真値)の 3 本を repo 外へ取得し、SHA-256 で固定する。

Fetch three LASIESTA sequences (real static-camera video with per-pixel ground truth) outside the
repository and pin them by SHA-256.

使い方 / usage::

    py -3.11 tools/fetch_lasiesta.py [置き場 / destination]

配布元: Grupo de Tratamiento de Imágenes, Universidad Politécnica de Madrid
(https://www.gti.ssr.upm.es/data/lasiesta_database)。ページの記載:
"This dataset is licensed under the Creative Commons Attribution-ShareAlike 4.0 International
License"。論文: C. Cuevas, E. M. Yáñez, N. García, "Labeled dataset for integral evaluation of
moving object detection algorithms: LASIESTA", Computer Vision and Image Understanding 152,
103-117 (2016), doi:10.1016/j.cviu.2016.08.005。

repo には入れない(容量。CC BY-SA の継承条件を repo の Apache-2.0 と混ぜない)。既定の置き場は
``examples/poc_real_bg_kalman_tracking.py`` の :func:`lasiesta_cache` と同じ
(上書きは ``FULLSEYE_LASIESTA_DATA``)。

fail-closed: CI / ``FULLSEYE_OFFLINE=1`` ではネットへ出ない。書庫は ``.part`` に書き、バイト数と
SHA-256 が下の台帳に一致したときだけ本名にして展開する。展開は ``tar``(bsdtar = libarchive、
Windows 10 以降と macOS に同梱)か ``unrar`` / ``7z`` に任せ、展開後に書庫の外へ出たパスが無いことを
確かめる。置き場にすでに違う中身の書庫があれば上書きせず止まる。
"""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

#: 取得元。``%s`` に列の名前が入る。
LASIESTA_URL = "https://www.gti.ssr.upm.es/images/Data/Downloads/LASIESTA/%s.rar"

#: 列の名前 → (書庫のバイト数, 書庫の SHA-256)。2026-11-08 に上の URL から取得した値。
LASIESTA_ARCHIVES = {
    "I_SI_01": (35209434, "20a1c462aa6f617e14cc1293d0d83d7957a585fd5ea09cf5f26cf0e07a21148b"),
    "I_OC_01": (33101291, "98338566d1981381d52d1fa5e16f7e9062075160890094876f2d5ae62100f72f"),
    "I_OC_02": (25580299, "a873bbf1e7a316b9e2e3e4114d16e9684bf8e4643cdb941dc97bda3318566c04"),
}


def default_cache() -> Path:
    """既定の置き場(PoC の :func:`lasiesta_cache` と同じ規則)。"""
    configured = os.environ.get("FULLSEYE_LASIESTA_DATA", "").strip()
    if configured:
        return Path(configured).expanduser()
    here = Path(__file__).resolve().parents[1]
    if here.parent.name.lower() == "projects":
        return here.parent.parent / "data" / "fullseye_poc_real" / "lasiesta"
    return Path.home() / ".cache" / "fullseye" / "lasiesta"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _download(url: str, part: Path, size: int) -> int:
    request = urllib.request.Request(url, headers={"User-Agent": "fullseye-realdata/1"})
    total = 0
    with urllib.request.urlopen(request, timeout=300) as resp, part.open("wb") as out:
        if not resp.geturl().startswith("https://"):
            raise SystemExit("https 以外へ転送された: %s" % resp.geturl())
        while True:
            block = resp.read(1 << 16)
            if not block:
                break
            total += len(block)
            if total > size:
                break
            out.write(block)
    return total


def _extractor() -> list[str]:
    """RAR を展開できる道具を探す(見つからなければ止まる)。"""
    for name, args in (("tar", ["-xf"]), ("unrar", ["x", "-o-"]), ("7z", ["x", "-y"])):
        exe = shutil.which(name)
        if exe:
            return [exe, *args]
    raise SystemExit("RAR を展開する道具(tar = bsdtar / unrar / 7z)が見つからない")


def _extract(archive: Path, dest: Path) -> None:
    tool = _extractor()
    work = dest / (archive.stem + ".extract")
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    if Path(tool[0]).stem.lower() == "tar":
        cmd = [*tool, str(archive), "-C", str(work)]
    elif Path(tool[0]).stem.lower() == "unrar":
        cmd = [*tool, str(archive), str(work) + os.sep]
    else:
        cmd = [*tool, str(archive), "-o" + str(work)]
    subprocess.run(cmd, check=True, stdin=subprocess.DEVNULL)
    root = work.resolve()
    for p in work.rglob("*"):
        if not p.resolve().is_relative_to(root) or p.is_symlink():
            shutil.rmtree(work, ignore_errors=True)
            raise SystemExit("書庫の外を指すパスがあった: %s" % p)
    target = dest / archive.stem
    if target.exists():
        shutil.rmtree(target)
    work.replace(target)


def fetch(dest: Path | None = None) -> Path:
    if os.environ.get("CI") or os.environ.get("FULLSEYE_OFFLINE") == "1":
        raise SystemExit("CI / FULLSEYE_OFFLINE=1 では取得しない")
    dest = Path(dest) if dest is not None else default_cache()
    raw = dest / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    for name, (size, digest) in LASIESTA_ARCHIVES.items():
        archive = raw / (name + ".rar")
        if archive.exists():
            if archive.stat().st_size != size or _sha256(archive) != digest:
                raise SystemExit("%s が台帳と違う中身で在る。消してから取り直す" % archive)
            print("ok    %s" % archive.name)
        else:
            part = archive.with_name(archive.name + ".part")
            total = _download(LASIESTA_URL % name, part, size)
            if total != size or _sha256(part) != digest:
                part.unlink(missing_ok=True)
                raise SystemExit("%s のバイト数 / SHA-256 が台帳と違う(取得物を捨てた)" % name)
            part.replace(archive)
            print("fetch %s (%d bytes)" % (archive.name, size))
        if not (dest / name / name).is_dir():
            _extract(archive, dest)
            print("展開  %s" % (dest / name))
    print("置き場: %s" % dest)
    return dest


if __name__ == "__main__":
    fetch(Path(sys.argv[1]) if len(sys.argv) > 1 else None)
