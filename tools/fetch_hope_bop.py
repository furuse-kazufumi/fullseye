# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""HOPE(Household Objects for Pose Estimation、BOP 形式)の val と模型を repo の外へ取得する。

    py -3.11 tools/fetch_hope_bop.py            # 置き場: FULLSEYE_HOPE_DATA か <作業場>/data/fullseye_poc_real/hope_bop

``examples/poc_mixed_case_depalletizing.py`` の実データの章が読む(能動ステレオ式の深度カメラの実深度で、平面 → 矩形の
寸法を BOP の真の姿勢と寸法で採点する)。取得元は BOP の配布(Hugging Face の bop-benchmark/hope)。

ライセンス: データに同梱の dataset_info.md は「CC BY-NC-SA 4.0」、BOP の配布ページは「CC BY-SA 4.0」と
食い違う。厳しい方(非商用)に倒し、PoC は**数値だけ**を出し画像を図に出さない。repo には入れない。
取得物は untrusted として SHA-256 を照合してから展開する。
"""
from __future__ import annotations

import hashlib
import os
import sys
import urllib.request
import zipfile
from pathlib import Path

URL = "https://huggingface.co/datasets/bop-benchmark/hope/resolve/main/"
#: 2026-11-08 に取得した値(examples/poc_mixed_case_depalletizing.py の HOPE_ZIPS と同じ)。
FILES = {
    "hope_base.zip": "fb3bf622e1cc873af2fecb676420a639967bf1f97f8e37d96503a64ac02b0be7",
    "hope_models.zip": "b92d47db20fc98c8f54ea42754ca1b5db123f7ed99aa9b9aca3ed0409160385d",
    "hope_val_realsense.zip": "25c75bb2daad4ad7e143b3f8d5bdff793fadb65463492792e822dbb36245a49f",
}


def cache_dir() -> Path:
    v = os.environ.get("FULLSEYE_HOPE_DATA", "").strip()
    if v:
        return Path(v)
    here = Path(__file__).resolve().parents[1]
    if here.parent.name.lower() == "projects":
        return here.parent.parent / "data" / "fullseye_poc_real" / "hope_bop"
    return Path.home() / ".cache" / "fullseye" / "hope_bop"


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    root = cache_dir()
    (root / "zips").mkdir(parents=True, exist_ok=True)
    for name, sha in FILES.items():
        f = root / "zips" / name
        if not f.is_file() or _sha(f) != sha:
            print("download", name, flush=True)
            urllib.request.urlretrieve(URL + name, str(f))
        got = _sha(f)
        if got != sha:
            print("SHA-256 mismatch for %s: %s" % (name, got), file=sys.stderr)
            return 1
        with zipfile.ZipFile(f) as z:
            for m in z.namelist():                       # 展開先の外へ出る名前は拒否する
                if m.startswith(("/", "\\")) or ".." in Path(m).parts:
                    print("unsafe member in %s: %s" % (name, m), file=sys.stderr)
                    return 1
            z.extractall(root)
    print("ok:", root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
