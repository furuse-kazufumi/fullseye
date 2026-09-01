# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""palette — 図の配色を「役割」で決める(色を直接選ばない)。

## なぜ op にするのか

図を作るたびに作者が色を選ぶと、**同じ意味に違う色が付く**。実際この repo でも、
ある展示は「赤枠 = 誤り / 緑枠 = 正しい」で描かれ、別の展示は同じ意味を
青-黒-橙で描いていた。どちらが良いかを図ごとに議論しても片付かない ――
**流儀を 1 か所に置いて、図はそれを引くだけ**にするのが筋。

だからここでは色を返すのではなく、**役割に色を割り当てる**:

    p = semantic_palette()
    ok, ng = p["right"], p["wrong"]      # 図は「正しい/誤り」としか言わない

流儀を変えたいときは `scheme=` を変える。図のコードは 1 行も直らない。

## 既定が Okabe–Ito である理由

既定の `"okabe_ito"` は、色覚特性の違いを前提に選ばれた 8 色の定性パレット
(Okabe & Ito, *Color Universal Design*, 2008)。**赤と緑を対にしない**のが要点で、
`right`/`wrong` には青系と橙/朱系が割り当たる。日本人男性の約 5 % が
赤緑の識別に困難を持つので、**「赤 = 誤り / 緑 = 正しい」は情報量ゼロになりうる**。

`"blue_orange"` は同じ思想の 2 色版(発散データ向け)、`"red_green"` は
**互換のためだけに残してある**(既存の図を再現する必要があるとき)。
既定にはしない。

## 色だけに意味を載せない

パレットを使っても、**色だけが唯一の手掛かりなら不十分**。`ROLE_MARKERS` は
各役割に記号を対応させるので、キャプションや凡例に併記できる:

    f"{ROLE_MARKERS['wrong']} spacing なし"     # -> "× spacing なし"

`assert_not_red_green_pair` は「その配色が赤緑の対になっていないか」を機械で
検査する。新しい scheme を足すときの歯止め。
"""
from __future__ import annotations

import numpy as np

#: 役割の名前。図はこれ以外の言葉で色を指さない。
ROLES = ("right", "wrong", "neutral", "emphasis", "baseline", "reference")

#: 色覚特性を前提に選ばれた定性パレット(Okabe & Ito 2008)。赤と緑を対にしない。
_OKABE_ITO = {
    "orange": (0.902, 0.624, 0.000),
    "sky": (0.337, 0.706, 0.914),
    "green": (0.000, 0.620, 0.451),
    "yellow": (0.941, 0.894, 0.259),
    "blue": (0.000, 0.447, 0.698),
    "vermillion": (0.835, 0.369, 0.000),
    "purple": (0.800, 0.475, 0.655),
    "black": (0.000, 0.000, 0.000),
}

_SCHEMES: dict[str, dict[str, tuple[float, float, float]]] = {
    # 既定。right=青 / wrong=朱 ―― 明度も離れているので白黒印刷でも分かれる。
    "okabe_ito": {
        "right": _OKABE_ITO["sky"],
        "wrong": _OKABE_ITO["vermillion"],
        "neutral": (0.62, 0.62, 0.66),
        "emphasis": _OKABE_ITO["orange"],
        "baseline": _OKABE_ITO["purple"],
        "reference": _OKABE_ITO["blue"],
    },
    # 発散データ(符号つきの差)向けの 2 色版。
    "blue_orange": {
        "right": (0.20, 0.55, 0.90),
        "wrong": (0.95, 0.55, 0.10),
        "neutral": (0.60, 0.60, 0.64),
        "emphasis": (1.00, 0.75, 0.20),
        "baseline": (0.55, 0.45, 0.75),
        "reference": (0.10, 0.35, 0.70),
    },
    # 互換のためだけ。既定にはしない(赤緑の対は色覚特性で潰れる)。
    "red_green": {
        "right": (0.20, 0.75, 0.35),
        "wrong": (0.90, 0.25, 0.25),
        "neutral": (0.60, 0.60, 0.64),
        "emphasis": (1.00, 0.80, 0.20),
        "baseline": (0.55, 0.45, 0.75),
        "reference": (0.30, 0.45, 0.85),
    },
}

#: 色だけに意味を載せないための記号。キャプション・凡例に併記する。
ROLE_MARKERS = {
    "right": "○", "wrong": "×", "neutral": "・",
    "emphasis": "★", "baseline": "—", "reference": "▷",
}

SCHEMES = tuple(sorted(_SCHEMES))


def semantic_palette(scheme: str = "okabe_ito") -> dict[str, tuple[float, float, float]]:
    """役割 → RGB float [0,1] の対応を返す。

    Raises ValueError: 未知の scheme(黙って既定へ落とすと、流儀が割れていることに
    誰も気づけない)。
    """
    if scheme not in _SCHEMES:
        raise ValueError(f"unknown scheme {scheme!r}; known: {', '.join(SCHEMES)}")
    return dict(_SCHEMES[scheme])


def role_color(role: str, scheme: str = "okabe_ito") -> tuple[float, float, float]:
    """1 つの役割の色。``semantic_palette(scheme)[role]`` と同じ。"""
    pal = semantic_palette(scheme)
    if role not in pal:
        raise ValueError(f"unknown role {role!r}; known: {', '.join(ROLES)}")
    return pal[role]


def role_rgb8(role: str, scheme: str = "okabe_ito") -> tuple[int, int, int]:
    """PIL / imagedraw にそのまま渡せる 0–255 の整数三つ組。"""
    return tuple(int(round(c * 255.0)) for c in role_color(role, scheme))


def diverging_lut(n: int = 256, scheme: str = "blue_orange") -> np.ndarray:
    """符号つきの量を塗る発散 LUT ``(n, 3)`` float [0,1]。中央は黒に寄せる。

    赤-緑の発散マップは、色覚特性によっては**中央と両端の区別が消える**。
    ここは ``wrong``(負側)→ 暗中央 → ``right``(正側)で組む。
    """
    if n < 2:
        raise ValueError(f"n must be >= 2, got {n}")
    pal = semantic_palette(scheme)
    lo = np.asarray(pal["wrong"], np.float64)
    hi = np.asarray(pal["right"], np.float64)
    mid = np.full(3, 0.06)
    t = np.linspace(-1.0, 1.0, int(n))[:, None]
    neg = mid + (lo - mid) * (-t)
    pos = mid + (hi - mid) * t
    return np.clip(np.where(t < 0.0, neg, pos), 0.0, 1.0)


def assert_not_red_green_pair(scheme: str = "okabe_ito") -> None:
    """``right`` と ``wrong`` が赤緑の対になっていないことを検査する。

    新しい scheme を足すときの歯止め。``"red_green"`` は互換用なので対象外だが、
    **既定に選べないこと**をここで担保する。

    Raises ValueError: 対が赤緑だった場合。
    """
    if scheme == "red_green":
        raise ValueError("'red_green' is kept only for compatibility; never make it the default")
    pal = semantic_palette(scheme)
    r_ok, g_ok, b_ok = pal["right"]
    r_ng, g_ng, b_ng = pal["wrong"]
    right_is_green = g_ok > r_ok + 0.15 and g_ok > b_ok + 0.15
    wrong_is_red = r_ng > g_ng + 0.15 and r_ng > b_ng + 0.15
    if right_is_green and wrong_is_red:
        raise ValueError(
            f"scheme {scheme!r} pairs green with red for right/wrong — that pair carries no "
            "information for a red-green colour vision deficiency; pick hues that differ in "
            "lightness as well as hue")
