# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""TBM(金属組織の実写の顕微鏡写真と専門家の手描きの粒界、320 枚)を repo 外へ取得し、SHA-256 で固定する。

Fetch the Texture Boundary in Metallography (TBM) dataset -- 320 real metallographic micrograph crops
with expert hand-drawn grain boundaries -- outside the repository and pin it by SHA-256.

使い方 / usage::

    py -3.11 tools/fetch_tbm.py [置き場 / destination]

配布元: Zenodo record 8386997(doi:10.5281/zenodo.8386997、2023-09-28 公開 v1)。
ライセンスの記載: "Creative Commons Attribution 4.0 International"。

repo には入れない(共通の決まり: 実データは取得の道具と SHA-256 で固定する)。既定の置き場は
``examples/poc_real_grain_skiz.py`` の :func:`tbm_cache` と同じ(上書きは ``FULLSEYE_TBM_DATA``)。

fail-closed: CI / ``FULLSEYE_OFFLINE=1`` ではネットへ出ない。書庫は ``.part`` に書き、バイト数と
SHA-256 が台帳に一致したときだけ本名にする。展開は ``TBM/`` の下の通常のファイルだけ
(``__MACOSX`` と ``.DS_Store`` は捨てる、書庫の外を指す名前は拒否)。
"""
from __future__ import annotations

import hashlib
import os
import sys
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

TBM_URL = "https://zenodo.org/records/8386997/files/TBM.zip?download=1"
TBM_BYTES = 92766034
#: 2026-11-08 に上の URL から取得した TBM.zip の SHA-256(Zenodo の md5 e391d82d511d5a7afafecbf078d138e5 とも一致)。
TBM_SHA256 = "08375c35fe0d80bb61beb82d7d9205a798838e2fccd6cd49586c6c4c8e2b8a29"


def default_cache() -> Path:
    """既定の置き場(PoC の :func:`tbm_cache` と同じ規則)。"""
    configured = os.environ.get("FULLSEYE_TBM_DATA", "").strip()
    if configured:
        return Path(configured).expanduser()
    here = Path(__file__).resolve().parents[1]
    if here.parent.name.lower() == "projects":
        return here.parent.parent / "data" / "fullseye_poc_real" / "tbm"
    return Path.home() / ".cache" / "fullseye" / "tbm"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _extract(archive: Path, dest: Path) -> int:
    n = 0
    with zipfile.ZipFile(archive) as zf:
        for info in zf.infolist():
            name = PurePosixPath(info.filename)
            if info.is_dir() or not name.parts or name.parts[0] != "TBM" or name.name == ".DS_Store":
                continue
            if name.is_absolute() or ".." in name.parts:
                raise SystemExit("書庫の外を指す名前: %s" % info.filename)
            out = dest.joinpath(*name.parts)
            out.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, out.open("wb") as dst:
                dst.write(src.read())
            n += 1
    return n


def fetch(dest: Path | None = None) -> Path:
    if os.environ.get("CI") or os.environ.get("FULLSEYE_OFFLINE") == "1":
        raise SystemExit("CI / FULLSEYE_OFFLINE=1 では取得しない")
    dest = Path(dest) if dest is not None else default_cache()
    raw = dest / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    archive = raw / "TBM.zip"
    if archive.exists():
        if archive.stat().st_size != TBM_BYTES or _sha256(archive) != TBM_SHA256:
            raise SystemExit("%s が台帳と違う中身で在る。消してから取り直す" % archive)
        print("ok    TBM.zip")
    else:
        part = archive.with_name("TBM.zip.part")
        request = urllib.request.Request(TBM_URL, headers={"User-Agent": "fullseye-realdata/1"})
        total = 0
        with urllib.request.urlopen(request, timeout=300) as resp, part.open("wb") as out:
            if not resp.geturl().startswith("https://"):
                raise SystemExit("https 以外へ転送された: %s" % resp.geturl())
            while True:
                block = resp.read(1 << 16)
                if not block:
                    break
                total += len(block)
                if total > TBM_BYTES:
                    break
                out.write(block)
        if total != TBM_BYTES or _sha256(part) != TBM_SHA256:
            part.unlink(missing_ok=True)
            raise SystemExit("TBM.zip のバイト数 / SHA-256 が台帳と違う(取得物を捨てた)")
        part.replace(archive)
        print("fetch TBM.zip (%d bytes)" % TBM_BYTES)
    if not (dest / "TBM" / "input_image").is_dir():
        print("展開  %d ファイル" % _extract(archive, dest))
    print("置き場: %s" % dest)
    return dest


if __name__ == "__main__":
    fetch(Path(sys.argv[1]) if len(sys.argv) > 1 else None)
