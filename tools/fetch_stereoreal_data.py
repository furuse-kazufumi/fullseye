# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""実写のステレオ対と校正板の写真を repo 外へ取得し、SHA-256 で固定する(PoC 2 本の台帳を兼ねる)。

使い方::

    py -3.11 tools/fetch_stereoreal_data.py            # 両方
    py -3.11 tools/fetch_stereoreal_data.py middeval3  # Middlebury MiddEval3 の 1/4 解像度だけ
    py -3.11 tools/fetch_stereoreal_data.py chessboard # OpenCV の校正板の写真だけ

読む側:

* ``examples/poc_real_stereo_multiscanline.py`` —— Middlebury MiddEval3 の訓練 15 場面(1/4 解像度、
  真値視差と遮蔽の印つき)。無ければ scikit-image 同梱の motorcycle だけで回る。
* ``examples/poc_real_chessboard_undistort.py`` —— OpenCV の配布する校正板の写真 13 枚。

データのライセンス(配布元の文言):

* Middlebury: "We grant permission to use and publish all images and disparity maps on this website."
  (https://vision.middlebury.edu/stereo/data/ の "How to cite our datasets")。引用の依頼は
  Scharstein et al., GCPR 2014。
* OpenCV samples/data: OpenCV のリポジトリの Apache License 2.0(https://github.com/opencv/opencv の LICENSE)。
  取得は固定のコミット :data:`OPENCV_COMMIT` から。

置き場は :func:`cache_dir`(上書きは ``FULLSEYE_MIDDEVAL3_DATA`` / ``FULLSEYE_OPENCV_CHESSBOARD_DATA``)。
データは repo に入れない。fail-closed: CI / ``FULLSEYE_OFFLINE=1`` ではネットへ出ない。各ファイルは
``.part`` に書き、バイト数と SHA-256 が台帳に一致したときだけ本名にする。違う中身が在れば上書きせず止まる。
"""
from __future__ import annotations

import hashlib
import os
import sys
import urllib.request
from pathlib import Path

#: Middlebury MiddEval3 の 1/4 解像度(入力と左の真値)。2026-11-08 に取得した値。
MIDDEVAL3_URL = "https://vision.middlebury.edu/stereo/submit3/zip/%s"
MIDDEVAL3_FILES = {
    "MiddEval3-data-Q.zip": (30937533, "a1411f283b523541e0d2e8b3a1dd6618974a0e539aea0122490791a041fffc09"),
    "MiddEval3-GT0-Q.zip": (13555667, "489b6a4015951a3c865aa54c0f37dcb648b5d0efad8019264e22499cef35ca45"),
}

#: OpenCV の校正板の写真(9x6 の内角、640x480)。left10.jpg は配布元に無い。
OPENCV_COMMIT = "9d4808bef88a7aacbb360732303d42b279ebb6b5"
OPENCV_URL = "https://raw.githubusercontent.com/opencv/opencv/" + OPENCV_COMMIT + "/samples/data/%s"
OPENCV_FILES = {
    "left01.jpg": (27908, "9621899098adffa1440c8264606bb7be535ccfd9ad126ae8e0bd9b0c5a5b8676"),
    "left02.jpg": (28611, "052e700bbcc865c112958ec2ea105cb1bce4deca50ac8d6efae13adca9df7a2c"),
    "left03.jpg": (29553, "c85b9426c3d8fcf161e1e727356105091009c3fd0b1b1a65bc2da91fea2724d2"),
    "left04.jpg": (25150, "b490599dccfbfe5eb56d33363415b02227a9548ab8c9b8e7b05d3580e97266d9"),
    "left05.jpg": (28743, "40bab8934fa76f82ec614a7fd0e6ebb4d9f74391d5e8b0c6f2f0ed6080c6c4de"),
    "left06.jpg": (28530, "1cb164db61b3bd52f58a7e9340bb27c5e0278895bc80b6f292fba5cf9bccc4a1"),
    "left07.jpg": (29864, "d2211fe9f971646b6ff88ed93a4f0d3f443741eb2894095cba15caade7c8c6e4"),
    "left08.jpg": (28689, "f7a0737894812a28243af5b409c5689f4fadfe7610958b8ca5fc79aec2f2cd1b"),
    "left09.jpg": (27244, "753939bc62d093c001d9118e989bef2b887f1b2f9ac03603df915a8b85aa81d3"),
    "left11.jpg": (27749, "e736ace3d515c94c547009c3c10d818c81506ed7059cb31123749b9cc3f94ee8"),
    "left12.jpg": (25603, "04bdd78b3b507fe0551aa7062a3ffd94846a147ee2bea7fb38082c720bdbe231"),
    "left13.jpg": (28129, "2637fb6dd5e557f4fadb06b353a453eb0b9223f4671f6f572f815302bc4a70b3"),
    "left14.jpg": (27875, "d4c032971dd7b859f9d6aed5090c9888bd8039b82e0604bee5bfe05444fce834"),
}

#: 名前 → (環境変数, 置き場の名前, URL の型, 台帳)
SETS = {
    "middeval3": ("FULLSEYE_MIDDEVAL3_DATA", "middlebury_eval3_q", MIDDEVAL3_URL, MIDDEVAL3_FILES),
    "chessboard": ("FULLSEYE_OPENCV_CHESSBOARD_DATA", "opencv_chessboard", OPENCV_URL, OPENCV_FILES),
}


class DataError(RuntimeError):
    """取得物が無い・欠けている・台帳と中身が違う。"""


def cache_dir(name: str) -> Path:
    """データ組 ``name`` の repo 外の置き場。

    環境変数があればそれ。無ければ、開発 worktree が ``<root>/projects/<checkout>`` にあるとき
    ``<root>/data/fullseye_poc_real/<組>``、それ以外は ``~/.cache/fullseye/<組>``
    (手元の絶対パスをソースに書かないための分岐。``realdata.e57_bunny_cache`` と同じ形)。
    """
    env, sub, _url, _files = SETS[name]
    configured = os.environ.get(env, "").strip()
    if configured:
        return Path(configured).expanduser()
    here = Path(__file__).resolve().parents[1]
    if here.parent.name.lower() == "projects":
        return here.parent.parent / "data" / "fullseye_poc_real" / sub
    return Path.home() / ".cache" / "fullseye" / sub


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def files(name: str, *, required: bool = True) -> dict[str, Path] | None:
    """取得済みの組を、バイト数と SHA-256 を照合してから ``{ファイル名: パス}`` で返す。

    1 つも無ければ ``required=False`` で ``None``(CI の既定)。一部だけ在る・中身が違うときは
    黙って使わず :class:`DataError`(取得物は untrusted として照合してから読む)。
    """
    _env, _sub, _url, table = SETS[name]
    root = cache_dir(name)
    present = {f: root / f for f in table if (root / f).is_file()}
    if not present:
        if required:
            raise DataError("%s が無い: %s。py -3.11 tools/fetch_stereoreal_data.py %s で取得する"
                            % (name, root, name))
        return None
    missing = sorted(set(table) - set(present))
    if missing:
        raise DataError("%s が欠けている(%s): %s" % (name, ", ".join(missing), root))
    for f, (size, digest) in table.items():
        p = present[f]
        if p.stat().st_size != size:
            raise DataError("%s のバイト数 %d が台帳 %d と違う" % (p, p.stat().st_size, size))
        got = sha256_file(p)
        if got != digest:
            raise DataError("%s の SHA-256 %s が台帳と違う" % (p, got))
    return present


def fetch(name: str) -> Path:
    if os.environ.get("CI") or os.environ.get("FULLSEYE_OFFLINE") == "1":
        raise SystemExit("CI / FULLSEYE_OFFLINE=1 では取得しない")
    _env, _sub, url, table = SETS[name]
    dest = cache_dir(name)
    dest.mkdir(parents=True, exist_ok=True)
    for f, (size, digest) in table.items():
        target = dest / f
        if target.exists():
            if target.stat().st_size == size and sha256_file(target) == digest:
                print("ok    %s" % f)
                continue
            raise SystemExit("%s が台帳と違う中身で在る。消してから取り直す" % target)
        part = target.with_name(target.name + ".part")
        request = urllib.request.Request(url % f, headers={"User-Agent": "fullseye-realdata/1"})
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
        if total != size or sha256_file(part) != digest:
            part.unlink(missing_ok=True)
            raise SystemExit("%s のバイト数 / SHA-256 が台帳と違う(取得物を捨てた)" % f)
        part.replace(target)
        print("fetch %s (%d bytes)" % (f, size))
    files(name, required=True)
    print("置き場: %s" % dest)
    return dest


if __name__ == "__main__":
    wanted = sys.argv[1:] or sorted(SETS)
    unknown = [w for w in wanted if w not in SETS]
    if unknown:
        raise SystemExit("未知の組: %s(知っているのは %s)" % (", ".join(unknown), ", ".join(sorted(SETS))))
    for w in wanted:
        fetch(w)
