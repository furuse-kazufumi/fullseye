# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""実写データの取り口(合成ではないものだけ)。

## なぜ要るか(2026-09-08)

この repo の PoC は**自分で真値を仕込む**規律で書いてある —— 合成なら
「答え」がデータの外に無く、崖も対照群も設計できるからです。ただし合成は
**自分が知っている壊れ方しか作れない**。スケール依存のしきい値、退化した
入力、規約(符号・参照画像・NaN)の食い違いは、実写を通した瞬間に出ます。

そこでこの module は、**追加ダウンロード無しで手元にある実写**だけを
返します。出どころは ``scikit-image`` に同梱されている小さな部分集合で、
ライセンスは下の :data:`CATALOGUE` に 1 件ずつ書いてあります(CC0 /
public domain / no known copyright restrictions のものだけを公開図に使う)。

## fail-closed

**データが無いときに黙って通さない**。:func:`require` は理由を印字して
``SystemExit(1)`` します —— 「実データが無かったので何も検査せず PASS」は、
この repo がいちばん嫌う形(記録は在るのに誰も読まない門)そのものなので。

CI では ``skimage`` extra が 3 つの matrix 全部に入るので、実データ PoC は
**必ず走ります**。手元で extra を入れていない場合だけ落ちます。

EXTEND: 自前の撮影に差し替えるなら :func:`load_gray` の戻り値
(float64 / [0, 1] / 2 次元)に合わせてください。ステレオは
:func:`stereo_pair` が ``(左, 右, 真値視差)`` を返す形で、真値の NaN は
「真値が無い画素」を表します(Middlebury の規約)。
"""
from __future__ import annotations

import sys

import numpy as np

#: 名前 -> (skimage.data の関数名, 種類, ライセンス, 出どころ)
#:
#: ★公開する図に使ってよいのは ``public`` の列が真のものだけ。
#: 研究・教育目的の引用付き利用に留めるものは ``cite`` を持つ。
CATALOGUE = {
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


def _data():
    try:
        import skimage.data as _d
    except Exception as exc:                                    # pragma: no cover
        print("実データが引けない: scikit-image が入っていない (%s)。"
              % type(exc).__name__)
        print("  pip install -e \".[skimage]\" で入る。")
        print("この PoC は実写でしか意味が無いので、黙って通さずここで止める。")
        raise SystemExit(1)
    return _d


def require(name: str):
    """実写を 1 つ返す。無ければ**理由を印字して落ちる**(fail-closed)。"""
    if name not in CATALOGUE:
        print("未登録の実データ名: %r (登録済み: %s)"
              % (name, ", ".join(sorted(CATALOGUE))))
        raise SystemExit(1)
    fn = CATALOGUE[name][0]
    d = _data()
    try:
        return getattr(d, fn)()
    except Exception as exc:
        # ★skimage は同梱の部分集合しか持っておらず、残りは実行時に
        #   pooch で取りに行く。取りに行けないものは**この repo では使わない**
        #   (PoC が回線に依存すると、落ちた理由が実装かネットワークか
        #   分からなくなる)。
        print("実データ %r を読めなかった: %s: %s" % (name, type(exc).__name__, exc))
        print("  同梱されていない (pooch のダウンロードが要る) 可能性が高い。")
        raise SystemExit(1)


def load_gray(name: str) -> np.ndarray:
    """実写を **float64 / [0, 1] / 2 次元**で返す。"""
    a = np.asarray(require(name))
    if a.ndim == 3:
        a = a[..., :3] @ np.array([0.2125, 0.7154, 0.0721])
    a = a.astype(np.float64)
    if a.max() > 1.5:
        a = a / 255.0
    return np.clip(a, 0.0, 1.0)


def load_rgb(name: str) -> np.ndarray:
    """実写を **float64 / [0, 1] / (H, W, 3)** で返す。"""
    a = np.asarray(require(name)).astype(np.float64)
    if a.ndim == 2:
        a = np.dstack([a] * 3)
    a = a[..., :3]
    if a.max() > 1.5:
        a = a / 255.0
    return np.clip(a, 0.0, 1.0)


def stereo_pair():
    """Middlebury 2014 motorcycle: ``(左, 右, 真値視差)``。

    真値の NaN は「真値が無い画素」(実測 27,226 / 370,500 = 7.3 %)。
    視差は 7.19 〜 59.91 px、中央値 38.73 px。

    ★skimage の docstring は ``disp`` を ``(500, 741, 3)`` と書いているが、
    実際に返るのは ``(500, 741)`` —— 実データは注記も含めて確かめること。
    """
    L, R, disp = require("stereo_motorcycle")
    L = np.asarray(L, np.float64)[..., :3] @ np.array([0.2125, 0.7154, 0.0721])
    R = np.asarray(R, np.float64)[..., :3] @ np.array([0.2125, 0.7154, 0.0721])
    disp = np.asarray(disp, np.float64)
    if disp.ndim == 3:
        disp = disp[..., 0]
    return L / 255.0, R / 255.0, disp


def attribution(names) -> str:
    """公開図に添える帰属表記を組み立てる。"""
    out = []
    for n in names:
        _fn, _k, lic, src, _pub, cite = CATALOGUE[n]
        line = "%s — %s (%s)" % (n, src, lic)
        if cite:
            line += " [%s]" % cite
        out.append(line)
    return chr(10).join(out)


if __name__ == "__main__":                                      # pragma: no cover
    ok, ng = [], []
    for name in sorted(CATALOGUE):
        try:
            require(name)
            ok.append(name)
        except SystemExit:
            ng.append(name)
    print("引けた %d / 引けない %d" % (len(ok), len(ng)))
    for n in ng:
        print("  x", n)
    sys.exit(1 if ng else 0)
