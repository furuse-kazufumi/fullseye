# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""実写データの取り口(合成ではないものだけ)。

## なぜ要るか(2026-09-08)

この repo の PoC は**自分で真値を仕込む**規律で書いてある —— 合成なら
「答え」がデータの外に無く、崖も対照群も設計できるからです。ただし合成は
**自分が知っている壊れ方しか作れない**。スケール依存のしきい値、退化した
入力、規約(符号・参照画像・NaN)の食い違いは、実写を通した瞬間に出ます。

そこでこの module は、**追加ダウンロード無しで手元にある実写**だけを
返します。出どころは ``scikit-image`` に同梱されている小さな部分集合で、
ライセンスは下の :data:`SAMPLE_PHOTOS` に 1 件ずつ書いてあります(CC0 /
public domain / no known copyright restrictions のものだけを公開図に使う)。

## fail-closed

**データが無いときに黙って通さない**。:func:`sample_photo_raw` は理由を印字して
``SystemExit(1)`` します —— 「実データが無かったので何も検査せず PASS」は、
この repo がいちばん嫌う形(記録は在るのに誰も読まない門)そのものなので。

CI では ``skimage`` extra が 3 つの matrix 全部に入るので、実データ PoC は
**必ず走ります**。手元で extra を入れていない場合だけ落ちます。

EXTEND: 自前の撮影に差し替えるなら :func:`sample_photo` の戻り値
(float64 / [0, 1] / 2 次元)に合わせてください。ステレオは
:func:`sample_stereo_pair` が ``(左, 右, 真値視差)`` を返す形で、真値が無い画素は
NaN ではなく ``+inf`` で入っています(scikit-image 同梱の motorcycle。``np.isfinite`` で判定する)。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np


#: Rothaug et al. の metal-layer SEM 実データ。原本は repo に入れず、
#: ``tools/fetch_sem_metal_layer.py`` がこの固定 URL から取得して provenance を残す。
SEM_METAL_URL = "https://edmond.mpg.de/api/access/datafile/223856"
SEM_METAL_BYTES = 6_396_523_974
# 2026-11-01 に上の固定 URL から取得した dataset.zip の SHA-256。
# サイズ・ZIP CRC と併せて検証済み。取得スクリプトは不一致なら展開しない。
SEM_METAL_SHA256 = "14e0aef2ceeee0aa46b324521535133eba2e33bea222c9b360a0e7b505024753"
SEM_METAL_DATASET_DOI = "10.17617/3.HY5SYN"
SEM_METAL_PAPER_DOI = "10.1145/3605769.3624000"
SEM_METAL_LICENSE = "CC BY 4.0"


def sem_metal_layer_cache() -> Path:
    """Metal-layer SEM データの repo 外キャッシュ先を返す。

    ``FULLSEYE_SEM_METAL_DATA`` があればその場所を使う。開発 worktree が
    ``<root>/projects/<checkout>`` にある場合は ``<root>/data/realdata``、それ以外の
    インストールではユーザーキャッシュを既定にする。ローカル絶対パスをソースへ
    焼き込まないための分岐である。
    """
    configured = os.environ.get("FULLSEYE_SEM_METAL_DATA", "").strip()
    if configured:
        return Path(configured).expanduser()
    here = Path(__file__).resolve().parent
    if here.parent.name.lower() == "projects":
        return here.parent.parent / "data" / "realdata" / "metal_layer_sem"
    return Path.home() / ".cache" / "fullseye" / "metal_layer_sem"


