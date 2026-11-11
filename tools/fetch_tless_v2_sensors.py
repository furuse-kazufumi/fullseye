# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Download the T-LESS v2 test scene used by ``examples/poc_3d_sensor_modalities.py``.

The PoC compares two depth sensors that imaged the **same scene from the same rig**: a
structured-light sensor (projected dot pattern + correlation) and a continuous-wave
time-of-flight sensor. T-LESS v2 (the original release, not the BOP subset) ships both,
with ground-truth poses per sensor and the CAD models, so the true depth can be rendered.

同じ場面を構造化光と ToF の 2 種類の深度センサで撮った T-LESS v2 の試験場面 1 つと CAD を、repo の外へ取ってくる。
データは repo に入れない。書庫の大きさと SHA-256 を固定し、合わなければ止める(fail-closed)。

    py -3.11 tools/fetch_tless_v2_sensors.py                 # 取得 + 検査 + 展開
    py -3.11 tools/fetch_tless_v2_sensors.py --verify-only   # 検査だけ

置き場所は ``FULLSEYE_TLESS_V2_DATA``(無ければ ``~/fullseye_data/tless_v2_sensors``)。展開後に
``sensors.json``(センサの種類 → フォルダ)と ``LICENSE.txt`` を書く。PoC はこの環境変数を見る。

Licence (quoted from http://cmp.felk.cvut.cz/t-less/ on 2026-11-08):
"This work is licensed under Creative Commons Attribution 4.0 International."
Citation: Hodaň et al., T-LESS: An RGB-D Dataset for 6D Pose Estimation of Texture-less
Objects, WACV 2017, https://doi.org/10.1109/WACV.2017.8
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.request
import zipfile
from pathlib import Path

BASE_URL = "http://ptak.felk.cvut.cz/darwin/t-less/v2/"
DEFAULT_DIR = Path(os.environ.get("FULLSEYE_TLESS_V2_DATA") or (Path.home() / "fullseye_data" / "tless_v2_sensors"))
SCENE = 2
ARCHIVES = {
    "t-less_v2_models_cad.zip": {
        "bytes": 9_745_999,
        "sha256": "aa95d617304fdfcd343de565ba0465ffe3184baa7397b66b4cade9987ca0122a",
    },
    "t-less_v2_test_kinect_02.zip": {
        "bytes": 307_900_983,
        "sha256": "d05fc98032854b3ff24db10365334705e26ae1136cecf5c8ad38c02836eed237",
    },
    "t-less_v2_test_primesense_02.zip": {
        "bytes": 381_217_606,
        "sha256": "0508791a7b9154a2181c3b98170b3a312ed1bee86457a64c913e92939ab7df23",
    },
}
#: sensor kind -> extracted folder (the PoC never spells the product names)
SENSORS = {"sl": "t-less_v2_test_primesense_02", "tof": "t-less_v2_test_kinect_02",
           "models": "t-less_v2_models_cad/models_cad"}

LICENCE_TEXT = """T-LESS v2 (test scene 02, two depth sensors, CAD models)
Licence: Creative Commons Attribution 4.0 International (CC BY 4.0)
Licence URL: https://creativecommons.org/licenses/by/4.0/
Statement: http://cmp.felk.cvut.cz/t-less/ ("This work is licensed under Creative Commons Attribution 4.0 International.")
Download: http://ptak.felk.cvut.cz/darwin/t-less/v2/
Citation: Hodan, Haluza, Obdrzalek, Matas, Lourakis, Zabulis. T-LESS: An RGB-D Dataset for 6D Pose
Estimation of Texture-less Objects. WACV 2017. https://doi.org/10.1109/WACV.2017.8
"""


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _check(path: Path, spec: dict) -> None:
    if not path.is_file():
        raise FileNotFoundError("missing archive: %s" % path)
    size = path.stat().st_size
    if size != spec["bytes"]:
        raise ValueError("%s: %d bytes, expected %d" % (path.name, size, spec["bytes"]))
    digest = _sha256(path)
    if digest != spec["sha256"]:
        raise ValueError("%s: sha256 %s, expected %s" % (path.name, digest, spec["sha256"]))


def _download(name: str, dest: Path) -> None:
    tmp = dest.with_suffix(".part")
    with urllib.request.urlopen(BASE_URL + name, timeout=60) as resp, tmp.open("wb") as fh:  # noqa: S310 (fixed URL)
        while True:
            block = resp.read(1 << 20)
            if not block:
                break
            fh.write(block)
    tmp.replace(dest)


def _extract(path: Path, root: Path) -> None:
    sub = root / path.stem
    with zipfile.ZipFile(path) as zf:
        for member in zf.namelist():
            target = (sub / member).resolve()
            # 前方一致の文字列比較では兄弟の "X2" が通るので、パスの親子で確かめる
            if not target.is_relative_to(sub.resolve()):
                raise ValueError("unsafe path in archive: %s" % member)
        zf.extractall(sub)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dir", type=Path, default=DEFAULT_DIR)
    ap.add_argument("--verify-only", action="store_true")
    a = ap.parse_args(argv)
    root = a.dir
    zips = root / "zips"
    zips.mkdir(parents=True, exist_ok=True)
    for name, spec in ARCHIVES.items():
        p = zips / name
        if not p.is_file() and not a.verify_only:
            print("downloading %s ..." % name)
            _download(name, p)
        _check(p, spec)
        print("ok  %s  %s" % (name, spec["sha256"]))
    if a.verify_only:
        return 0
    for name in ARCHIVES:
        _extract(zips / name, root)
    (root / "sensors.json").write_text(json.dumps(SENSORS, indent=1), encoding="utf-8")
    (root / "LICENSE.txt").write_text(LICENCE_TEXT, encoding="utf-8")
    print("extracted to %s; set FULLSEYE_TLESS_V2_DATA=%s" % (root, root))
    return 0


if __name__ == "__main__":
    sys.exit(main())
