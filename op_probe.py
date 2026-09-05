# -*- coding: utf-8 -*-
"""op を試すための、**その sort が実際に運ぶ値**を作る。

op を 1 つ手に取ったとき、最初の壁は「何を渡せばいいのか」である。
``in_sort`` は ``"points"`` や ``"lightfield"`` や ``"beatcube"`` まであり、
名前だけでは形が分からない。ここはその 1 行を提供する::

    import op_probe, fullseye
    v = op_probe.sample_input("points")
    out = fullseye.apply(v, "tb_estimate_point_normals")

生成器の**正本は ``tools/chain_fuzz.make_generators()``**(台帳の型ごとの
代表値を作る、ファザーが使っているもの)。ここはそれを op レジストリの
``in_sort`` へ写し、chain_fuzz が持たない sort(``region`` / ``contour`` /
``color``)を足すだけの薄い層。

``structured=True`` は**乱数でない**代表値を返す。乱数だけで試すと
「対称性の破れ」が隠れる —— 円も矩形も斜めエッジも無い一様乱数では、
方向を見る op も形を選ぶ op も差が出ず、**壊れていることに気づけない**。
検査で op の挙動を測るときは、必ず両方を通すこと。
"""
from __future__ import annotations

import os
import sys
import zlib

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))

#: op レジストリの ``in_sort`` → ``chain_fuzz`` の生成器名。
#: ここに無い sort は下の :func:`sample_input` が自前で作る(作れなければ ``None``)。
SORT_TO_GENERATOR = {
    "image": "image2d", "points": "points", "volume": "voxel", "signal": "signal",
    "matrix": "matrix", "cimage": "cimage", "lightfield": "lightfield",
    "counts": "counts", "rgbimage": "rgbimage", "video": "video",
    "qimage": "qimage", "beatcube": "beatcube", "keypoints": "keypoints",
}

#: ``chain_fuzz`` を通さず、ここで直接作る sort。
LOCAL_SORTS = ("region", "contour", "color", "any")

_CONTOUR_CACHE: dict[bool, object] = {}


def _generators():
    tools = os.path.join(_HERE, "tools")
    if tools not in sys.path:
        sys.path.insert(0, tools)
    import chain_fuzz                                     # noqa: PLC0415
    return chain_fuzz.make_generators()