def sem_metal_layer_root(*, required: bool = True) -> Path | None:
    """展開済み metal-layer SEM データの root を探す。

    認める配置は ``sems`` と ``labels`` を直下に持つ dir、またはキャッシュ内の
    1〜3 段下に同じ組を持つ dir。曖昧な候補が複数あれば選ばずに例外にする。
    PoC はこの関数から読むだけで、データが無い CI からネットへは出ない。
    """
    cache = sem_metal_layer_cache()
    candidates = []
    if (cache / "sems").is_dir() and (cache / "labels").is_dir():
        candidates.append(cache)
    if cache.is_dir():
        for sems in cache.glob("**/sems"):
            try:
                rel_parts = sems.relative_to(cache).parts
            except ValueError:  # pragma: no cover - Path contract
                continue
            if len(rel_parts) <= 4 and (sems.parent / "labels").is_dir():
                candidates.append(sems.parent)
    unique = sorted(set(p.resolve() for p in candidates))
    if len(unique) == 1:
        return unique[0]
    if len(unique) > 1:
        raise RealDataError(
            "metal-layer SEM の展開先が複数ある: %s — FULLSEYE_SEM_METAL_DATA で 1 つを指定する"
            % ", ".join(str(p) for p in unique))
    if required:
        raise RealDataError(
            "metal-layer SEM データが無い: %s。tools/fetch_sem_metal_layer.py で取得するか、"
            "FULLSEYE_SEM_METAL_DATA を展開先へ向ける" % cache)
    return None


def sem_metal_layer_pairs(limit: int | None = None) -> list[tuple[Path, Path]]:
    """ラベルのある SEM / SVG の組を番号順に返す。

    名前は配布物の ``semNNNN.*`` / ``labelNNNN.svg`` に限る。片方だけの番号を
    黙って落とさず、対応が無ければ :class:`RealDataError` にする。
    """
    root = sem_metal_layer_root(required=True)
    assert root is not None
    sem_dir = root / "sems"
    label_dir = root / "labels"
    nested_sem = sem_dir / "m2"
    nested_label = label_dir / "m2"
    if nested_sem.is_dir() or nested_label.is_dir():
        if not nested_sem.is_dir() or not nested_label.is_dir():
            raise RealDataError("metal-2 の sems / labels 配置が片側だけにある: %s" % root)
        sem_dir, label_dir = nested_sem, nested_label
    sems = {}
    for p in sem_dir.iterdir():
        if p.is_file() and p.stem.startswith("sem") and p.stem[3:].isdigit():
            sems[int(p.stem[3:])] = p
    labels = {}
    for p in label_dir.glob("label*.svg"):
        if p.stem[5:].isdigit():
            labels[int(p.stem[5:])] = p
    missing_image = sorted(set(labels) - set(sems))
    if missing_image:
        raise RealDataError("SVG に対応する SEM が無い番号: %s" % missing_image[:10])
    numbers = sorted(set(sems) & set(labels))
    if not numbers:
        raise RealDataError("ラベルつき SEM が 1 組も無い: %s" % root)
    if limit is not None:
        if not isinstance(limit, int) or limit <= 0:
            raise ValueError("limit must be a positive integer or None")
        numbers = numbers[:limit]
    return [(sems[n], labels[n]) for n in numbers]


def sem_metal_layer_credit() -> str:
    """図と実行ログへ載せるデータセットの帰属表記を返す。"""
    return ("Rothaug et al., A Real-World Metal-Layer SEM Image Dataset with Partial Labels, "
            "Edmond/MPG, DOI %s, %s; paper DOI %s"
            % (SEM_METAL_DATASET_DOI, SEM_METAL_LICENSE, SEM_METAL_PAPER_DOI))

#: 名前 -> (skimage.data の関数名, 種類, ライセンス, 出どころ)
#:
#: ★公開する図に使ってよいのは ``public`` の列が真のものだけ。
#: 研究・教育目的の引用付き利用に留めるものは ``cite`` を持つ。
SAMPLE_PHOTOS = {
    "coins": ("coins", "gray", "No known copyright restrictions",
              "scikit-image (Greek coins from Pompeii, British Museum)", True, None),
    "camera": ("camera", "gray", "CC0 (Lav Varshney)",
               "scikit-image", True, None),
    "clock": ("clock", "gray", "Public domain (Stefan van der Walt)",
              "scikit-image", True, None),
    "brick": ("brick", "gray", "CC0", "CC0Textures / Bricks25", True, None),
    "grass": ("grass", "gray", "CC0", "CC0Textures", True, None),
    "gravel": ("gravel", "gray", "CC0", "CC0Textures", True, None),
    "astronaut": ("astronaut", "rgb", "Public domain (NASA)",
                  "scikit-image", True, None),
    "coffee": ("coffee", "rgb", "CC0 (Rachel Michetti)", "scikit-image", True, None),
    "chelsea": ("chelsea", "rgb", "CC0 (Stefan van der Walt)", "scikit-image", True, None),
    "hubble_deep_field": ("hubble_deep_field", "rgb",
                          "Public domain (NASA/STScI)",
                          "Hubble Deep Field", True, None),
    "immunohistochemistry": ("immunohistochemistry", "rgb",
                             "No known copyright restrictions",
                             "scikit-image (DAB + haematoxylin)", True, None),
    "stereo_motorcycle": ("stereo_motorcycle", "stereo",
                          "Research / educational use with citation",
                          "Middlebury 2014 stereo benchmark", True,
                          "D. Scharstein et al., GCPR 2014"),
}


