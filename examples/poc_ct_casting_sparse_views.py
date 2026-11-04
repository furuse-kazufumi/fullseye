# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: 鋳物の空隙をコーンビーム CT で測る —— 投影を減らす・角度を欠くと、FDK / SIRT / OS-SART / TV の順位が入れ替わる

    py -3.11 examples/poc_ct_casting_sparse_views.py

アルミ鋳物の内部の空隙(ガス気孔・引け巣)は、工業用 CT で体積と位置を測って合否を決めます。
撮影時間を縮めたいときは投影の数を減らし(少数投影)、大きな部品や治具で回しきれないときは
角度の一部しか撮れません(限られた角度)。そのとき「どの再構成を使えば空隙を正しく測れるか」は
条件で変わるはずで、この PoC はそれを**真値と比べて**数えます。使うのは Fullseye の ``ct_scan`` 族
11 本を鎖にしたものだけです。

1. **真値の検算**(再構成の前に、道具そのものを確かめる):
   ``ellipsoid_phantom`` で描いた鋳物の空隙の体積を閉形式 4/3·π·a·b·c と比べ、
   ``ellipsoid_projections``(楕円体の弦の長さの閉形式)と ``ct_forward_project``(ボクセルを
   1 ボクセル刻みで三線形に積む離散の投影)が一致し、格子を細かくすると差が縮むことを見る。
   ``shepp_logan_3d`` でも同じ比較をする(細い構造のある相手)。``ct_forward_project`` と
   ``ct_adjoint_project`` の随伴性 <Ax, y> = <x, Aᵀy> を乱数の x・y で測り、わざと幾何をずらした
   Aᵀ では門が落ちることも確かめる(門に歯があるか)。
2. **3 条件 × 4 手法**: 360° に 36 投影(十分)/ 360° に 12 投影(少数投影)/ 110° に 30 投影
   (限られた角度、短走査の最低 180° + 扇角に届かない)。データは**閉形式の投影 + 雑音**で作るので、
   再構成と同じ離散の投影でデータを作る「逆問題の罪(inverse crime)」を避けている。手法ごとに
   体積全体の RMSE、空隙 3 個の体積誤差(閉形式と比べる)、重心の誤差、見落とし・偽の空隙を数え、
   条件ごとの順位を出す。空隙は再構成を Al の半値で 2 値化し、``vol_rle_components`` で成分に分け、
   ``vol_rle_volume`` / ``vol_rle_centroid`` で測る。体積はもう 1 通り、成分のまわりの球で母材からの
   欠損 Σ(1 − x) を積んで測る(部分体積を捨てない)。
3. **TV の勝ちの内訳**: TV の正則化の強さ(``tv_weight``)は**評価に使わない較正用の鋳物**
   (空隙の位置・大きさ・向きが違う、雑音の乱数も別)で格子から選び、評価用の鋳物ではその 1 つの
   値だけを使う。評価用で格子を全部回した「後知恵の最良」とも並べ、選んだ値との差を開示する。
4. **デュアルエナジー**: 鋳物に鉄の入れ子(ブッシュ)を鋳込み、低・高エネルギーの 2 回の撮影を
   ``ct_dual_energy_reconstruct`` で Al と Fe の 2 つの基底に分ける。入れ子の体積を閉形式と比べ、
   分けたことで雑音が何倍になるかを、基底変換の逆行列の行のノルム(閉形式)と比べる。

この PoC が示すこと(32³、数字は実行時に印字される実測値):

* ★**RMSE の順位は条件で入れ替わる。** 360° に 36 投影では OS-SART ≈ SIRT(0.0309)< TV(0.0321)
  < FDK(0.0529)で、TV は代数的な 2 手法の良いほうに対し 1.037 倍(勝たない)。12 投影と 110° では
  TV が 1 位に上がり、比は 0.771 / 0.783。FDK は 3 条件とも最下位で、110° では 0.2135。
* ★★**RMSE の順位は空隙の体積の順位ではない。** 12 投影で RMSE が最下位の FDK は、欠損で測る空隙の
  体積が閉形式と平均 0.9 % で、1 位の TV(5.9 %)より正しい。線形の再構成は欠損の積分(質量)を
  保存し、TV は縁を平らに塗って積分を動かす。
* ★**限られた角度の FDK は空隙を 1 個も拾わない**(見落とし 3・偽の空隙 2)。反復の 3 手法は 3 個とも拾う。
* ★**2 値の体積は真値そのものでも 16.7 % 偏る**(半値で切る部分体積)。110° の SIRT の 2 値の誤差
  4.3 % のように真値より良く見える数字は、ぼけと 2 値化の偏りの打ち消し合いで、正しさではない
  (欠損で測ると 15.4 %)。PoC はこの形の数字すべてに注を印字する。
* ★**TV の勝ちの内訳**: 重みは較正用の鋳物で 3e-4 / 3e-3 / 3e-2 から選び、3 条件とも 3e-3(格子の内側)。
  評価用で後知恵に格子を回しても最良は同じ 3e-3 で、選んだ値との差は 0。
* **デュアルエナジー**: 鉄の入れ子の体積は −8.7 %、交差は Al 0.038・Fe 0.0133。分けた代わりに Al の
  基底の雑音は 1 回の撮影の 41.65 倍(閉形式 ||inv(M)|| の行 41.00 倍、条件数 39.3)。

