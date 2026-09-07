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


def structured_fragments(n: int = 48) -> np.ndarray:
    """細い線分の断片(長さ 3 / 6 / 12 / 25 / 40 px)+ 小さな塊 + 弱い背景勾配。

    ``structured_image`` は塊が大きく、しきい値で二値化すると連結成分が数百画素に
    なる。だから「短い断片を落とす」「近い端点を繋ぐ」「線の長さで選ぶ」種類の
    ノブは、あの画像だけでは何を振っても出力が変わらない(2026-09-07:
    ``hx_close_edges_length`` の ``b`` = 残す最小画素数 2〜22 が探針では
    「効かない」と誤判定された)。断片の長さが段階的に並ぶこの画像を 1 枚足す。
    """
    y, x = np.mgrid[0:n, 0:n]
    s = 0.08 * (x / float(n - 1))
    row = 4
    for L in (3, 6, 12, 25, 40):
        L = min(L, n - 4)
        s[row, 2:2 + L] = 1.0
        row += 5
    # 斜めの断片(4 近傍では 1 画素ずつに切れる)と、小さな塊
    for k in range(8):
        s[min(n - 1, row + k), min(n - 1, 2 + k)] = 1.0
    s[n - 8:n - 4, n - 10:n - 5] = 0.9
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


# --------------------------------------------------------------------------- #
# 2026-09-08 に足した 8 sort —— 門が 4 sort しか見ていなかった                    #
# --------------------------------------------------------------------------- #
# ``tests/test_op_probe_ledger.py`` は image / region / color / volume の 4 つに
# しか入力を作っておらず、残り 13 sort・**217 op(レジストリ 901 本の 24 %)**を
# "uncallable" として素通りさせていた。門が「正しい場所に立っている」だけでは
# 足りず、**入力を作れる範囲までしか見ていない**という穴だった。
#
# ここで足す 8 本は、どれも「その sort が本来運ぶ物理」を閉形式で仕込む。
# 乱数で埋めると、たとえば背景差分は全画素が前景になって**定数**を返し、
# それを「壊れている」と読み違える(実測でそうなりかけた)。
def structured_video(t: int = 8, n: int = 32) -> np.ndarray:
    """静止した地の上を**斜めに動く明るい円**。背景差分・動き履歴に意味が出る。

    乱数のフレームを積むと前景が全面になり、5 つの video op がそろって
    「定数を返す」に見える(2026-09-08 実測)。動く物と動かない地を分けて
    仕込むのが、この sort の探針の要件。
    """
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    ground = 0.35 + 0.15 * np.sin(xx / 3.0) * np.cos(yy / 4.0)
    out = np.empty((t, n, n))
    for k in range(t):
        cx, cy = 6.0 + 2.2 * k, 8.0 + 1.6 * k
        disk = np.exp(-(((xx - cx) ** 2 + (yy - cy) ** 2) / 18.0))
        out[k] = np.clip(ground + 0.55 * disk, 0.0, 1.0)
    return out


def structured_qimage(n: int = 32) -> np.ndarray:
    """**純四元数**の画像(実部 = 0、i/j/k に色)。``quaternion_to_rgb`` の契約。

    実部を 0 にしないと「純でない」と拒否される —— それは op が正しく
    fail-closed なのであって、拒否を欠陥と読んではいけない。
    """
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    r = 0.5 + 0.4 * np.sin(xx / 5.0)
    g = 0.5 + 0.4 * np.cos(yy / 6.0)
    b = 0.5 + 0.4 * np.sin((xx + yy) / 7.0)
    return np.stack([np.zeros_like(r), r, g, b], axis=-1)


def structured_cimage(n: int = 32) -> np.ndarray:
    """既知の**位相ランプ**(縞 3 本ぶん)× なだらかな振幅。位相 op に真値が出る。"""
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    phase = 2.0 * np.pi * (3.0 * xx / n + 1.0 * yy / n)
    amp = 0.4 + 0.3 * np.exp(-(((xx - n / 2) ** 2 + (yy - n / 2) ** 2) / (n * 4.0)))
    return amp * np.exp(1j * phase)