class RealDataError(RuntimeError):
    """実写サンプルが引けない(未登録名 / scikit-image 不在 / 同梱されていない)。

    ★2026-09-19(GenSpark 第 13 報): ここは以前 ``raise SystemExit(1)`` だった。PoC スクリプトの都合
    (理由を印字して rc 1)だが、``fullseye.sample_photo`` は**公開 API** なので、未登録名を渡した
    呼び手のプロセス(GUI・サービス・テストハーネス)ごと落としていた —— 第三者のスモークでは
    「ワーカープロセスが消滅 = ネイティブクラッシュ」と観測された。fail-closed は例外で守る。
    """


#: 立っていると、:func:`mark_read` が「実データを読んだ」印を 1 行ずつこのファイルへ足す。
#: ``tools/record_real_data_runs.py`` が門と同じ条件(CI と同じく手元のキャッシュ無し)で
#: 例を走らせるときに立て、``docs/real_data_runs.json`` に残す。成熟度台帳の
#: ``validated-public-real-data`` はその記録を見る(``tools/gen_maturity.py``)。
REAL_DATA_LOG_ENV = "FULLSEYE_REAL_DATA_LOG"


def mark_read(dataset: str) -> None:
    """実データ ``dataset`` を**実際に読んだ**ことを記録する(読み終えた直後に呼ぶ)。

    ★2026-11-05(敵対的検証 第 2 巡 D6): 成熟度台帳は「例が ``data: real`` で、門が走らせる」だけで
    ``validated-public-real-data`` を出していた。実データが CI に無い例は、実データの章を飛ばして
    記録値を印字し PASS する —— 2026-11-05 に測ると 19 能力のうち 11 がそうだった。読んだかどうかは例の中でしか
    分からないので、読んだ所で印を残す。環境変数が無いときは何もしない(利用者の出力を汚さない)。
    """
    if not isinstance(dataset, str) or not dataset.strip() or "\n" in dataset:
        raise ValueError("mark_read: dataset は 1 行の空でない名前: %r" % (dataset,))
    path = os.environ.get(REAL_DATA_LOG_ENV, "").strip()
    if not path:
        return
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(dataset.strip() + "\n")


def _data():
    try:
        import skimage.data as _d
    except Exception as exc:                                    # pragma: no cover
        raise RealDataError(
            "実データが引けない: scikit-image が入っていない (%s)。pip install \"fullseye[skimage]\" で入る。"
            "この PoC は実写でしか意味が無いので、黙って通さずここで止める。" % type(exc).__name__) from exc
    return _d


def sample_photo_raw(name: str):
    """実写を 1 つ返す。無ければ**理由を印字して落ちる**(fail-closed)。"""
    if name not in SAMPLE_PHOTOS:
        raise RealDataError("未登録の実データ名: %r (登録済み: %s)"
                            % (name, ", ".join(sorted(SAMPLE_PHOTOS))))
    fn = SAMPLE_PHOTOS[name][0]
    d = _data()
    try:
        out = getattr(d, fn)()
    except Exception as exc:
        # ★skimage は同梱の部分集合しか持っておらず、残りは実行時に
        #   pooch で取りに行く。取りに行けないものは**この repo では使わない**
        #   (PoC が回線に依存すると、落ちた理由が実装かネットワークか
        #   分からなくなる)。
        raise RealDataError("実データ %r を読めなかった: %s: %s — 同梱されていない (pooch のダウンロードが要る) "
                            "可能性が高い" % (name, type(exc).__name__, exc)) from exc
    mark_read("skimage.data:%s" % name)
    return out