★正直に書いておくこと:
  * 楕円体だけの合成の鋳物で、空隙の形は凸。実物の引け巣の枝分かれ・表面のざらつきは無い。
  * 単色の X 線(ビームハードニング・散乱・検出器のぼけ無し)。雑音は線積分に足したガウス雑音
    (最大の線積分の 0.5 %)で、光子計数の Poisson ではない。
  * デュアルエナジーの減衰係数は Al・Fe の 60 / 150 keV のおおよその桁に合わせた**例示の値**で、
    XCOM の表から引いたものではない。
  * 反復法の回数(SIRT 40、OS-SART 6 周、TV 40)は先に決めて固定した。少数投影の SIRT は
    回数そのものが正則化として効く(半収束)ので、評価用の鋳物で回数ごとの RMSE も印字して開示する。
  * 大きさは CPU で数分に収まるよう 32³。空隙は 24〜84 ボクセルなので、2 値の体積には部分体積の分が
    大きく入る。``FULLSEYE_POC_BUDGET=reduced``(CI の既定)は格子を縮めず、TV の重みの較正と後知恵の
    格子を省いて full が選んだ値を使う(24³ に縮めると結論が変わったため)。
  * 反復法の比較は回数を固定した比較。TV は Chambolle-Pock を 40 回しか回しておらず、弱い重みでは
    最小二乗に届く前で止まっている(弱い重みの TV が SIRT より悪いのはそのため)。