def structured_lightfield(v: int = 3, u: int = 3, n: int = 32) -> np.ndarray:
    """視差が**視点に線形**な平面(奥行き一定)。EPI の傾きが閉形式で分かる。"""
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    base = 0.4 + 0.35 * np.sin(xx / 3.5) * np.cos(yy / 5.0)
    out = np.empty((v, u, n, n))
    d = 1.5                                        # 視点 1 つあたりの視差 [px]
    for iv in range(v):
        for iu in range(u):
            sx, sy = d * (iu - u // 2), d * (iv - v // 2)
            out[iv, iu] = 0.4 + 0.35 * np.sin((xx - sx) / 3.5) * np.cos((yy - sy) / 5.0)
    del base
    return out


def structured_beatcube(a: int = 4, c: int = 16, s: int = 32) -> np.ndarray:
    """FMCW の**既知の 1 目標**(距離 bin 6・ドップラー bin 3・到来角 20 度)。

    ``(antennas, chirps, samples)`` の複素。距離は標本方向の周波数、速度は
    チャープ方向の位相、角度はアンテナ間の位相で表す —— 3 つとも閉形式なので
    ``range_doppler_map`` / ``beamform_delay_sum`` の答えを先に予測できる。
    """
    ia = np.arange(a)[:, None, None]
    ic = np.arange(c)[None, :, None]
    is_ = np.arange(s)[None, None, :]
    f_range, f_dopp = 6.0 / s, 3.0 / c
    phi_a = 2.0 * np.pi * 0.5 * np.sin(np.radians(20.0))
    sig = np.exp(2j * np.pi * (f_range * is_ + f_dopp * ic) + 1j * phi_a * ia)
    return sig.astype(np.complex128)


def structured_counts(n: int = 256) -> np.ndarray:
    """TCSPC の**指数減衰 + 背景**(寿命 40 bin、ピーク 900、床 12)。

    一様乱数だと寿命も飛行時間も出ない。``dtof_depth`` / ``tcspc_*`` は
    この形を前提にしている。
    """
    t = np.arange(n, dtype=np.float64)
    peak = 24.0
    decay = np.where(t >= peak, 900.0 * np.exp(-(t - peak) / 40.0), 0.0)
    return decay + 12.0


def structured_keypoints(m: int = 160) -> np.ndarray:
    """既知の**楕円**(中心 (24,18)、半径 14×9、傾き 25 度)の上の (u, v)。"""
    th = np.linspace(0.0, 2.0 * np.pi, m, endpoint=False)
    ca, sa = np.cos(np.radians(25.0)), np.sin(np.radians(25.0))
    x, y = 14.0 * np.cos(th), 9.0 * np.sin(th)
    return np.stack([24.0 + ca * x - sa * y, 18.0 + sa * x + ca * y], axis=1)


def structured_matrix(rows: int = 2, cols: int = 8) -> np.ndarray:
    """**相関のある** 2 行のデータ行列(相関係数 ≈ 0.94)。共分散 op に差が出る。"""
    t = np.linspace(0.0, 1.0, cols)
    a = np.sin(2.0 * np.pi * t)
    b = 0.9 * a + 0.1 * np.cos(6.0 * np.pi * t)
    out = np.stack([a, b], axis=0)
    if rows != 2:
        out = np.resize(out, (rows, cols))
    return out


#: 構造版を作れる sort(ここに無い sort は :func:`sample_pair` が独立な乱数を 2 本使う)
STRUCTURED_SORTS = ("image", "any", "region", "contour", "color", "rgbimage",
                    "volume", "points", "signal",
                    # 2026-09-08 追加(門を 4 sort → 全 sort に広げるため)
                    "video", "qimage", "cimage", "lightfield", "beatcube",
                    "counts", "keypoints", "matrix")


# --------------------------------------------------------------------------- #
# op 単位の探針上書き —— 「畳んだ型」の請求書                                     #
# --------------------------------------------------------------------------- #
# ``backends_typed.TYPE_TO_SORT`` は宣言型を進化側の sort に畳む
# (``indices`` → ``signal``、``normals`` → ``points`` …。理由と実測は
#  ``docs/TYPE_ALIAS_LEDGER.json``)。畳むと **sort だけでは正しい探針を作れない**
# op が出る: 添字を取る op に連続な信号を渡せば当然拒否されるが、それは op が
# 正しく fail-closed なのであって欠陥ではない。
#
# この表は、その「畳んだせいで sort 既定の探針では走れない op」を 1 行ずつ挙げる。
# **表が伸びることが、畳んだことの費用**なので、伸ばすときは理由を書くこと。
# ``tests/test_op_probe_ledger.py`` が (1) 既定の探針では本当に落ちること
# (2) 上書きなら通ること の両方を毎回測るので、要らなくなった行は残せない。
def _monogenic_probe(n: int = 32) -> np.ndarray:
    """``(帯域通過像, R1, R2, 0)`` の本物のモノジェニック信号(Felsberg & Sommer 2001)。"""
    import quatimage as Q                                  # noqa: PLC0415
    return Q.monogenic_signal(structured_image(n), wavelength_px=9.0,
                              bandwidth_octaves=1.125)


def _pure_quaternion_probe(n: int = 32) -> np.ndarray:
    """実部 0 の**純**四元数(色の四元数)。``quaternion_to_rgb`` の契約。"""
    return structured_qimage(n)


def _unit_normals_probe(m: int = 160) -> np.ndarray:
    """単位法線(球面上の一様に近い向き)。位置の点群ではない。"""
    i = np.arange(m, dtype=np.float64) + 0.5
    phi = np.arccos(1.0 - 2.0 * i / m)
    th = np.pi * (1.0 + 5.0 ** 0.5) * i
    return np.stack([np.sin(phi) * np.cos(th), np.sin(phi) * np.sin(th),
                     np.cos(phi)], axis=1)


def _indices_probe(n: int = 24) -> np.ndarray:
    """非負整数の添字(``indices``)。``signal`` の連続値では拒否される。"""
    return np.arange(0, 4 * n, 4, dtype=np.float64)


def _dichromatic_probe():
    """二色性レンダ(単一材質 + ハイライト)。``specular_*` の契約。"""
    return _generators()["rgbimage"](np.random.default_rng(20260908))


#: ``op 名 -> (探針を作る関数, なぜ sort 既定では駄目か)``
OP_PROBE_OVERRIDE = {
    "tb_monogenic_amplitude": (_monogenic_probe,
        "qimage は色の四元数とモノジェニック信号の 2 つを兼ねている。"
        "前者は実部 0・k に青、後者は実部が帯域通過像で k が 0 —— 両立しない"),
    "tb_monogenic_phase": (_monogenic_probe, "同上(qimage が 2 つの契約を兼ねている)"),
    "tb_monogenic_orientation": (_monogenic_probe, "同上(qimage が 2 つの契約を兼ねている)"),
    "tb_quaternion_to_rgb": (_pure_quaternion_probe,
        "純四元数(実部 0)だけを受ける。乱数の qimage は実部が残るので拒否される"),
    "tb_normals_to_egi": (_unit_normals_probe,
        "normals は points に畳まれている。位置の雲を渡すと原点が零ベクトルになり拒否される"),
    "tb_indices_to_labels": (_indices_probe,
        "indices は signal に畳まれている。連続値は整数でないので正しく拒否される"),
    "tb_specular_diffuse_split": (_dichromatic_probe,
        "単一材質の面(照明直交成分の階数 1)を要求する。乱数の色画像は階数が立つ"),
    "tb_specular_coefficient_map": (_dichromatic_probe, "同上(単一材質を要求する)"),
}


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
    if structured:
        # 2026-09-08 追加分。形は chain_fuzz の生成器と同じにしてある
        # (揃えないと「探針を足したら形が変わって落ちた」が起きる)。
        extra = {
            "video": structured_video, "qimage": structured_qimage,
            "cimage": structured_cimage, "lightfield": structured_lightfield,
            "beatcube": structured_beatcube, "counts": structured_counts,
            "keypoints": structured_keypoints, "matrix": structured_matrix,
        }
        if sort in extra:
            return extra[sort]()
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