def sample_photo(name: str) -> np.ndarray:
    """実写を **float64 / [0, 1] / 2 次元**で返す。"""
    a = np.asarray(sample_photo_raw(name))
    if a.ndim == 3:
        a = a[..., :3] @ np.array([0.2125, 0.7154, 0.0721])
    a = a.astype(np.float64)
    if a.max() > 1.5:
        a = a / 255.0
    return np.clip(a, 0.0, 1.0)


def sample_photo_rgb(name: str) -> np.ndarray:
    """実写を **float64 / [0, 1] / (H, W, 3)** で返す。"""
    a = np.asarray(sample_photo_raw(name)).astype(np.float64)
    if a.ndim == 2:
        a = np.dstack([a] * 3)
    a = a[..., :3]
    if a.max() > 1.5:
        a = a / 255.0
    return np.clip(a, 0.0, 1.0)


def sample_stereo_pair():
    """Middlebury 2014 motorcycle: ``(左, 右, 真値視差)``。

    真値が無い画素は NaN ではなく ``+inf``(実測 +inf 27,226 / 370,500 = 7.3 %、NaN 0)。
    ``np.nanmedian`` などは +inf を数に入れてしまうので、``np.isfinite`` で判定すること。
    視差は 7.19 〜 59.91 px、中央値 38.73 px。

    ★skimage の docstring は ``disp`` を ``(500, 741, 3)`` と書いているが、
    実際に返るのは ``(500, 741)`` —— 実データは注記も含めて確かめること。
    """
    L, R, disp = sample_photo_raw("stereo_motorcycle")
    L = np.asarray(L, np.float64)[..., :3] @ np.array([0.2125, 0.7154, 0.0721])
    R = np.asarray(R, np.float64)[..., :3] @ np.array([0.2125, 0.7154, 0.0721])
    disp = np.asarray(disp, np.float64)
    if disp.ndim == 3:
        disp = disp[..., 0]
    return L / 255.0, R / 255.0, disp


def sample_photo_credit(names) -> str:
    """サンプル写真の名前の列から、公開図に添える帰属表記(出典・ライセンス)を組み立てる。

    1 行 1 枚で ``名前 — 出典 (ライセンス) [引用]`` を改行で連ねた文字列を返す。
    """
    out = []
    for n in names:
        _fn, _k, lic, src, _pub, cite = SAMPLE_PHOTOS[n]
        line = "%s — %s (%s)" % (n, src, lic)
        if cite:
            line += " [%s]" % cite
        out.append(line)
    return chr(10).join(out)


# ---------------------------------------------------------------------------
# libE57 の公開試験点群(E57 の読み手の採点用。再配布の条件が書かれていないので同梱しない)
# ---------------------------------------------------------------------------
#: 取得元の URL は配布物に入れず、取得道具 ``tools/fetch_e57_bunny.py`` の ``E57_BUNNY_URL`` に置く
#: (配布されるのは照合用のバイト数と SHA-256 だけ)。
#: 同じ点(Stanford bunny 由来の 30,571 点)を 6 つの数値型で格納した E57 の型名。
E57_BUNNY_KINDS = ("Double", "Float", "Int32", "Int24", "Int21", "Int19")
#: ファイル名 → (バイト数, SHA-256)。2026-11-04 に上の URL から取得した値。``bunnyData.pts`` は
#: 同じ点の文字版(真値として使う)。
E57_BUNNY_FILES = {
    "bunnyDouble.e57": (743424, "5ec10af7a8b4cf7778d247ea20b2c3058e6488b55ef102ae187373d5cbe8b056"),
    "bunnyFloat.e57": (374784, "ed48ac81e9e79c00a14950f6d00c8f93b0a7df0b400a01e85d488d9ddea11660"),
    "bunnyInt32.e57": (374784, "6b3696c452a2dd0e325ab30b1ad28a40de87f1a56cd9d8a24ad81389b606c205"),
    "bunnyInt24.e57": (282624, "11fe6c4bbddc44b0e8e825a782dee56f7deae5a47c4251dc8248cfb8c80c3c9c"),
    "bunnyInt21.e57": (248832, "671d1f169fb9db0b5729af3b8d1fbc96e1585b21448ec25d6ce3f06bb9af1e2a"),
    "bunnyInt19.e57": (225280, "71375f94ea8e35dbdcec1595117461ee8f24047705bf951f64b4cea2a93a3154"),
    "bunnyData.pts": (880566, "2bc55437d6c3a6b3fbf6e63e9f909a6ab9e0bf73cc43628e243d720a6e04d40f"),
}


