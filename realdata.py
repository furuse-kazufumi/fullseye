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
:func:`sample_stereo_pair` が ``(左, 右, 真値視差)`` を返す形で、真値の NaN は
「真値が無い画素」を表します(Middlebury の規約)。
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
        return getattr(d, fn)()
    except Exception as exc:
        # ★skimage は同梱の部分集合しか持っておらず、残りは実行時に
        #   pooch で取りに行く。取りに行けないものは**この repo では使わない**
        #   (PoC が回線に依存すると、落ちた理由が実装かネットワークか
        #   分からなくなる)。
        raise RealDataError("実データ %r を読めなかった: %s: %s — 同梱されていない (pooch のダウンロードが要る) "
                            "可能性が高い" % (name, type(exc).__name__, exc)) from exc


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

    真値の NaN は「真値が無い画素」(実測 27,226 / 370,500 = 7.3 %)。
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