def structured_image(n: int = 48) -> np.ndarray:
    """円 + 矩形 + 斜めエッジ + 勾配。**一様乱数には無い構造**を持つ画像。

    方向(斜めエッジ)・閉じた形(円)・直線的な境界(矩形)・なだらかな変化(勾配)を
    1 枚に入れてある。どれか 1 つでも欠けると、それを見る種類の op で差が出ない。
    """
    y, x = np.mgrid[0:n, 0:n]
    s = np.zeros((n, n))
    s[(x - n // 3) ** 2 + (y - n // 3) ** 2 < (n // 5) ** 2] = 1.0
    s[int(n * 0.62):int(n * 0.87), int(n * 0.17):int(n * 0.83)] = 0.7
    s += 0.25 * (x > y)
    s += 0.3 * (x / float(n - 1))
    return np.clip(s, 0.0, 1.0)


def structured_region(n: int = 48) -> np.ndarray:
    """穴つき 2 連結成分の二値領域。面積・穴数・凸性のどれでも差が出る形。"""
    b = np.zeros((n, n))
    b[int(n * .2):int(n * .5), int(n * .2):int(n * .62)] = 1.0
    b[int(n * .58):int(n * .83), int(n * .42):int(n * .92)] = 1.0
    b[int(n * .3):int(n * .4), int(n * .3):int(n * .4)] = 0.0
    return b


def _contour(structured: bool, rng):
    """実物の contour 値(``{"shape", "cs"}``)を、contour を出す op に作らせる。

    形を手で書き下さないのは、**contour の内部表現が変わったときに
    ここだけ古くなる**のを避けるため(生成側の op が単一の真実源)。
    """
    key = bool(structured)
    if key not in _CONTOUR_CACHE:
        import ops                                        # noqa: PLC0415
        producer = next((o for o in ops.REGISTRY if o.name == "sk_find_contours"), None)
        if producer is None:                              # skimage 不在
            return None
        v = structured_region() if structured else (rng.random((48, 48)) > 0.5).astype(float)
        _CONTOUR_CACHE[key] = producer.fn(v, 0.5, 0.5)
    return _CONTOUR_CACHE[key]


def structured_volume(n: int = 16) -> np.ndarray:
    """球 + 直方体 + 平面。voxel の乱数には無い「連結した塊」を持つ体積。"""
    z, y, x = np.mgrid[0:n, 0:n, 0:n]
    v = np.zeros((n, n, n))
    c = n // 3
    v[(x - c) ** 2 + (y - c) ** 2 + (z - c) ** 2 < (n // 4) ** 2] = 1.0
    v[int(n * .55):int(n * .85), int(n * .2):int(n * .7), int(n * .3):int(n * .8)] = 0.6
    v += 0.2 * (z / float(n - 1))
    return np.clip(v, 0.0, 1.0)


def structured_points(m: int = 160) -> np.ndarray:
    """平面 + 球殻の点群。法線も曲率もクラスタ数も、乱数の雲とは別の値になる。"""
    k = m // 2
    t = np.linspace(0.0, 1.0, k)
    plane = np.stack([t, (t * 3.0) % 1.0, np.zeros(k)], axis=1)
    phi = np.linspace(0.0, np.pi, m - k)
    th = np.linspace(0.0, 6.0 * np.pi, m - k)
    shell = np.stack([0.3 * np.sin(phi) * np.cos(th) + 0.5,
                      0.3 * np.sin(phi) * np.sin(th) + 0.5,
                      0.3 * np.cos(phi) + 0.8], axis=1)
    return np.concatenate([plane, shell], axis=0)


def structured_signal(n: int = 256) -> np.ndarray:
    """チャープ + 段差 + 直流。周波数を見る op も段差を見る op も差が出る。"""
    t = np.linspace(0.0, 1.0, n)
    s = 0.5 + 0.3 * np.sin(2.0 * np.pi * (2.0 + 18.0 * t) * t)
    s[n // 2:] += 0.15
    return np.clip(s, 0.0, 1.0)


#: 構造版を作れる sort(ここに無い sort は :func:`sample_pair` が独立な乱数を 2 本使う)
STRUCTURED_SORTS = ("image", "any", "region", "contour", "color", "rgbimage",
                    "volume", "points", "signal")


def sample_input(sort: str, rng=None, structured: bool = False):
    """``sort`` が運ぶ値を 1 つ返す。作れない sort は ``None``。

    *structured* が真なら、乱数でない代表値(作れる sort のみ。作れなければ
    乱数を返す —— **黙って乱数に落ちる**ので、検査では
    :func:`sample_pair` を使って両方を明示的に通すこと)。
    """
    rng = np.random.default_rng(0) if rng is None else rng
    if sort in ("image", "any"):
        return structured_image() if structured else _generators()["image2d"](rng)
    if sort == "region":
        return structured_region() if structured else (rng.random((48, 48)) > 0.5).astype(float)
    if sort == "contour":
        return _contour(structured, rng)
    if sort in ("color", "rgbimage"):
        # 構造版 = chain_fuzz の**二色性レンダ**(既知の法線・アルベド・光源から
        # 描いた、分離の真値が分かる画像)。これは rng を使わず毎回同じ絵を返す
        # ——「真値が分かる種」なので正しいのだが、そのまま 2 本引くと
        # **入力が変わらない**ことになり、op が死んで見える。だから
        # 乱数版は一様乱数を別に作る。
        if structured:
            return _generators()["rgbimage"](rng)
        n = 3 if sort == "color" else 3
        return rng.random((24, 32, n))
    if structured and sort == "volume":
        return structured_volume()
    if structured and sort == "points":
        return structured_points()
    if structured and sort == "signal":
        return structured_signal()
    key = SORT_TO_GENERATOR.get(sort)
    return None if key is None else _generators()[key](rng)


def sample_pair(sort: str, rng=None):
    """``[乱数版, 構造版]``。構造版を作れない sort は**独立な乱数を 2 本**。

    op の挙動を測るときはこの 2 本を必ず両方通す —— 片方だけだと
    「その入力では差が出ないだけ」を「壊れている」と読み違える。
    """
    rng = np.random.default_rng(0) if rng is None else rng
    a = sample_input(sort, rng, structured=False)
    if a is None:
        return []
    b = sample_input(sort, rng, structured=True) if sort in STRUCTURED_SORTS else None
    if b is None:
        b = sample_input(sort, rng, structured=False)     # 構造版が無い sort
    return [a, b]


def sample_probes(sort: str, name: str = "", n: int = 4):
    """op を測るための入力を *n* 本。**op 名から種を作る**ので順序に依らず再現する。

    共有の乱数生成器を op の並び順に消費すると、op を 1 つ足しただけで
    以降すべての入力が変わり、**測定結果が実行ごとに揺れる**(実測: 効かない
    はずのノブ 4 件が「効く」に化けた)。名前で種を固定すればそれが起きない。
    """
    seed = zlib.crc32(name.encode("utf-8")) if name else 0
    rng = np.random.default_rng(seed)
    out = sample_pair(sort, rng)
    if not out:
        return []
    while len(out) < n:
        v = sample_input(sort, rng, structured=False)
        if v is None:
            break
        out.append(v)
    return out


def sorts_with_samples() -> list[str]:
    """代表値を作れる ``in_sort`` の一覧(``fullseye.list_ops`` の in_sort と突き合わせる)。"""
    return sorted(set(SORT_TO_GENERATOR) | set(LOCAL_SORTS))