def e57_bunny_cache() -> Path:
    """libE57 の bunny 一式の repo 外キャッシュ先(``FULLSEYE_E57_BUNNY_DATA`` で上書き)。

    開発 worktree が ``<root>/projects/<checkout>`` にあれば ``<root>/data/realdata/e57_bunny``、
    それ以外はユーザーキャッシュ。ローカル絶対パスをソースに焼き込まないための分岐
    (:func:`sem_metal_layer_cache` と同じ形)。
    """
    configured = os.environ.get("FULLSEYE_E57_BUNNY_DATA", "").strip()
    if configured:
        return Path(configured).expanduser()
    here = Path(__file__).resolve().parent
    if here.parent.name.lower() == "projects":
        return here.parent.parent / "data" / "realdata" / "e57_bunny"
    return Path.home() / ".cache" / "fullseye" / "e57_bunny"


def _sha256_file(path: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def e57_bunny_files(*, required: bool = True) -> dict[str, Path] | None:
    """取得済みの bunny 一式を、バイト数と SHA-256 を照合してから返す。

    1 つも無ければ ``required=False`` で ``None``(CI の既定)。一部だけ在る・中身が違う場合は
    黙って使わず :class:`RealDataError` にする(取得物は untrusted として照合してから読む)。
    """
    cache = e57_bunny_cache()
    present = {name: cache / name for name in E57_BUNNY_FILES if (cache / name).is_file()}
    if not present:
        if required:
            raise RealDataError("libE57 の bunny 一式が無い: %s。tools/fetch_e57_bunny.py で取得する" % cache)
        return None
    if len(present) != len(E57_BUNNY_FILES):
        missing = sorted(set(E57_BUNNY_FILES) - set(present))
        raise RealDataError("libE57 の bunny 一式が欠けている(%s): %s" % (", ".join(missing), cache))
    for name, (size, digest) in E57_BUNNY_FILES.items():
        path = present[name]
        if path.stat().st_size != size:
            raise RealDataError("%s のバイト数 %d が台帳 %d と違う" % (path, path.stat().st_size, size))
        got = _sha256_file(path)
        if got != digest:
            raise RealDataError("%s の SHA-256 %s が台帳と違う" % (path, got))
    return present


# --------------------------------------------------------------------------- #
# 実測のコーンビーム CT: クルミ(Der Sarkissian ほか 2019、CC BY 4.0)
# --------------------------------------------------------------------------- #
#: Zenodo のレコード(標本 1〜8)。``tools/fetch_walnut_cbct.py`` が標本 1 の zip から一部だけ取る。
WALNUT_CBCT_RECORD = "https://zenodo.org/records/2686726"
WALNUT_CBCT_URL = "https://zenodo.org/api/records/2686726/files/Walnut1.zip/content"
#: zip の大きさ(Zenodo の API が返した値。md5 は ``0ecd525f245e3029788538a44f5491e3``、全体を取らないので
#: 照合は要素ごとの CRC-32 と下の一覧の SHA-256 で行う)。
WALNUT_CBCT_ZIP_BYTES = 6_058_580_169
WALNUT_CBCT_DATASET_DOI = "10.5281/zenodo.2686726"
WALNUT_CBCT_PAPER_DOI = "10.1038/s41597-019-0235-y"
#: 配布元(Zenodo record 2686726)の記載のまま: "Creative Commons Attribution 4.0 International"。
WALNUT_CBCT_LICENSE = "CC BY 4.0 (Creative Commons Attribution 4.0 International)"
#: 使う標本と軌道(2 = 中段の線源位置。配布元の FDK 参照 ``fdk_pos2`` と同じ軌道)。
WALNUT_CBCT_SAMPLE = 1
WALNUT_CBCT_ORBIT = 2
#: 投影の間引き: 1200 枚から 4 枚に 1 枚(配布元の ``angluar_sub_sampling`` と同じ数え方)。
WALNUT_CBCT_ANGULAR_STEP = 4
#: 同じ角度を 2 度撮った投影(0 番と 1200 番は同じ角度。配布元の FDK スクリプトの注記)。差が雑音だけになる。
WALNUT_CBCT_REPEAT_INDEX = 0
#: 配布元の参照再構成: 3 軌道すべてを使った非負最小二乗(Nesterov 50 回)と、軌道 2 の FDK。
WALNUT_CBCT_RECONSTRUCTIONS = ("full_AGD_50", "fdk_pos2")
WALNUT_CBCT_REFERENCE_SLICES = 501
#: 取得物の一覧(名前・大きさ・SHA-256)の SHA-256。2026-11-07 に取得して固定した値。
WALNUT_CBCT_MANIFEST_SHA256 = "af0d0d5cda5d55eb8e602c572bf1dd610eabeca9d892009e98975e0c3163c24d"
WALNUT_CBCT_MANIFEST = "manifest_sha256.json"


def walnut_cbct_projection_indices() -> list[int]:
    """取得する投影のファイル番号(配布元の FDK スクリプトと同じく逆順: 1200, 1196, ...)。"""
    return list(range(1200, 0, -WALNUT_CBCT_ANGULAR_STEP))


def walnut_cbct_cache() -> Path:
    """クルミ CT の repo 外キャッシュ先(``FULLSEYE_WALNUT_CBCT_DATA`` で上書き)。

    開発 worktree が ``<root>/projects/<checkout>`` にあれば ``<root>/data/fullseye_poc_real/walnut_cbct``、
    それ以外はユーザーキャッシュ(:func:`sem_metal_layer_cache` と同じ形)。
    """
    configured = os.environ.get("FULLSEYE_WALNUT_CBCT_DATA", "").strip()
    if configured:
        return Path(configured).expanduser()
    here = Path(__file__).resolve().parent
    if here.parent.name.lower() == "projects":
        return here.parent.parent / "data" / "fullseye_poc_real" / "walnut_cbct"
    return Path.home() / ".cache" / "fullseye" / "walnut_cbct"


def _walnut_manifest_bytes(rows) -> bytes:
    import json as _json

    return _json.dumps(rows, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode("ascii")


def walnut_cbct_write_manifest(root: Path, names) -> str:
    """取得した全要素の (名前, 大きさ, SHA-256) を書き、その SHA-256 を返す(取得道具が呼ぶ)。"""
    rows = []
    for name in sorted(names):
        p = Path(root) / name
        rows.append([name, p.stat().st_size, _sha256_file(p)])
    raw = _walnut_manifest_bytes(rows)
    (Path(root) / WALNUT_CBCT_MANIFEST).write_bytes(raw)
    import hashlib

    return hashlib.sha256(raw).hexdigest()


def walnut_cbct_root(*, required: bool = True, root: Path | None = None, deep: bool = True) -> Path | None:
    """取得済みのクルミ CT の置き場を、一覧の SHA-256(と各要素の SHA-256)を照合してから返す。

    無ければ ``required=False`` で ``None``(CI の既定)。一覧が台帳と違う・要素が欠ける・中身が
    違う場合は黙って使わず :class:`RealDataError` にする(取得物は untrusted として照合してから読む)。
    """
    import hashlib
    import json as _json

    root = Path(root) if root is not None else walnut_cbct_cache()
    mpath = root / WALNUT_CBCT_MANIFEST
    if not mpath.is_file():
        if required:
            raise RealDataError("クルミ CT が無い: %s。tools/fetch_walnut_cbct.py で取得する" % root)
        return None
    raw = mpath.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if WALNUT_CBCT_MANIFEST_SHA256 is None or digest != WALNUT_CBCT_MANIFEST_SHA256:
        raise RealDataError("クルミ CT の一覧の SHA-256 %s が台帳 %s と違う" % (digest, WALNUT_CBCT_MANIFEST_SHA256))
    rows = _json.loads(raw.decode("ascii"))
    for name, size, sha in rows:
        p = root / name
        if not p.is_file() or p.stat().st_size != size:
            raise RealDataError("クルミ CT の要素が欠けている / 大きさが違う: %s" % name)
        if deep and _sha256_file(p) != sha:
            raise RealDataError("クルミ CT の要素の SHA-256 が一覧と違う: %s" % name)
    return root


def walnut_cbct_credit() -> str:
    """クルミのコーンビーム CT の帰属表記(論文とデータの DOI、ライセンス)を返す。図と実行ログへ載せる。"""
    return ("Der Sarkissian, Lucka, van Eijnatten, Colacicco, Coban & Batenburg, A cone-beam X-ray CT data "
            "collection designed for machine learning, Sci. Data 6, 215 (2019), doi:%s; data doi:%s, %s"
            % (WALNUT_CBCT_PAPER_DOI, WALNUT_CBCT_DATASET_DOI, WALNUT_CBCT_LICENSE))


# ---------------------------------------------------------------------------
# DTU の PV 発電所のドローン熱画像(CC BY 4.0、太陽光の熱画像点検の PoC が読む)
# ---------------------------------------------------------------------------
#: Del Prado Santamaría ほか、DTU Data(figshare)の「DTU PV plant - Drone Infrared Thermography
#: Dataset: Influence of Irradiance and Altitude」。故障の種類(EL 画像と IV 曲線で確かめた)ごとに
#: モジュールを分け、各モジュールを 4 つの日射(200 / 600 / 800 / 800 超 W/m²)と 4 つの高さ
#: (8 / 10 / 14 / 20 m)で撮った温度の画像(.raw = float32、605 x 363、°C)。
#: 原本は repo に入れず ``tools/fetch_dtu_pv_irt.py`` が取得して展開する。
DTU_PV_IRT_DOI = "10.11583/DTU.29665346.v1"
DTU_PV_IRT_LICENSE = "CC BY 4.0"
DTU_PV_IRT_BYTES = 642_610_942
#: 2026-11-08 に取得した ``IRT DATASET.7z`` の SHA-256(配布元の MD5 2ca8adbcf45639f6eefc668eceac3fe7 とも一致)。
DTU_PV_IRT_SHA256 = "3af1c066145fb4fc0ff80b7acf02d84b238b5d83c65c686364c01a9f1afb63c3"
DTU_PV_IRT_SHAPE = (605, 363)
DTU_PV_IRT_ALTITUDES = (8, 10, 14, 20)
DTU_PV_IRT_IRRADIANCES = ("200", "600", "800", "abv800")


def dtu_pv_irt_cache() -> Path:
    """DTU の PV 熱画像の repo 外の置き場(``FULLSEYE_PV_IRT_DATA`` で上書き)。

    開発 worktree が ``<root>/projects/<checkout>`` にあれば ``<root>/data/fullseye_poc_real/dtu_pv_irt``、
    それ以外はユーザーキャッシュ(:func:`sem_metal_layer_cache` と同じ形。手元の絶対パスを焼き込まない)。
    """
    configured = os.environ.get("FULLSEYE_PV_IRT_DATA", "").strip()
    if configured:
        return Path(configured).expanduser()
    here = Path(__file__).resolve().parent
    if here.parent.name.lower() == "projects":
        return here.parent.parent / "data" / "fullseye_poc_real" / "dtu_pv_irt"
    return Path.home() / ".cache" / "fullseye" / "dtu_pv_irt"


def dtu_pv_irt_root(*, required: bool = True) -> Path | None:
    """展開済みの ``IRT DATASET`` の dir。無ければ ``required=False`` で ``None``(CI の既定)。"""
    cache = dtu_pv_irt_cache()
    for cand in (cache / "extracted" / "IRT DATASET", cache / "IRT DATASET"):
        if cand.is_dir():
            return cand
    if required:
        raise RealDataError("DTU の PV 熱画像が無い: %s。tools/fetch_dtu_pv_irt.py で取得する" % cache)
    return None


def dtu_pv_irt_frame(category: str, module: int, altitude_m: int, irradiance: str) -> Path:
    """故障の種類の dir 名・モジュール番号・高さ・日射の組の ``.raw`` を 1 つだけ返す(0 個 / 2 個以上は例外)。

    配布物のファイル名は 2 つの形がある: 故障の 5 種は ``T10_10m_200_APV771.raw``(高さ → 日射)、
    汚れの 2 種は ``T_200_10m - Copy_PD.raw`` / ``T_800_10m_PD.png_S1.raw``(日射 → 高さ、後ろに
    任意の飾り)。★2026-11-08 までは前者の形しか見ておらず、汚れの 144 枚が読み口に合わずに集計から
    黙って外れていた(敵対的レビューの指摘)。2 つの形は先頭(``T10_`` か ``T_<日射>_``)が違うので
    互いに混ざらない —— 故障の 5 種の選択は前と同じ。
    """
    import re

    if altitude_m not in DTU_PV_IRT_ALTITUDES or irradiance not in DTU_PV_IRT_IRRADIANCES:
        raise ValueError("altitude / irradiance が配布物の条件に無い: %r %r" % (altitude_m, irradiance))
    root = dtu_pv_irt_root(required=True)
    assert root is not None
    folder = root / category / ("Module %d" % int(module)) / "IRT"
    pat = re.compile(r"_%dm_%s(_|\.raw$)" % (int(altitude_m), re.escape(irradiance)))
    pat_soil = re.compile(r"^T_%s_%dm[ _.]" % (re.escape(irradiance), int(altitude_m)))
    hits = sorted(p for p in folder.glob("*.raw") if pat.search(p.name) or pat_soil.match(p.name))
    if len(hits) != 1:
        raise RealDataError("%s の %d m・%s の .raw が %d 個(1 個のはず)" % (folder, altitude_m, irradiance, len(hits)))
    return hits[0]


def dtu_pv_irt_load(path: Path) -> np.ndarray:
    """``.raw``(float32、605 x 363、°C)を読む。バイト数が違えば黙って読まず例外。"""
    path = Path(path)
    want = DTU_PV_IRT_SHAPE[0] * DTU_PV_IRT_SHAPE[1] * 4
    if path.stat().st_size != want:
        raise RealDataError("%s のバイト数 %d が %d(605 x 363 の float32)と違う" % (path, path.stat().st_size, want))
    a = np.fromfile(path, dtype="<f4").reshape(DTU_PV_IRT_SHAPE).astype(np.float64)
    if not np.all(np.isfinite(a)) or a.min() < -60.0 or a.max() > 150.0:
        raise RealDataError("%s の温度が範囲外(-60〜150 °C)" % path)
    return a


def dtu_pv_irt_credit() -> str:
    """DTU の PV 熱画像の帰属表記(著者・題・DOI・CC BY 4.0)を 1 行の文字列で返す。図のキャプションと実行ログに載せる。"""
    return ("R. del Prado Santamaría et al., DTU PV plant - Drone Infrared Thermography Dataset: "
            "Influence of Irradiance and Altitude, DTU Data, doi:%s (%s)" % (DTU_PV_IRT_DOI, DTU_PV_IRT_LICENSE))


if __name__ == "__main__":                                      # pragma: no cover
    ok, ng = [], []
    for name in sorted(SAMPLE_PHOTOS):
        try:
            sample_photo_raw(name)
            ok.append(name)
        except SystemExit:
            ng.append(name)
    print("引けた %d / 引けない %d" % (len(ok), len(ng)))
    for n in ng:
        print("  x", n)
    sys.exit(1 if ng else 0)
