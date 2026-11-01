# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""CC BY 4.0 の metal-layer SEM データを repo 外へ取得し、由来を固定する。

使い方::

    py -3.11 tools/fetch_sem_metal_layer.py

既定のキャッシュ先は :func:`realdata.sem_metal_layer_cache`、上書きは
``FULLSEYE_SEM_METAL_DATA``。CI / ``FULLSEYE_OFFLINE=1`` ではネットへ出ない。
取得中は ``dataset.zip.part`` に書き、Range で再開する。期待バイト数と SHA-256 の
両方が一致するまで展開しない。ZIP の絶対パス、``..``、symlink、総展開量の過大な
申告を拒否してから展開する。原本、展開物、``SOURCE.json`` は repo に入れない。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import realdata  # noqa: E402


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _download(target: Path) -> None:
    if os.environ.get("CI") or os.environ.get("FULLSEYE_OFFLINE") == "1":
        raise RuntimeError("CI / FULLSEYE_OFFLINE=1 では 6.4 GB の実データを取得しない")
    if not realdata.SEM_METAL_SHA256:
        raise RuntimeError("realdata.SEM_METAL_SHA256 が未記録なので取得物を検証できない")
    part = target.with_suffix(target.suffix + ".part")
    if target.exists() and target.stat().st_size == realdata.SEM_METAL_BYTES:
        return
    if target.exists():
        if part.exists():
            raise RuntimeError("未完了ファイルが 2 つある: %s / %s" % (target, part))
        target.replace(part)
    offset = part.stat().st_size if part.exists() else 0
    if offset > realdata.SEM_METAL_BYTES:
        raise RuntimeError("部分ファイルが期待サイズを超えている: %d" % offset)
    headers = {"User-Agent": "fullseye-realdata/1"}
    if offset:
        headers["Range"] = "bytes=%d-" % offset
    request = urllib.request.Request(realdata.SEM_METAL_URL, headers=headers)
    print("取得: %s" % realdata.SEM_METAL_URL)
    print("再開位置: %s / %s bytes" % (format(offset, ","), format(realdata.SEM_METAL_BYTES, ",")))
    try:
        response = urllib.request.urlopen(request, timeout=600)  # noqa: S310 - 固定 HTTPS URL
    except urllib.error.URLError as exc:
        raise RuntimeError("取得に失敗: %s" % exc) from exc
    status = getattr(response, "status", response.getcode())
    if offset and status != 206:
        response.close()
        raise RuntimeError("Range 再開に対して HTTP %s (206 でない); 部分ファイルを上書きしない" % status)
    mode = "ab" if offset else "wb"
    with response, part.open(mode) as out:
        shutil.copyfileobj(response, out, length=8 * 1024 * 1024)
    if part.stat().st_size != realdata.SEM_METAL_BYTES:
        raise RuntimeError("取得サイズ %d、期待 %d。再実行すれば続きから再開する"
                           % (part.stat().st_size, realdata.SEM_METAL_BYTES))
    part.replace(target)


def _safe_members(zf: zipfile.ZipFile):
    total = 0
    members = zf.infolist()
    if len(members) > 100_000:
        raise RuntimeError("ZIP member が多すぎる: %d" % len(members))
    for info in members:
        name = PurePosixPath(info.filename.replace("\\", "/"))
        if name.is_absolute() or ".." in name.parts or not name.parts:
            raise RuntimeError("ZIP の危険なパス: %r" % info.filename)
        mode = (info.external_attr >> 16) & 0o170000
        if mode == 0o120000:
            raise RuntimeError("ZIP 内 symlink は展開しない: %r" % info.filename)
        total += info.file_size
        if total > 20_000_000_000:
            raise RuntimeError("ZIP の展開後申告サイズが 20 GB を超える")
    return members, total


def _extract(archive: Path, cache: Path) -> Path:
    out = cache / "extracted"
    marker = out / ".complete"
    if marker.is_file() and marker.read_text(encoding="ascii").strip() == realdata.SEM_METAL_SHA256:
        return out
    if out.exists() and any(out.iterdir()):
        raise RuntimeError("未完了の展開先が空でない: %s (確認して空にしてから再実行)" % out)
    out.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as zf:
        members, total = _safe_members(zf)
        print("展開: %d files / %s bytes -> %s" % (len(members), format(total, ","), out))
        zf.extractall(out, members=members)
    marker.write_text(realdata.SEM_METAL_SHA256 + "\n", encoding="ascii")
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--no-extract", action="store_true", help="ZIP の検証までで止める")
    args = ap.parse_args(argv)
    cache = realdata.sem_metal_layer_cache()
    cache.mkdir(parents=True, exist_ok=True)
    archive = cache / "dataset.zip"
    _download(archive)
    size = archive.stat().st_size
    digest = _sha256(archive)
    print("dataset.zip: %s bytes" % format(size, ","))
    print("SHA-256: %s" % digest)
    if size != realdata.SEM_METAL_BYTES or digest != realdata.SEM_METAL_SHA256:
        raise RuntimeError("原本のサイズまたは SHA-256 が記録値と一致しない。展開しない")
    extracted = None if args.no_extract else _extract(archive, cache)
    license_candidates = list(extracted.glob("**/LICENSE*")) if extracted is not None else []
    if extracted is not None and not license_candidates:
        raise RuntimeError("展開物に LICENSE が無い。出典を確定できない")
    if license_candidates:
        shutil.copyfile(license_candidates[0], cache / "LICENSE.dataset.txt")
    source = {
        "title": "A Real-World Metal-Layer SEM Image Dataset with Partial Labels",
        "authors": "Rothaug et al.",
        "dataset_doi": realdata.SEM_METAL_DATASET_DOI,
        "paper_doi": realdata.SEM_METAL_PAPER_DOI,
        "license": realdata.SEM_METAL_LICENSE,
        "source_url": realdata.SEM_METAL_URL,
        "bytes": size,
        "sha256": digest,
        "acquired_utc": datetime.now(timezone.utc).isoformat(),
        "archive": archive.name,
    }
    (cache / "SOURCE.json").write_text(json.dumps(source, ensure_ascii=False, indent=2) + "\n",
                                        encoding="utf-8")
    print("出典: %s" % realdata.sem_metal_layer_credit())
    if extracted is not None:
        print("展開先: %s" % extracted)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
