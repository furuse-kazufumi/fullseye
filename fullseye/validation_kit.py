# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""fullseye.validation_kit — 手元の非公開データで能力を確かめ、**集計値だけ**を JSON に出す。

Run a Fullseye capability on your own (possibly confidential) data and write only an
aggregate JSON — metrics, n, Fullseye version/commit, environment, input count and
optional SHA-256 hashes. **No pixels, no file names, no paths** ever leave your machine
through this file. Paste the JSON into the validation-report issue form
(``.github/ISSUE_TEMPLATE/real_validation_report.yml``) or send it privately.

なぜ要るか(2026-10-11): Fullseye は個人開発で物理の計測装置を持たない。実機を持つ人の
多くは企業の中にいて、画像・CAD・測定値を外に出せない。だから「データは手元に置いたまま、
結果の数字だけを出す」道を一級にする。そのとき報告者ごとに集計のしかたが違うと、
報告同士を比べられない —— 集計は**同じコード**で行う。

使い方 / Usage::

    python -m fullseye.validation_kit list
    python -m fullseye.validation_kit run blob-count --manifest truth.csv --out result.json

``truth.csv`` は 2 列 ``file,truth``(``file`` は CSV の置き場所からの相対パス、
``truth`` は基準で得た真値)。画像は :func:`imgio.load` が読める形式か ``.npy``。

★出力に入れないもの: 画素・ファイル名・パス・ホスト名・ユーザー名。入れるもの: 件数・
誤差の集計・Fullseye の版とコミット・Python / numpy の版・OS の種類・入力ファイルの
SHA-256(``--no-hashes`` で外せる。ハッシュは「同じファイルで再実行した」ことを後で
示すためのもので、中身は復元できない)。

能力を足すには :data:`KITS` に :class:`Kit` を 1 つ足す(``measure`` は灰色画像
``float64 [0,1]`` と引数 dict を受けてスカラー 1 つを返す)。試験は
``tests/test_validation_kit.py``。
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import platform
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Callable, Dict, List

import numpy as np

__all__ = ["Kit", "KITS", "run_kit", "aggregate", "main", "KIT_SCHEMA"]

#: 出力 JSON の形の版。形を変えたら上げる(フォームに貼られた JSON を後で読むため)。
KIT_SCHEMA = 1


class KitError(ValueError):
    """入力が確かめられない(fail-closed: 部分的な集計を出さずに止める)。"""


@dataclass(frozen=True)
class Kit:
    """1 つの能力を確かめる手順。

    ``measure(image, params) -> float`` は灰色画像 1 枚から測定値 1 つを返す。
    ``integer`` が真なら真値と測定値を整数として扱い、完全一致率も出す。
    """

    name: str
    capability: str
    description: str
    unit: str
    measure: Callable[[np.ndarray, dict], float]
    params: Dict[str, object] = field(default_factory=dict)
    integer: bool = False


def _measure_blob_count(image: np.ndarray, params: dict) -> float:
    """自動しきい値(大津)で二値化し、連結成分を数える。``invert`` で明暗を反転。"""
    import fullseye as fs

    img = np.asarray(image, np.float64)
    if params.get("invert"):
        img = 1.0 - img
    mask = fs.apply(img, "otsu")
    return float(fs.apply(np.asarray(mask, np.float64), "blob_count"))


#: 使える手順の一覧。**足すときはここに 1 行**(名前は CLI の引数になる)。
KITS: Dict[str, Kit] = {
    "blob-count": Kit(
        name="blob-count",
        capability="blob-and-region",
        description="Count separated objects (Otsu threshold -> connected components) "
                    "and compare with counts from a reference method. / 物体の個数を数えて"
                    "基準の個数と比べる",
        unit="objects",
        measure=_measure_blob_count,
        params={"invert": False},
        integer=True,
    ),
}


def _load_image(path: str) -> np.ndarray:
    if path.lower().endswith(".npy"):
        arr = np.load(path, allow_pickle=False)
    else:
        import imgio
        arr = imgio.load(path)
    arr = np.asarray(arr, np.float64)
    if arr.ndim == 3:
        arr = arr.mean(axis=2)
    if arr.ndim != 2 or arr.size == 0:
        raise KitError("image must be a non-empty 2-D greyscale array (got shape %s)"
                       % (arr.shape,))
    if not np.all(np.isfinite(arr)):
        raise KitError("image contains NaN or inf")
    lo, hi = float(arr.min()), float(arr.max())
    if lo < 0.0 or hi > 1.0:          # .npy は任意の範囲で来うる → [0,1] に寄せる
        arr = (arr - lo) / (hi - lo) if hi > lo else np.zeros_like(arr)
    return arr