"""
from __future__ import annotations

import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import examplefig as figs  # noqa: E402
import fullseye as fs  # noqa: E402

LG = fs.ledger
CHECKS = []
DEV = "cpu"                                      # GPU は使わない(CI と同じ経路で測る)

REDUCED = os.environ.get("FULLSEYE_POC_BUDGET",
                         "reduced" if os.environ.get("CI") else "full") == "reduced"
#: 再構成の格子(立方体の 1 辺のボクセル数)。★reduced でも格子は縮めない: 24³ にすると最小の空隙が
#: 7 ボクセルになり、順位の結論そのものが変わる(2026-11-04 実測: 門 32 本中 8 本が別の答え)。
#: reduced は TV の重みの較正と後知恵の格子を省き、full が較正で選んだ値 TV_FULL_CHOICE を使う
#: (省いた段の門は判定しない。閾値は変えない)。
N = 32
TV_FULL_CHOICE = 3e-3
VOX = 0.25                                       # ボクセルの 1 辺 [mm]
NOISE = 0.005                                    # 線積分の雑音(最大の線積分に対する比)
SIRT_IT, OSSART_IT, TV_IT = 40, 6, 40
TV_GRID = (3e-4, 3e-3, 3e-2)
METHODS = ("fdk", "sirt", "os_sart", "tv")
CONDITIONS = (("full", "360° に 36 投影"), ("few", "360° に 12 投影(少数投影)"),
              ("limited", "110° に 30 投影(限られた角度)"))

#: 行 = (x0, y0, z0, a, b, c, phi_deg, rho)、正規化座標 [-1, 1]³(半幅 = N/2 ボクセル)。
#: 鋳物の母材(Al の減衰を 1 に正規化)と、rho = -1 で母材を打ち消す空隙。
CAST = (0.0, 0.0, 0.0, 0.82, 0.64, 0.56, 20.0, 1.0)
VOIDS_TEST = ((0.38, 0.05, 0.05, 0.20, 0.14, 0.16, 30.0, -1.0),
              (-0.36, -0.12, -0.08, 0.17, 0.17, 0.17, 0.0, -1.0),
              (-0.02, 0.30, 0.18, 0.13, 0.10, 0.11, -40.0, -1.0))
#: 較正用(TV の重みを選ぶだけに使う)。位置・大きさ・向きを変えてある。
VOIDS_CAL = ((-0.30, 0.20, -0.08, 0.19, 0.14, 0.15, -25.0, -1.0),
             (0.34, -0.16, 0.10, 0.16, 0.16, 0.16, 0.0, -1.0),
             (0.05, -0.05, -0.24, 0.13, 0.11, 0.10, 60.0, -1.0))
#: デュアルエナジーの鉄の入れ子(ブッシュ)と、その脇の空隙 2 個。
INSERT = (-0.30, 0.0, 0.0, 0.20, 0.20, 0.30, 0.0, 1.0)
VOIDS_DE = ((0.36, 0.12, 0.05, 0.18, 0.13, 0.15, 30.0, -1.0),
            (0.20, -0.28, -0.12, 0.14, 0.14, 0.14, 0.0, -1.0))
#: 実効減衰係数 [1/mm](Al, Fe)。例示の値(60 / 150 keV のおおよその桁)。
MU_LOW, MU_HIGH = (0.075, 0.94), (0.037, 0.154)


def check(ok, label, detail=""):
    CHECKS.append((bool(ok), label, detail))
    print("  [%s] %s %s" % ("OK" if ok else "NG", label, detail))


# --------------------------------------------------------------------------- 場面と幾何
def half_mm(n=N):
    """正規化座標の 1 が何 mm か(``ellipsoid_phantom`` / ``ellipsoid_projections`` の約束)。"""
    return n * VOX / 2.0


def void_volume_mm3(row, n=N):
    """楕円体の体積の閉形式 4/3·π·a·b·c [mm³]。"""
    h = half_mm(n)
    return 4.0 / 3.0 * math.pi * row[3] * row[4] * row[5] * h ** 3


def void_center_vox(row, n=N):
    """楕円体の中心をボクセルの添字 ``(z, y, x)`` で。"""
    c = (n - 1) / 2.0
    return np.array([row[2] * n / 2.0 + c, row[1] * n / 2.0 + c, row[0] * n / 2.0 + c])


def geometry(cond, n=N):
    """条件ごとのコーンビームの走査。検出器は拡大後に 1 ボクセル = 1 画素、幅 1.3 倍。"""
    nd = int(round(1.3 * n))
    kw = dict(n_u=nd, n_v=nd, vol_shape=n, voxel=VOX)
    if cond == "full":
        return LG.ct_scan_geometry("cone", n_views=36, **kw)
    if cond == "few":
        return LG.ct_scan_geometry("cone", n_views=12, **kw)
    if cond == "limited":
        return LG.ct_scan_geometry("cone", n_views=30, arc_deg=110.0, **kw)
    raise ValueError(cond)


def noisy(p, seed):
    rng = np.random.default_rng(seed)
    return p + NOISE * float(p.max()) * rng.standard_normal(p.shape)


def run_method(method, p, g, tv_weight=None, on_iter=None):
    if method == "fdk":
        # 限られた角度は式の前提(180° + 扇角)を満たさないので allow_incomplete で明示的に通す
        return LG.fdk_reconstruct(p, g, filter_name="hann", device=DEV, allow_incomplete=True)
    if method == "sirt":
        return LG.sirt_reconstruct(p, g, n_iter=SIRT_IT, device=DEV, on_iter=on_iter)
    if method == "os_sart":
        return LG.os_sart_reconstruct(p, g, n_iter=OSSART_IT, n_subsets=min(8, g["n_views"] // 3),
                                      device=DEV)
    if method == "tv":
        return LG.tv_reconstruct(p, g, tv_weight=tv_weight, n_iter=TV_IT, device=DEV)
    raise ValueError(method)


def rms_error(a, b):
    return float(np.sqrt(np.mean((np.asarray(a) - np.asarray(b)) ** 2)))


def interior_mask(n=N, shrink=0.9):
    """母材の内側(表面の部分体積を外す)。母材の楕円体を shrink 倍に縮めた中。"""
    x0, y0, z0, a, b, c, phi, _ = CAST
    idx = (np.arange(n) - (n - 1) / 2.0) / (n / 2.0)
    zz, yy, xx = np.meshgrid(idx, idx, idx, indexing="ij")
    ph = math.radians(phi)
    p = (xx - x0) * math.cos(ph) + (yy - y0) * math.sin(ph)
    q = -(xx - x0) * math.sin(ph) + (yy - y0) * math.cos(ph)
    return (p / a) ** 2 + (q / b) ** 2 + ((zz - z0) / c) ** 2 <= shrink ** 2


def measure_voids(vol, voids, level=0.5, n=N, interior=None):
    """空隙を測る: 母材の内側で level 未満を 2 値化 → 成分 → 体積・重心。

    真の空隙ごとに、その中心にいちばん近い重心の成分(2 ボクセル以内)を対応させる。
    体積は 2 通り: 2 値化した成分のボクセル数(現場の既定)と、成分の重心のまわりの球(等価半径 + 2
    ボクセル、母材の内側)で母材からの欠損 Σ(1 − x) を積んだもの(部分体積の欠損。ぼけても線形に保存される)。
    返り値: 空隙ごとの ``(2 値の体積 mm³, 重心誤差 mm, 欠損の体積 mm³)``(見落としは nan)と、
    対応しなかった成分の数(偽の空隙)。
    """
    inside = interior_mask(n) if interior is None else interior
    vol = np.asarray(vol, dtype=np.float64)
    binary = (vol < level) & inside
    comps = LG.vol_rle_components(binary.astype(np.float64)) if binary.any() else []
    found = []
    for r in comps:
        nvox = LG.vol_rle_volume(r)
        if nvox < 2:                              # 1 ボクセルの点は雑音として数えない
            continue
        found.append((np.array(LG.vol_rle_centroid(r)), nvox))
    used = set()
    out = []
    grid = np.indices(vol.shape).astype(np.float64)
    for row in voids:
        c = void_center_vox(row, n)
        best, dist = None, 2.0 + max(row[3:6]) * n / 2.0
        for k, (cen, _nv) in enumerate(found):
            d = float(np.linalg.norm(cen - c))
            if k not in used and d < dist:
                best, dist = k, d
        if best is None:
            out.append((float("nan"), float("nan"), float("nan")))
            continue
        used.add(best)
        cen, nvox = found[best]
        radius = (3.0 * nvox / (4.0 * math.pi)) ** (1.0 / 3.0) + 2.0
        roi = (np.sum((grid - cen[:, None, None, None]) ** 2, axis=0) <= radius ** 2) & inside
        deficit = float(np.sum(1.0 - vol[roi])) * VOX ** 3
        out.append((nvox * VOX ** 3, dist * VOX, deficit))
    return out, len(found) - len(used)


def summarize(vol, truth, voids, n=N):
    res, false_pos = measure_voids(vol, voids, n=n)
    vtrue = np.array([void_volume_mm3(r, n) for r in voids])
    vols = np.array([v for v, _, _ in res])
    cens = np.array([c for _, c, _ in res])
    defs = np.array([d for _, _, d in res])
    missed = int(np.sum(~np.isfinite(vols)))
    rel = np.where(np.isfinite(vols), np.abs(vols - vtrue) / vtrue, 1.0)   # 見落としは誤差 100 %
    rel_d = np.where(np.isfinite(defs), np.abs(defs - vtrue) / vtrue, 1.0)
    return {"rms_err": rms_error(vol, truth), "vol_err": float(rel.mean()), "vol_rel": rel,
            "def_err": float(rel_d.mean()), "def_rel": rel_d,
            "cen_err": float(np.nanmax(cens)) if missed < len(voids) else float("nan"),
            "missed": missed, "false": int(false_pos)}


# --------------------------------------------------------------------------- 1) 真値の検算
def adjoint_gap(g, seed=0, g_t=None):
    """|<Ax, y> - <x, Aᵀy>| / |<Ax, y>|。g_t を渡すと Aᵀ を別の幾何で取る(歯の確認用)。"""
    rng = np.random.default_rng(seed)
    x = rng.standard_normal(tuple(g["vol_shape"]))
    y = rng.standard_normal((g["n_views"], g["n_v"], g["n_u"]))
    ax = LG.ct_forward_project(x, g, device=DEV)
    aty = LG.ct_adjoint_project(y, g if g_t is None else g_t, device=DEV)
    lhs, rhs = float(np.sum(ax * y)), float(np.sum(x * aty))
    return abs(lhs - rhs) / abs(lhs), lhs, rhs


def projector_gap(table, n, views=8):
    """離散の投影(``ellipsoid_phantom`` → ``ct_forward_project``)と閉形式の投影の相対 L2 差。"""
    nd = int(round(1.3 * n))
    g = LG.ct_scan_geometry("cone", n_views=views, n_u=nd, n_v=nd, vol_shape=n, voxel=VOX)
    exact = LG.ellipsoid_projections(g, table, device=DEV)
    if table is None:
        vol = LG.shepp_logan_3d(n, supersample=2)
    else:
        vol = LG.ellipsoid_phantom(n, table, supersample=2)
    disc = LG.ct_forward_project(vol, g, device=DEV)
    return float(np.linalg.norm(disc - exact) / np.linalg.norm(exact)), exact, disc


def chapter_truth():
    print("=" * 78)
    print("1) 真値の検算: 描いた空隙の体積・投影の閉形式と離散・随伴性")
    print("=" * 78)
    table = (CAST,) + VOIDS_TEST
    # 空隙の体積: 母材だけの描画との差(部分体積を含む)を閉形式と比べる
    solid = LG.ellipsoid_phantom(N, (CAST,), supersample=4)
    for k, row in enumerate(VOIDS_TEST):
        one = LG.ellipsoid_phantom(N, (CAST, row), supersample=4)
        v = float(np.sum(solid - one)) * VOX ** 3
        vt = void_volume_mm3(row)
        print("  空隙 %d: 描画 %.4f mm³、閉形式 4/3πabc %.4f mm³(差 %+.2f %%)" % (k + 1, v, vt, 100 * (v / vt - 1)))
        check(abs(v / vt - 1) < 0.02, "空隙 %d の描画の体積が閉形式と 2 %% 以内(supersample 4)" % (k + 1))
    # 中心を通る線の弦: 母材だけ・投影 1 本の中央画素は 2·(楕円体の中心を通る弦) に等しいはず
    g1 = LG.ct_scan_geometry("parallel", n_views=1, n_u=N + 1, n_v=N + 1, vol_shape=N, voxel=VOX,
                             angles_deg=[0.0])
    sphere = (0.0, 0.0, 0.0, 0.5, 0.5, 0.5, 0.0, 1.0)
    p1 = LG.ellipsoid_projections(g1, (sphere,), device=DEV)
    chord = float(p1[0, N // 2, N // 2])
    want = 2.0 * 0.5 * half_mm()
    print("  球(半径 %.2f mm)の中心を通る弦: %.6f mm、閉形式 2r = %.6f mm" % (0.5 * half_mm(), chord, want))
    check(abs(chord - want) < 1e-9 * want, "閉形式の投影の中心の弦が 2r に一致(1e-9)")

    # 平行ビームなら各投影の総和 × 画素の面積は角度によらず質量 Σ rho·4/3πabc(再構成を見ない検算)
    gp = LG.ct_scan_geometry("parallel", n_views=6, n_u=2 * N, n_v=2 * N, vol_shape=N, voxel=VOX)
    pp = LG.ellipsoid_projections(gp, table, device=DEV)
    mass = sum(r[7] * void_volume_mm3(r) for r in table)
    per_view = pp.sum(axis=(1, 2)) * gp["du"] * gp["dv"]
    dev_mass = float(np.max(np.abs(per_view / mass - 1)))
    print("  平行ビームの投影の総和 = 質量: 閉形式 %.4f mm³、6 方向の最大のずれ %.2e" % (mass, dev_mass))
    check(dev_mass < 0.01, "閉形式の投影の総和が全方向で質量の閉形式と 1 % 以内(画素の中心の点の標本なので縁の分だけずれる)", "(%.2e)" % dev_mass)

    gaps = {}
    for name, tab in (("鋳物", table), ("Shepp-Logan", None)):
        for n in (N, 2 * N):
            gaps[(name, n)] = projector_gap(tab, n)[0]
            print("  %-12s %3d³: 離散の投影と閉形式の相対 L2 差 %.4f" % (name, n, gaps[(name, n)]))
        # Shepp-Logan は頭蓋の殻が 32³ で 1〜2 ボクセルしかなく、縁の離散化が L2 を 13 % まで押し上げる
        # (64³ で 9 %)。鋳物の 5 % と同じ床は当てられないので 20 % にし、収束の門を主にする。
        lim = 0.05 if tab is not None else 0.20
        check(gaps[(name, N)] < lim, "%s: 離散の投影が閉形式と相対 L2 で %d %% 以内(%d³)" % (name, round(100 * lim), N))
        check(gaps[(name, 2 * N)] < 0.75 * gaps[(name, N)],
              "%s: 格子を 2 倍に細かくすると差が縮む(0.75 倍未満)" % name,
              "(%.4f → %.4f)" % (gaps[(name, N)], gaps[(name, 2 * N)]))
    check(np.allclose(LG.shepp_logan_3d(N, supersample=2), LG.ellipsoid_phantom(N, None, supersample=2)),
          "shepp_logan_3d は ellipsoid_phantom(既定の表)と同じ体積")

    # 随伴性。float64 で数十万項の和なので丸めの相対誤差は 1e-13 の桁(eps·√項数)。
    # 1e-6 は丸めより 7 桁大きく、補間の重みを 1 か所でも取り違えた対の 1e-3 の桁よりは 3 桁小さい。
    g = geometry("full")
    gap, lhs, rhs = adjoint_gap(g)
    print("  随伴性: <Ax,y> = %.10e、<x,Aᵀy> = %.10e、相対差 %.2e" % (lhs, rhs, gap))
    check(gap < 1e-6, "ct_forward_project と ct_adjoint_project が随伴(相対 1e-6 未満)", "(%.2e)" % gap)
    g_off = LG.ct_scan_geometry("cone", n_views=g["n_views"], n_u=g["n_u"], n_v=g["n_v"],
                                vol_shape=N, voxel=VOX, offset_u=0.5)
    bad, _, _ = adjoint_gap(g, g_t=g_off)
    print("  歯の確認: 検出器を 0.5 画素ずらした Aᵀ では相対差 %.2e" % bad)
    check(bad > 1e-3, "幾何をずらした Aᵀ は門を落ちる(門に歯がある)", "(%.2e)" % bad)
    return gaps, gap


# --------------------------------------------------------------------------- 2) 3 条件 × 4 手法
def choose_tv_weight(g, cal_data, cal_truth):
    """較正用の鋳物で TV の重みを格子から選ぶ(評価用の鋳物は見ない)。"""
    scores = {w: rms_error(run_method("tv", cal_data, g, tv_weight=w), cal_truth) for w in TV_GRID}
    return min(scores, key=scores.get), scores


def chapter_methods():
    print()
    print("=" * 78)
    print("2) 3 条件 × 4 手法: 体積の RMSE・空隙の体積誤差・重心の誤差(真値と比べる)")
    print("=" * 78)
    table_t = (CAST,) + VOIDS_TEST
    table_c = (CAST,) + VOIDS_CAL
    truth = LG.ellipsoid_phantom(N, table_t, supersample=2)
    truth_c = LG.ellipsoid_phantom(N, table_c, supersample=2)
    vt = [void_volume_mm3(r) for r in VOIDS_TEST]
    for name, tr, vs in (("評価用", truth, VOIDS_TEST), ("較正用", truth_c, VOIDS_CAL)):
        s0 = summarize(tr, tr, vs)
        check(float(tr.min()) >= -1e-12 and s0["missed"] == 0 and s0["false"] == 0,
              "%s の真値: 空隙どうしが重ならず(最小 %.3f ≥ 0)、2 値化で 1 個ずつの成分になる" % (name, tr.min()),
              "(2 値の体積誤差 %.1f %%、欠損 %.1f %%)" % (100 * s0["vol_err"], 100 * s0["def_err"]))
    print("  空隙の真の体積(閉形式): %s mm³(%s ボクセル)"
          % (" / ".join("%.3f" % v for v in vt), " / ".join("%.1f" % (v / VOX ** 3) for v in vt)))
    results, tv_info, recons, sirt_curves = {}, {}, {}, {}
    for cond, label in CONDITIONS:
        g = geometry(cond)
        p = noisy(LG.ellipsoid_projections(g, table_t, device=DEV), 1)
        if REDUCED:
            w, cal_scores = TV_FULL_CHOICE, {}
            grid = (w,)
        else:
            p_c = noisy(LG.ellipsoid_projections(g, table_c, device=DEV), 2)
            w, cal_scores = choose_tv_weight(g, p_c, truth_c)
            # 後知恵の格子は TV が勝つと言う条件(少数投影・限られた角度)だけ回す(時間の都合)
            grid = TV_GRID if cond != "full" else (w,)
        tv_recon = {ww: run_method("tv", p, g, tv_weight=ww) for ww in grid}
        oracle = {ww: rms_error(x, truth) for ww, x in tv_recon.items()}
        tv_info[cond] = (w, cal_scores, oracle)
        curve = []
        print()
        print("  %s(%s、視野の角度 %.0f°)" % (label, cond, g["arc_deg"]))
        for m in METHODS:
            t = time.time()
            cb = (lambda k, x, _c=curve: _c.append(rms_error(x, truth))) if m == "sirt" else None
            x = tv_recon[w] if m == "tv" else run_method(m, p, g, tv_weight=w, on_iter=cb)
            assert np.all(np.isfinite(x)) and float(np.ptp(x)) > 0.1, (cond, m)
            s = summarize(x, truth, VOIDS_TEST)
            results[(cond, m)] = s
            recons[(cond, m)] = x
            print("    %-7s RMSE %.4f  空隙の体積誤差 2 値 %5.1f %%(%s)・欠損 %5.1f %%(%s)  重心誤差 最大 %.3f mm  "
                  "見落とし %d  偽 %d  (%.1f 秒)"
                  % (m, s["rms_err"], 100 * s["vol_err"], " / ".join("%.0f" % (100 * e) for e in s["vol_rel"]),
                     100 * s["def_err"], " / ".join("%.0f" % (100 * e) for e in s["def_rel"]),
                     s["cen_err"], s["missed"], s["false"], time.time() - t))
        sirt_curves[cond] = curve
        order = sorted(METHODS, key=lambda mm: results[(cond, mm)]["rms_err"])
        print("    順位(RMSE): %s" % " < ".join(order))
        if cal_scores:
            print("    TV の重み: 較正用で選んだ %.0e(較正用の RMSE %s)"
                  % (w, ", ".join("%.0e:%.4f" % kv for kv in sorted(cal_scores.items()))))
        else:
            print("    TV の重み: reduced なので較正を回さず、full が較正で選んだ %.0e を使う" % w)
        if len(oracle) > 1:
            print("               評価用で後知恵に回すと %s"
                  % ", ".join("%.0e:%.4f" % kv for kv in sorted(oracle.items())))
        k_best = int(np.argmin(curve))
        print("    SIRT の回数ごとの RMSE(評価用): 最良 %d 回目 %.4f、使った %d 回目 %.4f"
              % (k_best + 1, curve[k_best], SIRT_IT, curve[-1]))
    return results, tv_info, recons, truth, sirt_curves


def rank(results, cond, key="rms_err"):
    return sorted(METHODS, key=lambda m: results[(cond, m)][key])


def gate_methods(results, tv_info, sirt_curves, truth):
    print()
    print("  門:")
    full = {m: results[("full", m)] for m in METHODS}
    check(all(s["missed"] == 0 and s["false"] == 0 for s in full.values()),
          "十分な投影では 4 手法とも空隙 3 個を全部見つけ、偽の空隙を出さない")
    check(full["fdk"]["def_err"] < 0.05 and full["fdk"]["cen_err"] < VOX,
          "十分な投影の FDK: 欠損で測った空隙の体積が閉形式と平均 5 % 以内・重心誤差 1 ボクセル未満",
          "(%.1f %%, %.3f mm)" % (100 * full["fdk"]["def_err"], full["fdk"]["cen_err"]))
    for cond in ("few", "limited"):
        check(results[(cond, "fdk")]["rms_err"] > 1.3 * results[("full", "fdk")]["rms_err"],
              "%s: FDK の RMSE が十分な投影の 1.3 倍を超えて悪化する" % cond,
              "(%.4f vs %.4f)" % (results[(cond, "fdk")]["rms_err"], results[("full", "fdk")]["rms_err"]))
    # ★順位の入れ替わり: TV の RMSE を、SIRT と OS-SART の良いほうで割る。投影が足りている条件では
    #   勝たず(TV の仮定が要らない)、足りない条件でだけ勝つ —— が、重みを評価用で選んでいない状態で言えるか。
    ratio = {}
    for cond, _ in CONDITIONS:
        alg = min(results[(cond, "sirt")]["rms_err"], results[(cond, "os_sart")]["rms_err"])
        ratio[cond] = results[(cond, "tv")]["rms_err"] / alg
        print("    %-8s RMSE の順位 %s、TV / (SIRT・OS-SART の良いほう) = %.3f"
              % (cond, " < ".join(rank(results, cond)), ratio[cond]))
    check(ratio["full"] > 0.95, "十分な投影では TV は SIRT・OS-SART に勝たない(比 > 0.95)",
          "(%.3f)" % ratio["full"])
    check(ratio["few"] < 0.9 and ratio["limited"] < 0.9,
          "少数投影・限られた角度では TV が RMSE の 1 位に上がる(比 < 0.9)",
          "(%.3f / %.3f)" % (ratio["few"], ratio["limited"]))
    # ★RMSE の順位は空隙の体積の順位ではない: 少数投影の FDK は RMSE が最下位でも、欠損で測る体積は
    #   線形の再構成なので質量が保存され、TV より正しい(TV は縁を平らに塗るので欠損の積分を動かす)。
    few = {m: results[("few", m)] for m in METHODS}
    check(rank(results, "few")[-1] == "fdk" and few["fdk"]["def_err"] < few["tv"]["def_err"],
          "少数投影: RMSE が最下位の FDK のほうが、1 位の TV より欠損で測る空隙の体積が正しい",
          "(%.1f %% vs %.1f %%)" % (100 * few["fdk"]["def_err"], 100 * few["tv"]["def_err"]))
    lim = {m: results[("limited", m)] for m in METHODS}
    check(lim["fdk"]["missed"] == len(VOIDS_TEST)
          and all(lim[m]["missed"] == 0 for m in ("sirt", "os_sart", "tv")),
          "限られた角度: FDK は空隙を 1 個も拾えず、反復の 3 手法は 3 個とも拾う",
          "(FDK の偽の空隙 %d)" % lim["fdk"]["false"])
    # ★「異常に良い」の内訳: 2 値の体積は真値そのものでも部分体積で偏る。手法がそれより小さな誤差を
    #   出したら、ぼけの偏りと 2 値化の偏りが打ち消し合っただけ(正しさではない)と印字する。
    own = summarize(truth, truth, VOIDS_TEST)
    check(own["def_err"] < 0.03, "測り方の検算: 真値そのものを欠損で測ると閉形式と 3 % 以内",
          "(2 値では %.1f %% 偏る)" % (100 * own["vol_err"]))
    for (cond, m), s in sorted(results.items()):
        if s["missed"] == 0 and s["vol_err"] < own["vol_err"]:
            print("    注: %s / %s の 2 値の体積誤差 %.1f %% は真値そのもの(%.1f %%)より小さい —— "
                  "偏りの打ち消し合いで、正しさの証拠ではない" % (cond, m, 100 * s["vol_err"], 100 * own["vol_err"]))
    # TV の内訳: 重みは較正用の鋳物だけで選んだ。格子の端で選ばれていないこと、後知恵の最良との差。
    for cond, _ in CONDITIONS:
        w, cal, oracle = tv_info[cond]
        if not cal:
            continue
        check(min(cal) < w < max(cal), "%s: 較正用で選んだ TV の重みが格子の内側(端なら格子が足りない)" % cond,
              "(%.0e)" % w)
        check(w == TV_FULL_CHOICE, "%s: 較正で選んだ重みが reduced の使う TV_FULL_CHOICE と同じ(古くなっていない)" % cond,
              "(%.0e vs %.0e)" % (w, TV_FULL_CHOICE))
        if len(oracle) > 1:
            best = min(oracle.values())
            check(oracle[w] <= 1.15 * best,
                  "%s: 較正用で選んだ重みの RMSE は、評価用の後知恵の最良と 15 %% 以内" % cond,
                  "(%.4f vs %.4f、%.0e vs %.0e)" % (oracle[w], best, w, min(oracle, key=oracle.get)))
    for cond, curve in sirt_curves.items():
        k = int(np.argmin(curve))
        print("    %-8s SIRT の RMSE は %d 回目が最良(使った %d 回目との差 %.1f %%)"
              % (cond, k + 1, SIRT_IT, 100 * (curve[-1] / curve[k] - 1)))


# --------------------------------------------------------------------------- 4) デュアルエナジー
def chapter_dual_energy():
    print()
    print("=" * 78)
    print("4) デュアルエナジー: 鉄の入れ子を Al と Fe の基底に分ける(360° に 36 投影、FDK)")
    print("=" * 78)
    t_al = (CAST, (INSERT[:7] + (-1.0,))) + VOIDS_DE
    t_fe = (INSERT,)
    g = geometry("full")
    path_al = LG.ellipsoid_projections(g, t_al, device=DEV)
    path_fe = LG.ellipsoid_projections(g, t_fe, device=DEV)
    low = MU_LOW[0] * path_al + MU_LOW[1] * path_fe
    high = MU_HIGH[0] * path_al + MU_HIGH[1] * path_fe
    sigma = NOISE * float(high.max())
    rng = np.random.default_rng(5)
    n_low, n_high = sigma * rng.standard_normal(low.shape), sigma * rng.standard_normal(high.shape)
    clean = LG.ct_dual_energy_reconstruct(low, high, g, MU_LOW, MU_HIGH, method="fdk", device=DEV,
                                          filter_name="hann")
    de = LG.ct_dual_energy_reconstruct(low + n_low, high + n_high, g, MU_LOW, MU_HIGH, method="fdk",
                                       device=DEV, filter_name="hann")
    truth_al = LG.ellipsoid_phantom(N, t_al, supersample=2)
    truth_fe = LG.ellipsoid_phantom(N, t_fe, supersample=2)
    e_al, e_fe = rms_error(clean["basis_0"], truth_al), rms_error(clean["basis_1"], truth_fe)
    print("  基底変換の条件数 %.1f" % de["condition"])
    print("  雑音なし: Al の基底の RMSE %.4f、Fe の基底の RMSE %.4f(真値は 0 / 1 の体積率)" % (e_al, e_fe))
    # Fe の入れ子の体積: Fe の基底を半値で 2 値化
    fe_vox = int(np.sum(np.asarray(de["basis_1"]) > 0.5))
    fe_true = void_volume_mm3(INSERT)
    print("  Fe の入れ子の体積: 再構成 %.3f mm³、閉形式 %.3f mm³(差 %+.1f %%)"
          % (fe_vox * VOX ** 3, fe_true, 100 * (fe_vox * VOX ** 3 / fe_true - 1)))
    check(abs(fe_vox * VOX ** 3 / fe_true - 1) < 0.15, "Fe の入れ子の体積が閉形式と 15 % 以内(雑音あり)")
    # 交差: 入れ子の中の Al の基底、母材の中の Fe の基底(どちらも 0 のはず)
    ins = LG.ellipsoid_phantom(N, ((INSERT[:3] + tuple(0.7 * v for v in INSERT[3:6]) + (0.0, 1.0)),),
                               supersample=1) > 0.5
    al_only = (truth_al > 0.99) & (truth_fe < 0.01) & interior_mask(N, 0.8)
    x_al = float(np.mean(np.asarray(clean["basis_0"])[ins]))
    x_fe = float(np.mean(np.asarray(clean["basis_1"])[al_only]))
    print("  交差(雑音なし): 入れ子の芯の Al の基底 %.3f、母材の Fe の基底 %.4f" % (x_al, x_fe))
    check(abs(x_al) < 0.1 and abs(x_fe) < 0.02, "Al と Fe が分かれる(交差 Al < 0.1・Fe < 0.02)")
    no_insert = interior_mask(N) & (truth_fe < 0.01)
    res, false_pos = measure_voids(de["basis_0"], VOIDS_DE, interior=no_insert)
    print("  Al の基底で空隙を測る: 2 値の体積 %s mm³・欠損 %s mm³(閉形式 %s)、偽の空隙 %d"
          % (" / ".join("%.3f" % v for v, _, _ in res), " / ".join("%.3f" % d for _, _, d in res),
             " / ".join("%.3f" % void_volume_mm3(r) for r in VOIDS_DE), false_pos))
    # 雑音の増幅: FDK は線形なので、基底 k の雑音 = ||inv(M) の k 行|| × (低エネルギー 1 回の雑音)
    inv = np.linalg.inv(np.array([MU_LOW, MU_HIGH]))
    single = LG.fdk_reconstruct(n_low, g, filter_name="hann", device=DEV)
    sd1 = float(np.std(single))
    amp = []
    for k, key in enumerate(("basis_0", "basis_1")):
        meas = float(np.std(np.asarray(de[key]) - np.asarray(clean[key]))) / sd1
        pred = float(np.hypot(inv[k, 0], inv[k, 1]))
        amp.append((meas, pred))
        print("  %s の雑音 / 1 回の撮影の雑音: 実測 %.2f 倍、閉形式 ||inv(M)_k|| = %.2f 倍" % (key, meas, pred))
        check(abs(meas / pred - 1) < 0.1, "%s の雑音の増幅が閉形式と 10 %% 以内" % key)
    return de, clean, truth_al, truth_fe, amp


# --------------------------------------------------------------------------- 図
def mid(vol, z=None):
    v = np.asarray(vol)
    return v[v.shape[0] // 2 if z is None else z]


def figures(recons, truth, results, tv_info, de, truth_al, truth_fe):
    if not figs.enabled():
        return
    z = int(round(void_center_vox(VOIDS_TEST[0])[0]))
    panels, caps = [], []
    for cond, _label in CONDITIONS:
        panels.append(mid(truth, z))
        caps.append("真値(z = %d)/ %s" % (z, cond))
        for m in METHODS:
            panels.append(mid(recons[(cond, m)], z))
            caps.append("%s / %s RMSE %.3f" % (cond, m, results[(cond, m)]["rms_err"]))
    figs.save_grid("slices", panels, caps, ncols=5, vrange=(0.0, 1.2), gray=True,
                   title="鋳物の断面(行 = 36 投影 / 12 投影 / 110° に 30 投影、列 = 真値・FDK・SIRT・OS-SART・TV)")
    header = ["条件", "手法", "RMSE", "体積誤差 2 値 %", "体積誤差 欠損 %", "重心誤差 mm", "見落とし", "偽"]
    rows = []
    for cond, _ in CONDITIONS:
        for m in METHODS:
            s = results[(cond, m)]
            rows.append([cond, m, "%.4f" % s["rms_err"], "%.1f" % (100 * s["vol_err"]), "%.1f" % (100 * s["def_err"]),
                         "%.3f" % s["cen_err"], str(s["missed"]), str(s["false"])])
    figs.save_table("ranking", header, rows, title="3 条件 × 4 手法(空隙 3 個、真値の閉形式と比べる)")
    series, styles = [], []
    for cond, _ in CONDITIONS:
        _w, cal, oracle = tv_info[cond]
        if len(oracle) < 2:
            continue
        ws = sorted(oracle)
        series.append(("%s(評価用・後知恵)" % cond, np.log10(ws), [oracle[w] for w in ws]))
        styles.append(None)
        series.append(("%s(較正用・選ぶ側)" % cond, np.log10(ws), [cal[w] for w in ws]))
        styles.append("dashed")
    figs.save_plot("tv_weight", series, xlabel="log10 tv_weight", ylabel="RMSE", styles=styles,
                   title="TV の重みと RMSE: 較正用(破線)で選んだ 3e-3 は評価用(実線)でも最良")
    big = [np.kron(mid(v), np.ones((8, 8))) for v in (de["basis_0"], truth_al, de["basis_1"], truth_fe)]
    figs.save_grid("dual_energy", big, ["Al の基底(雑音あり)", "Al の真値", "Fe の基底(雑音あり)", "Fe の真値"],
                   ncols=4, vrange=(-0.2, 1.2), gray=True,
                   title="デュアルエナジー: 鉄の入れ子を Al と Fe に分ける(Al の雑音は 1 回の撮影の約 41 倍)")
    assert not figs.errors(), figs.errors()


def main() -> int:
    t0 = time.time()
    print("BUDGET: %s(FULLSEYE_POC_BUDGET、CI では reduced が既定)格子 %d³、ボクセル %.2f mm"
          % ("reduced" if REDUCED else "full", N, VOX))
    chapter_truth()
    results, tv_info, recons, truth, sirt_curves = chapter_methods()
    gate_methods(results, tv_info, sirt_curves, truth)
    de, _clean, truth_al, truth_fe, _amp = chapter_dual_energy()
    figures(recons, truth, results, tv_info, de, truth_al, truth_fe)
    bad = [c for c in CHECKS if not c[0]]
    print()
    print("門: %d / %d 合格(%.1f 秒)" % (len(CHECKS) - len(bad), len(CHECKS), time.time() - t0))
    if not bad:
        print("PASS")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