def _read_manifest(manifest: str) -> List[tuple]:
    """``[(absolute_path, truth), ...]``。1 行でも壊れていれば止める。"""
    if not os.path.isfile(manifest):
        raise KitError("manifest not found: %s" % manifest)
    base = os.path.dirname(os.path.abspath(manifest))
    rows = []
    with open(manifest, encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None or not {"file", "truth"} <= set(reader.fieldnames):
            raise KitError("manifest must have the header columns: file,truth")
        for n, rec in enumerate(reader, start=2):
            name = (rec.get("file") or "").strip()
            if not name:
                raise KitError("manifest line %d: empty file column" % n)
            try:
                truth = float(rec.get("truth", ""))
            except ValueError:
                raise KitError("manifest line %d: truth is not a number" % n)
            if not math.isfinite(truth):
                raise KitError("manifest line %d: truth is not finite" % n)
            path = name if os.path.isabs(name) else os.path.join(base, name)
            if not os.path.isfile(path):
                raise KitError("manifest line %d: file not found" % n)
            rows.append((path, truth))
    if not rows:
        raise KitError("manifest has no data rows")
    return rows


def aggregate(truth: List[float], measured: List[float], integer: bool = False) -> dict:
    """誤差の集計(**画素も名前も持たない数字だけ**)。"""
    t = np.asarray(truth, np.float64)
    m = np.asarray(measured, np.float64)
    if t.shape != m.shape or t.size == 0:
        raise KitError("truth and measured must be non-empty and the same length")
    err = m - t
    out = {
        "n": int(t.size),
        "mean_signed_error": float(err.mean()),
        "mean_abs_error": float(np.abs(err).mean()),
        "rms_error": float(np.sqrt((err ** 2).mean())),
        "max_abs_error": float(np.abs(err).max()),
        "std_error": float(err.std(ddof=1)) if t.size > 1 else None,
    }
    nz = t != 0
    out["mean_abs_relative_error"] = (float(np.abs(err[nz] / t[nz]).mean())
                                      if nz.any() else None)
    out["relative_error_n"] = int(nz.sum())
    if integer:
        out["exact_match_rate"] = float(np.mean(np.rint(m) == np.rint(t)))
    return out


def _git_commit() -> object:
    """Fullseye の置き場所が git の作業木ならそのコミット。そうでなければ None。"""
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    try:
        r = subprocess.run(["git", "-C", here, "rev-parse", "HEAD"],
                           capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    sha = r.stdout.strip()
    return sha if r.returncode == 0 and len(sha) == 40 else None


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def run_kit(name: str, manifest: str, params: dict = None, hashes: bool = True) -> dict:
    """手順 *name* を *manifest* の全件に掛け、集計 JSON(dict)を返す。"""
    if name not in KITS:
        raise KitError("unknown kit %r (available: %s)" % (name, ", ".join(sorted(KITS))))
    kit = KITS[name]
    p = dict(kit.params)
    for k, v in (params or {}).items():
        if k not in p:
            raise KitError("kit %s has no parameter %r" % (name, k))
        p[k] = v
    rows = _read_manifest(manifest)
    truth, measured = [], []
    for n, (path, t) in enumerate(rows, start=1):
        v = float(kit.measure(_load_image(path), p))
        if not math.isfinite(v):
            raise KitError("item %d: measurement is not finite" % n)
        truth.append(t)
        measured.append(v)
    import fullseye as fs
    out = {
        "kit_schema": KIT_SCHEMA,
        "kit": kit.name,
        "capability": kit.capability,
        "unit": kit.unit,
        "parameters": p,
        "fullseye_version": getattr(fs, "__version__", None),
        "fullseye_commit": _git_commit(),
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "os": platform.system(),
            "machine": platform.machine(),
        },
        "inputs": {
            "count": len(rows),
            "sha256": sorted(_sha256(path) for path, _t in rows) if hashes else None,
        },
        "metrics": aggregate(truth, measured, integer=kit.integer),
        "privacy": "No pixels, file names or paths are included in this file.",
    }
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="python -m fullseye.validation_kit",
        description="Run a Fullseye capability on local data and print only aggregate "
                    "numbers (no pixels, no file names).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="list the available kits")
    r = sub.add_parser("run", help="run a kit on a manifest of files and true values")
    r.add_argument("kit")
    r.add_argument("--manifest", required=True, help="CSV with columns file,truth")
    r.add_argument("--invert", action="store_true",
                   help="objects are darker than the background (blob-count)")
    r.add_argument("--no-hashes", action="store_true",
                   help="omit the SHA-256 hashes of the input files")
    r.add_argument("--out", help="write the JSON here instead of printing it")
    a = ap.parse_args(argv)
    if a.cmd == "list":
        for k in sorted(KITS.values(), key=lambda x: x.name):
            print("%-12s capability=%s  unit=%s\n    %s" % (k.name, k.capability, k.unit,
                                                          k.description))
        return 0
    params = {"invert": True} if a.invert else {}
    try:
        res = run_kit(a.kit, a.manifest, params, hashes=not a.no_hashes)
    except KitError as exc:
        print("validation_kit: %s" % exc, file=sys.stderr)
        return 2
    text = json.dumps(res, ensure_ascii=False, indent=1) + "\n"
    if a.out:
        with open(a.out, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        print("wrote %s" % a.out)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
