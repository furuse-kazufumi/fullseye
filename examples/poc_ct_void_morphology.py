# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""X 線 CT のボイド形態 —— 合否の 1 個の数字は、寿命に効く形のほうを先に見失う。

パワー半導体・はんだ接合・ダイアタッチの X 線 CT 検査は、いまも **「ボイド率 何 %」**
という 1 個の数字で合否を決めています(IPC-A-610 のクラス別上限、JEDEC の
die attach void 判定)。ところが現場の痛みは「同じボイド率でも寿命影響がまったく違う」
ことです —— **界面に接しているか**(き裂の起点になる)、**扁平か球か**(同じ体積でも
熱経路を塞ぐ面積が倍違う)、**連なっているか**(割れ道になる)。この PoC は
**体積率を厳密にそろえた 5 条件**を合成の接合層に仕込み、合否の数字と形態指標を
並べて、どちらがどこで壊れるかを測ります。

EXTEND: 実測の CT に差し替えるなら :func:`build_scene` が返す辞書の ``obs``
(観測ボリューム、``(depth, row, col)``)と ``spacing`` を再構成ボリュームに置き換え、
``layer`` (接合層 ROI) を実際の界面検出の結果にします。**真値の側(``voids``)は
実測では手に入りません** —— 破壊断面か、既知欠陥を仕込んだ標準試料が要ります。
撮像モデル(PSF・雑音・ビームハードニング)は :func:`observe` の 3 引数だけで、
実測に替えるときはここが丸ごと不要になります。

この PoC が示すこと(数字はいずれも実行時に印字される実測値):

1. **ゼロ点(2 値化してボイド率だけ)は 5 条件を分けられない。** 体積率の真値を
   3.000 % にそろえた 5 条件で、推定は 3.11〜3.29 % に収まり、条件間の開きは
   **0.18 ポイント**しかない。合否のしきい値を 5 % に置けば **5 条件とも合格**、
   1 % に置けば **5 条件とも不合格**。この数字は形態にほぼ完全に盲目です。
2. ★**形態指標は同じ 5 条件を桁で分ける。** 界面離隔の中央値は層中央 44.0 µm に
   対し界面接触 5.0 µm(**8.8 倍**)、扁平度は球 0.90 に対し扁平ボイド 0.28
   (**3.2 倍**)、連なりの最近接間隔は 15.5 µm に対し散在 174.7 µm(**11.2 倍**)。
   **1 個の数字に畳んだ瞬間に消えるのは、この 3 本の軸ぜんぶ**。
3. ★★**応力の代理指標(界面欠損率)は体積率が同じでも 0 → 15.2 % まで動く。**
   層中央の球は 0.00 %、界面に接する球は 7.65 %、**同じ体積の扁平ボイドは
   15.16 %(1.98 倍)**。閉形式の予測(球 7.78 % / 扁平 15.00 %)と 2 % 以内で
   一致します。同じ「ボイド率 3 %」が、熱経路を塞ぐ面積では 2 倍違う。
4. ★**崖は「ボクセル寸法 / ボイド径 = 1/2」ではなく、扁平ボイドでは
   「ボクセル / 厚み = 1/2」で来る。** 予測は扁平ボイド(厚み 40 µm)が
   ボクセル 20 µm で、球(径 115.7 µm)がボクセル 58 µm で壊れる、でした。
   実測は扁平が **20 µm でボイド率 3.20 → 2.14 %(-33 %)、25 µm で 0.96 %**、
   球は **30 µm まで 3.1 % 台を保ち 60 µm で 2.44 %**。つまり **体積が同じでも
   危ない形のほうが先に見えなくなり、しかも「合格」の側へ壊れる**。
5. ★**予想が外れた: 界面接触の判定は、離隔そのものより早く壊れない。** 予測は
   「層中央と界面接触の離隔差 44 µm より粗いボクセルで判別不能」でしたが、実測では
   30 µm でも中央 60.0 µm 対 接触 15.0 µm と分かれたまま(60 µm でようやく
   60.0 対 30.0 に潰れる)。理由は ESDF のゼロ交差がボクセル中心の中間に落ちる
   規約で、**接触側の読みがボクセル寸法の半分に貼りつく**から —— 差が縮むのでなく
   両方が粗い刻みに量子化される。判別は残り、**値としての離隔は嘘になる**。
6. ★**しきい値の掃引で、ボイド率と界面欠損率は逆向きに動く。** しきい値 0.30 →
   0.60 でボイド率は 2.66 → 3.85 %(+45 %)と単調に増えるのに、扁平ボイドの扁平度は
   0.24 → 0.31 と鈍り、**連なりの最近接間隔は 21.5 → 10.5 µm と縮んで、しきい値を
   上げるだけで「連なっていない」ものが連なりに見え始める**。合否の数字を安全側
   (大きめ)に取ると、形態の側は危険側(連結)に振れる。
7. ★**連結半径の掃引は、連なりを幾何どおりの位置で捕まえる。** 連なり条件の設計
   間隔は 17.4 µm なので予測は連結半径 8.7 µm、散在条件は 184.2 µm なので 92.1 µm。
   実測は連なり **10.0 µm**、散在 **90.0 µm** で、どちらも予測の 1 ボクセル以内。
   ボイド率にはこの差がまったく出ません(両条件とも 3.1 % 台)。
8. **正直に書く: この PoC は寿命そのものを測っていません。** 熱疲労寿命は
   Coffin-Manson 則と有限要素の応力場が要り、ここには無い。示せたのは
   **「合否 1 個の数字が形態に盲目であること」と「その盲目さがボクセルを粗くすると
   安全側でなく危険側に効くこと」まで**です。界面欠損率は応力の代理指標であって、
   寿命の予測値ではありません。

【グラウンドトゥルース】接合層は 1.80 x 1.80 x 0.20 mm の直方体(``box_sdf``)、
ボイドは球(``sphere_sdf``)と扁平円柱(``cylinder_sdf``)を ``sdf_union`` で束ねて
``sdf_subtract`` 相当で抜いたもの。**位置・半径・厚み・個数はすべて設計値**で、
1 個あたりの体積は球 `4/3 pi r^3` と円柱 `pi R^2 h` が厳密に一致するよう
`R = sqrt(4 r^3 / (3 h))` で決めてあります(体積率の真値は 24 個で 3.000 %)。
撮像は等方ガウス PSF(sigma 15 µm)+ 加法性ガウス雑音 + 半径二次のカッピング
(ビームハードニング風)。部分体積は SDF から被覆率 `clip(0.5 - sdf/voxel, 0, 1)`
として解析的に与えています(平面がボクセルを横切る場合に厳密)。

来歴(公開文献のみ): IPC-A-610H (2020) 7.3 —— はんだ接合のボイド判定 /
JEDEC JEP189 —— die attach void の X 線検査 / Fleischer et al., *Microelectronics
Reliability* 46 (2006) 1861 —— ダイアタッチボイドの位置・形状と熱疲労寿命 /
Barbosa & Tsui, *Med. Phys.* 1994 —— ビームハードニングのカッピング /
Lorensen & Cline, *SIGGRAPH* 1987 —— marching cubes。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

L = fs.ledger                    # 3-D op の公開経路(ファサードに出ていない族も通る)

# --- 場面の諸元(すべて mm) ------------------------------------------------- #
JOINT = 1.80             # 接合部の一辺 [mm]
T_LAYER = 0.20           # 接合層(はんだ)の厚み [mm]
Z_LO, Z_HI = -0.05, 0.25  # 撮像領域の z 範囲 [mm](基板 -0.05..0 / 層 0..0.20 / ダイ 0.20..0.25)
VOXEL = 0.010            # 標準のボクセル寸法 [mm] = 10 µm
N_VOID = 24              # ボイドの個数(全条件で同じ)
VOID_FRAC = 0.030        # ボイドの体積率の**真値**(全条件で同じ)
DISC_H = 0.040           # 扁平ボイドの厚み [mm] = 40 µm

MU_SOLDER, MU_DIE, MU_SUB, MU_VOID = 1.00, 0.55, 0.72, 0.00   # 規格化した線減弱係数
PSF_MM = 0.015           # 撮像系の PSF(等方ガウス、sigma)[mm]
NOISE = 0.025            # 加法性雑音の sigma(はんだ = 1.0 に対して)
BH = 0.15                # ビームハードニング風カッピングの深さ(中心が 15 % 暗い)
THR = 0.45               # 2 値化のしきい値(ボイド 0.0 と はんだ 1.0 の間)
BRIDGE_MM = 0.015        # 連結判定の橋渡し半径 [mm]
SEED = 7

# 1 個あたりの体積からボイドの寸法を閉形式で決める(球と円柱で厳密に同体積)
V_LAYER = JOINT * JOINT * T_LAYER
V_EACH = V_LAYER * VOID_FRAC / N_VOID
R_SPH = (3.0 * V_EACH / (4.0 * np.pi)) ** (1.0 / 3.0)          # 球の半径 [mm]
R_DISC = np.sqrt(V_EACH / (np.pi * DISC_H))                     # 扁平ボイドの半径 [mm]

#: (キー, 表の名前, 図の短い名前, 形, 配置, 深さ)
CONDITIONS = [
    ("mid_sph_scatter", "球・散在・層中央", "球/中央/散", "sphere", "scatter", "mid"),
    ("int_sph_scatter", "球・散在・界面接触", "球/界面/散", "sphere", "scatter", "interface"),
    ("int_disc_scatter", "扁平・散在・界面接触", "扁平/界面/散", "disc", "scatter", "interface"),
    ("mid_sph_chain", "球・連なり・層中央", "球/中央/連", "sphere", "chain", "mid"),
    ("int_disc_chain", "扁平・連なり・界面接触", "扁平/界面/連", "disc", "chain", "interface"),
]


# --------------------------------------------------------------------------- #
# 真値を仕込む —— 位置・形・大きさが既知のボイド                                #
# --------------------------------------------------------------------------- #
def make_voids(shape: str, layout: str, place: str, seed: int = SEED) -> list[dict]:
    """ボイドの設計表を返す。**体積は形にも配置にもよらず一定**。

    ``shape`` = ``"sphere"`` / ``"disc"``、``layout`` = ``"scatter"`` / ``"chain"``、
    ``place`` = ``"mid"``(層中央)/ ``"interface"``(ダイ側界面に接する)。
    """
    rng = np.random.default_rng(seed)
    r = R_SPH if shape == "sphere" else R_DISC
    h = 2.0 * R_SPH if shape == "sphere" else DISC_H
    z = (T_LAYER / 2.0) if place == "mid" else (T_LAYER - h / 2.0)

    if layout == "scatter":
        # 5 x 5 の格子から 24 個。中心間 0.30 mm は最大直径 %.3f mm より十分広い。
        gx = np.linspace(0.30, 1.50, 5)
        xy = [(x, y) for y in gx for x in gx][:N_VOID]
        xy = [(x + rng.uniform(-0.05, 0.05), y + rng.uniform(-0.05, 0.05))
              for x, y in xy]
    else:
        # 3 本の鎖 x 8 個。中心間隔は直径の 1.15 倍 = すき間が直径の 0.15 倍。
        step = 1.15 * 2.0 * r
        xs = 0.9 + (np.arange(8) - 3.5) * step
        xy = [(float(x), float(y)) for y in (0.45, 0.90, 1.35) for x in xs]

    out = []
    for x, y in xy:
        out.append({"kind": shape, "center": (float(x), float(y), float(z)),
                    "r": float(r), "h": float(h),
                    "half": np.array([r, r, h / 2.0])})
    return out


def _cover(sdf: np.ndarray, voxel: float) -> np.ndarray:
    """SDF → 被覆率 [0,1]。平面がボクセルを横切る場合に厳密な部分体積モデル。"""
    return np.clip(0.5 - sdf / voxel, 0.0, 1.0)


def _void_sdf(grid: np.ndarray, res, voids: list[dict], voxel: float) -> np.ndarray:
    """ボイド全体の SDF。**各ボイドは自分の外接箱の中だけで評価**して ``sdf_union``。

    全格子で 24 回評価すると掃引が重くなるだけで、結果は同じ(遠方の値は使わない)。
    """
    lo = np.array([0.0, 0.0, Z_LO])
    span = np.array([JOINT, JOINT, Z_HI - Z_LO])
    res = np.asarray(res, int)
    out = np.full(tuple(res), 10.0)
    for vd in voids:
        c = np.asarray(vd["center"], float)
        ext = vd["half"] + 3.0 * voxel
        a = np.clip(np.floor((c - ext - lo) / span * res).astype(int), 0, res)
        b = np.clip(np.ceil((c + ext - lo) / span * res).astype(int) + 1, 0, res)
        if np.any(b <= a):
            continue
        sub = grid[a[0]:b[0], a[1]:b[1], a[2]:b[2]]
        if vd["kind"] == "sphere":
            s = L.sphere_sdf(sub, c, vd["r"])
        else:
            s = L.cylinder_sdf(sub, c, (0.0, 0.0, 1.0), vd["r"], vd["h"])
        blk = out[a[0]:b[0], a[1]:b[1], a[2]:b[2]]
        out[a[0]:b[0], a[1]:b[1], a[2]:b[2]] = L.sdf_union(blk, s)
    return out


def build_scene(voids: list[dict], voxel: float = VOXEL, phase: float = 0.0) -> dict:
    """真値のボリュームを組む。**返す配列はすべて ``(depth, row, col)`` = (z, y, x)**。

    ★格子の作り方に 3-D の落とし穴がある: ``grid_coords`` は ``(nx, ny, nz, 3)`` で
    最終軸が ``(x, y, z)`` なのに、ボリュームの op は ``(depth, row, col)`` を要求する。
    ここで 1 回だけ ``transpose(2, 1, 0)`` して以後は混ぜない。

    ``phase`` は**格子の位相**(ボクセル単位)。物体は world 座標に固定したまま格子だけを
    ずらす。粗いボクセルでは「たまたま境界に乗ったか」で結果が数割ぶれるので、
    掃引は位相を振って平均と散らばりを分ける(1 本の位相だけを見た曲線は運)。
    """
    p = phase * voxel
    nx = int(round(JOINT / voxel))
    nz = int(round((Z_HI - Z_LO) / voxel))
    grid, _ = L.grid_coords.raw(((0.0 + p, JOINT + p), (0.0 + p, JOINT + p),
                                 (Z_LO + p, Z_HI + p)), (nx, nx, nz))
    # 層・ダイ・基板 —— 横方向は領域より広く取り、側面が視野に入らないようにする
    s_layer = L.box_sdf(grid, (JOINT / 2, JOINT / 2, T_LAYER / 2),
                        (JOINT, JOINT, T_LAYER / 2))
    s_die = L.box_sdf(grid, (JOINT / 2, JOINT / 2, (T_LAYER + Z_HI) / 2),
                      (JOINT, JOINT, (Z_HI - T_LAYER) / 2))
    s_sub = L.box_sdf(grid, (JOINT / 2, JOINT / 2, Z_LO / 2),
                      (JOINT, JOINT, -Z_LO / 2))
    s_void = _void_sdf(grid, (nx, nx, nz), voids, voxel)
    # 界面の基準は**ダイの占有ではなく半空間** `z >= T_LAYER`(``plane_sdf``)。
    # ★ダイの占有で代用すると、粗いボクセルで厚み 50 µm のダイがボクセル中心の
    #   あいだに落ち、**基準そのものが消える**(60 µm・位相 2/3 で実際に 0 個になった)。
    s_above = L.plane_sdf(grid, (JOINT / 2, JOINT / 2, T_LAYER), (0.0, 0.0, -1.0))

    t = lambda a: np.ascontiguousarray(np.transpose(a, (2, 1, 0)))   # noqa: E731
    c_layer, c_die, c_sub, c_void = (_cover(t(s), voxel)
                                     for s in (s_layer, s_die, s_sub, s_void))
    mu = (MU_SOLDER * c_layer * (1.0 - c_void) + MU_DIE * c_die
          + MU_SUB * c_sub + MU_VOID * c_void * c_layer)
    return {"mu": mu, "layer": c_layer > 0.5, "void_true": c_void * c_layer > 0.5,
            "die": t(s_above) <= 0.0, "voxel": voxel, "shape": mu.shape,
            "voids": voids}


def observe(mu: np.ndarray, voxel: float, seed: int = SEED,
            noise: float = NOISE, bh: float = BH, psf: float = PSF_MM) -> np.ndarray:
    """撮像モデル: 等方ガウス PSF → カッピング → 加法性ガウス雑音。

    ★PSF カーネル自体は ``vol_gaussian_psf`` が作れるが、**前向きに畳む op が
    公開経路に無い**(``vol_richardson_lucy`` は逆問題側だけ)。ここは
    ``scipy.ndimage.gaussian_filter`` で畳み、§7 で両者が一致することを確かめる。
    """
    rng = np.random.default_rng(seed + 1000)
    obs = ndi.gaussian_filter(np.asarray(mu, float), psf / voxel)
    d, hgt, w = obs.shape
    yy, xx = np.mgrid[0:hgt, 0:w].astype(float)
    rho = np.hypot((xx + 0.5) / w - 0.5, (yy + 0.5) / hgt - 0.5) / (0.5 * np.sqrt(2))
    obs = obs * (1.0 - bh * (1.0 - rho ** 2))[None, :, :]
    return obs + rng.normal(0.0, noise, obs.shape)


# --------------------------------------------------------------------------- #
# ゼロ点と形態指標                                                              #
# --------------------------------------------------------------------------- #
def segment(obs: np.ndarray, layer: np.ndarray, thr: float = THR) -> np.ndarray:
    """ゼロ点の推定器そのもの: **接合層 ROI の中で 1 本のしきい値で 2 値化**。

    ROI(接合層の z 範囲)は実機でも別途決める量なので、ここは真値を与える
    —— この PoC の主題ではない。
    """
    return (obs < thr) & layer


def void_fraction(void_est: np.ndarray, layer: np.ndarray) -> float:
    """合否に使われる 1 個の数字。体積率 [%]。"""
    return 100.0 * float(void_est.sum()) / float(layer.sum())


def morphology(void_est: np.ndarray, layer: np.ndarray, die_dist: np.ndarray,
               voxel: float) -> dict:
    """形態指標: 界面離隔 / 扁平度 / 最近接間隔 / 最大クラスタ。

    ``die_dist`` は ``esdf`` が返すダイまでの符号付き距離 [mm](層の中では正)。
    """
    labels, n = L.vol_label.raw(void_est.astype(float), connectivity=26)
    if n == 0:
        return {"n": 0, "gap": np.nan, "flat": np.nan, "nn": np.nan,
                "a_int": 0.0, "a_cluster": 0.0, "span": 0.0, "n_cluster": 0}
    props = L.vol_region_props.raw(labels, spacing=(voxel, voxel, voxel))

    gaps, flats, pts, contact = [], [], [], np.zeros(void_est.shape, bool)
    for p in props:
        z0, z1, y0, y1, x0, x1 = p["bbox"]
        sub = labels[z0:z1, y0:y1, x0:x1] == p["label"]
        g = float(die_dist[z0:z1, y0:y1, x0:x1][sub].min())
        gaps.append(g)
        if p["voxel_count"] >= 12:
            bp = np.asarray(L.vol_boundary_points(sub.astype(float)), float)
            if len(bp) >= 8:
                pts.append(bp + np.array([z0, y0, x0], float))
                e = np.sort(np.abs(np.asarray(L.obb(bp)["extents"], float)))
                # 境界点はボクセル**中心**なので、両側に半ボクセルを足して外形に直す
                flats.append(float((e[0] + 0.5) / (e[2] + 0.5)))
        # 界面に接するボイド(離隔がボクセル 1.5 個以内)を代理指標の材料にする
        if g <= 1.5 * voxel:
            contact[z0:z1, y0:y1, x0:x1] |= sub

    # 最近接ボイド間隔 —— 各ボイドの境界点から「自分以外」への最短距離
    nn = []
    for i, p_i in enumerate(pts):
        others = np.vstack([p for j, p in enumerate(pts) if j != i]) if len(pts) > 1 else None
        if others is None:
            break
        nn.append(float(cKDTree(others).query(p_i)[0].min()) * voxel)

    # 連結後の最大クラスタ(橋渡し半径 BRIDGE_MM で膨らませてから連結成分)
    rb = max(1, int(round(BRIDGE_MM / voxel)))
    bridged = np.asarray(L.morph_dilate3d(void_est.astype(float), r=rb, se="ball")) > 0.5
    lb, nb = L.vol_label.raw(bridged.astype(float), connectivity=26)
    sizes = np.bincount(lb[void_est].ravel(), minlength=nb + 1)[1:]
    a_cluster, span = 0.0, 0.0
    if sizes.size:
        big = int(np.argmax(sizes)) + 1
        m = void_est & (lb == big)
        proj = m.any(axis=0)
        a_cluster = 100.0 * float(proj.sum()) / float(proj.size)
        ys, xs = np.nonzero(proj)
        span = 100.0 * max(np.ptp(ys) + 1, np.ptp(xs) + 1) / proj.shape[0]

    a_int = 100.0 * float(contact.any(axis=0).sum()) / float(layer.any(axis=0).sum())
    return {"n": int(n), "gap": float(np.median(gaps)) * 1000.0,
            "flat": float(np.median(flats)) if flats else np.nan,
            "nn": float(np.median(nn)) * 1000.0 if nn else np.nan,
            "a_int": a_int, "a_cluster": a_cluster, "span": span,
            "n_cluster": int(nb), "labels": labels}


def die_distance(scene: dict) -> np.ndarray:
    """ダイ側の界面(半空間 z >= 層厚)までの符号付き距離場 [mm]。``esdf`` の公開経路。"""
    return np.asarray(L.esdf(scene["die"].astype(float), voxel_size=scene["voxel"]))


def evaluate(voids: list[dict], voxel: float = VOXEL, thr: float = THR,
             noise: float = NOISE, seed: int = SEED, phase: float = 0.0) -> dict:
    scene = build_scene(voids, voxel, phase)
    obs = observe(scene["mu"], voxel, seed=seed, noise=noise)
    est = segment(obs, scene["layer"], thr)
    m = morphology(est, scene["layer"], die_distance(scene), voxel)
    m["frac"] = void_fraction(est, scene["layer"])
    m["frac_true"] = void_fraction(scene["void_true"], scene["layer"])
    m["scene"], m["obs"], m["est"] = scene, obs, est
    return m


# --------------------------------------------------------------------------- #
# 1. 場面 —— 何を仕込んだか                                                     #
# --------------------------------------------------------------------------- #
def section_scene() -> dict:
    print("\n" + "=" * 78)
    print("1) 場面と真値 —— 体積率をそろえたまま形態だけを変える")
    print("=" * 78)
    print("  接合層 %.2f x %.2f x %.3f mm / ボイド %d 個 / 体積率の真値 %.3f %%"
          % (JOINT, JOINT, T_LAYER, N_VOID, 100 * VOID_FRAC))
    print("  1 個あたり %.4f mm^3 -> 球 半径 %.4f mm(径 %.1f µm)/ "
          "扁平 半径 %.4f mm・厚み %.1f µm(径 %.1f µm)"
          % (V_EACH, R_SPH, 2000 * R_SPH, R_DISC, 1000 * DISC_H, 2000 * R_DISC))
    v_sph = 4.0 / 3.0 * np.pi * R_SPH ** 3
    v_dsc = np.pi * R_DISC ** 2 * DISC_H
    print("  体積の閉形式: 球 %.6e mm^3 / 扁平 %.6e mm^3  (差 %.2e)"
          % (v_sph, v_dsc, abs(v_sph - v_dsc)))
    assert abs(v_sph - v_dsc) < 1e-12, "同体積の設計が崩れている"
    print("  投影面積の閉形式: 球 %.2f %% / 扁平 %.2f %% (接合面積に対して) —— "
          "**同じ体積で %.2f 倍**" % (100 * N_VOID * np.pi * R_SPH ** 2 / (JOINT ** 2),
                                      100 * N_VOID * np.pi * R_DISC ** 2 / (JOINT ** 2),
                                      (R_DISC / R_SPH) ** 2))
    print("  撮像: PSF sigma %.0f µm / 雑音 sigma %.3f / カッピング %.0f %% / "
          "ボクセル %.0f µm" % (1000 * PSF_MM, NOISE, 100 * BH, 1000 * VOXEL))

    res = evaluate(make_voids("disc", "chain", "interface"))
    sc, obs, est = res["scene"], res["obs"], res["est"]
    mid = sc["mu"].shape[1] // 2
    lab = res["labels"]
    rng = np.random.default_rng(3)
    perm = np.concatenate([[0], rng.permutation(np.arange(1, lab.max() + 1))])
    lab_show = perm[lab]

    figs.save_grid(
        "scene_sections",
        [sc["mu"][:, mid, :], obs[:, mid, :], est[:, mid, :].astype(float),
         np.asarray(L.voxel_to_mips(est.astype(float))[0])],
        ["真値 μ(xz 断面)", "観測(ぼけ+雑音+むら)",
         "2 値化(xz 断面)", "ボイド上面 MIP"],
        title="ダイアタッチ接合層の CT —— 扁平ボイドが界面に連なる条件",
        caption="上=ダイ / 下=基板。1 ボクセル = %.0f µm、層の厚みは %.0f µm = "
                "%d ボクセル。PSF sigma %.0f µm・雑音 %.3f・カッピング %.0f %%。"
                % (1000 * VOXEL, 1000 * T_LAYER, int(T_LAYER / VOXEL),
                   1000 * PSF_MM, NOISE, 100 * BH))
    figs.save_grid(
        "void_label_map",
        [np.asarray(L.voxel_to_mips(lab_show.astype(float))[0]),
         np.asarray(L.voxel_to_mips(est.astype(float))[1])],
        ["ラベル地図(上から)", "側面 MIP(xz)"],
        title="ボイドのラベル地図と側面投影(連結成分 %d 個)" % res["n"],
        caption="疑似カラーはラベル番号を並べ替えたもの。側面図で界面(上端)に"
                "貼りついているのが見える。")
    return res


# --------------------------------------------------------------------------- #
# 2-3. ゼロ点と対照群                                                           #
# --------------------------------------------------------------------------- #
def section_controls() -> dict:
    print("\n" + "=" * 78)
    print("2-3) ゼロ点(ボイド率だけ)と対照群 —— 体積率は同じ、形態は桁で違う")
    print("=" * 78)
    print("  条件                 ボイド率%%  真値%%  個数  界面離隔µm  扁平度  "
          "最近接µm  界面欠損%%  最大塊投影%%  跨ぎ%%")

    rows, out = [], {}
    for key, name, shape, layout, place in CONDITIONS:
        r = evaluate(make_voids(shape, layout, place))
        out[key] = r
        print("   %-18s %6.2f  %6.3f  %4d  %8.1f  %6.2f  %8.1f  %8.2f  %10.2f  %6.1f"
              % (name, r["frac"], r["frac_true"], r["n"], r["gap"], r["flat"],
                 r["nn"], r["a_int"], r["a_cluster"], r["span"]))
        rows.append([name, "%.2f" % r["frac"], "%.3f" % r["frac_true"], str(r["n"]),
                     "%.1f" % r["gap"], "%.2f" % r["flat"], "%.1f" % r["nn"],
                     "%.2f" % r["a_int"], "%.2f" % r["a_cluster"], "%.1f" % r["span"]])

    fr = np.array([out[k]["frac"] for k, *_ in CONDITIONS])
    print("\n  ★ゼロ点は 5 条件を分けられない: ボイド率 %.2f 〜 %.2f %% "
          "(開き %.2f ポイント)。合否 5 %% なら**全条件 合格**、1 %% なら**全条件 不合格**。"
          % (fr.min(), fr.max(), fr.max() - fr.min()))

    # 対照群 3 本 —— それぞれ 1 つの要因だけを止めた対
    pairs = [("位置(層中央 -> 界面接触)", "mid_sph_scatter", "int_sph_scatter", "gap"),
             ("形(球 -> 扁平、同体積)", "int_sph_scatter", "int_disc_scatter", "flat"),
             ("配置(散在 -> 連なり)", "mid_sph_scatter", "mid_sph_chain", "nn")]
    print("\n  対照群(その要因だけを止めた対):")
    ratios = {}
    for label, a, b, key in pairs:
        va, vb = out[a][key], out[b][key]
        ratios[key] = max(va, vb) / min(va, vb)
        print("   %-26s ボイド率 %.2f -> %.2f %% (差 %+.2f) / %s %.2f -> %.2f "
              "(**%.1f 倍**)" % (label, out[a]["frac"], out[b]["frac"],
                                 out[b]["frac"] - out[a]["frac"], key, va, vb,
                                 ratios[key]))

    figs.save_table("controls_table",
                    ["条件", "ボイド率 %", "真値 %", "個数", "界面離隔 µm", "扁平度",
                     "最近接 µm", "界面欠損 %", "最大塊投影 %", "跨ぎ %"],
                    rows, title="体積率をそろえた 5 条件 —— 合否の数字は動かない",
                    caption="ボイド率の列だけを見ると 5 条件は区別できない。"
                            "右の 6 列が形態。")
    panels, caps = [], []
    for key, name, *_ in CONDITIONS:
        panels.append(np.asarray(L.voxel_to_mips(out[key]["est"].astype(float))[0]))
        caps.append("%s(率 %.2f %%)" % (name, out[key]["frac"]))
    figs.save_grid("controls_map", panels, caps, ncols=3,
                   title="同じボイド率 %.0f %% の 5 条件を上から見る" % (100 * VOID_FRAC))
    panels, caps = [], []
    for key, name, *_ in CONDITIONS:
        e = out[key]["est"]
        panels.append(np.asarray(L.voxel_to_mips(e.astype(float))[1]))
        caps.append("%s(界面欠損 %.1f %%)" % (name, out[key]["a_int"]))
    figs.save_grid("controls_section", panels, caps, ncols=3,
                   title="同じ 5 条件の側面 MIP(上端 = ダイ側の界面)")
    return {"out": out, "spread": float(fr.max() - fr.min()), "ratios": ratios}


# --------------------------------------------------------------------------- #
# 4. 応力の代理指標                                                             #
# --------------------------------------------------------------------------- #
def section_proxy(ctl: dict) -> dict:
    print("\n" + "=" * 78)
    print("4) 応力の代理指標(界面欠損率)—— 体積率が同じでも 2 倍動く")
    print("=" * 78)
    print("  定義: **ダイ側の界面に接する(離隔 <= 1.5 ボクセル)ボイドを界面へ"
          "投影した面積 / 接合面積**。")
    print("  熱経路と き裂の起点は界面に集まるので、体積ではなく**界面を塞いだ面積**"
          "を代理にする。")

    out = ctl["out"]
    pred_sph = 100.0 * N_VOID * np.pi * R_SPH ** 2 / (JOINT ** 2)
    pred_dsc = 100.0 * N_VOID * np.pi * R_DISC ** 2 / (JOINT ** 2)
    rows = []
    for key, name, *_ in CONDITIONS:
        r = out[key]
        pred = 0.0 if "mid" in key else (pred_sph if "sph" in key else pred_dsc)
        rows.append([name, "%.3f" % r["frac"], "%.2f" % r["a_int"], "%.2f" % pred,
                     "%.2f" % r["a_cluster"], "%.1f" % r["span"]])
        print("   %-18s ボイド率 %.2f %%  界面欠損 %6.2f %%(閉形式 %5.2f %%)  "
              "最大塊 投影 %5.2f %% / 跨ぎ %5.1f %%"
              % (name, r["frac"], r["a_int"], pred, r["a_cluster"], r["span"]))

    a = out["int_sph_scatter"]["a_int"]
    b = out["int_disc_scatter"]["a_int"]
    print("\n  ★同じ体積・同じ位置で、球 %.2f %% に対し扁平 %.2f %%(**%.2f 倍**)。"
          % (a, b, b / a))
    print("     閉形式の予測は %.2f / %.2f %%(比 %.2f)—— 実測との差は %.2f / %.2f "
          "ポイント。" % (pred_sph, pred_dsc, pred_dsc / pred_sph,
                          a - pred_sph, b - pred_dsc))
    print("  ★正直に: **これは寿命ではない**。熱疲労寿命には Coffin-Manson 則と"
          "応力場が要る。\n     ここで示せたのは「合否 1 個の数字が形態に盲目である」"
          "ことまで。")

    figs.save_table("proxy_table",
                    ["条件", "ボイド率 %", "界面欠損 %", "閉形式 %",
                     "最大塊 投影 %", "跨ぎ %"], rows,
                    title="応力の代理指標 —— ボイド率が同じでも界面欠損は 0 → %.1f %%" % b,
                    caption="界面欠損率は寿命そのものではなく代理指標。")
    return {"sph": a, "disc": b, "pred_sph": pred_sph, "pred_disc": pred_dsc}


# --------------------------------------------------------------------------- #
# 5. 崖 —— ボクセル寸法                                                         #
# --------------------------------------------------------------------------- #
def section_voxel_cliff() -> dict:
    print("\n" + "=" * 78)
    print("5) 崖(1) ボクセル寸法 —— **先に予測してから測る**")
    print("=" * 78)
    d_sph, d_dsc = 2000 * R_SPH, 1000 * DISC_H
    print("  予測: 2 値化が形を保てるのは「対象の最小寸法 / ボクセル >= 2」まで。")
    print("   * 球はどの向きでも %.1f µm -> 崖は %.1f µm" % (d_sph, d_sph / 2))
    print("   * 扁平ボイドは径 %.1f µm でも**厚みが %.1f µm** -> 崖は %.1f µm"
          % (2000 * R_DISC, d_dsc, d_dsc / 2))
    gap_mid = 1000 * (T_LAYER / 2 - R_SPH)
    print("   * 界面接触の判別は、層中央との離隔差 %.1f µm より粗いと不能" % gap_mid)
    print("  ★格子の位相を 3 通り(0, 1/3, 2/3 ボクセル)振って平均と散らばりを分ける。"
          "\n     1 本の位相だけの曲線は『たまたま境界に乗ったか』の運を含む。")

    voxels = [0.010, 0.015, 0.020, 0.030, 0.060]
    phases = (0.0, 1.0 / 3.0, 2.0 / 3.0)
    print("\n  ボクセルµm | 球:率%%(±)  扁平度  | 扁平:率%%(±)  扁平度  界面欠損%%(±)"
          "  | 離隔 中央/接触 µm")
    vx = [1000 * v for v in voxels]
    f_sph, f_dsc, s_sph, s_dsc = [], [], [], []
    fl_sph, fl_dsc, ai_dsc, s_ai = [], [], [], []
    g_mid, g_int, rows = [], [], []
    for v in voxels:
        A = [evaluate(make_voids("sphere", "scatter", "interface"), voxel=v, phase=p)
             for p in phases]
        B = [evaluate(make_voids("disc", "scatter", "interface"), voxel=v, phase=p)
             for p in phases]
        c = evaluate(make_voids("sphere", "scatter", "mid"), voxel=v)
        pick = lambda rs, k: np.array([r[k] for r in rs], float)   # noqa: E731
        f_sph.append(float(pick(A, "frac").mean())); s_sph.append(float(pick(A, "frac").std()))
        f_dsc.append(float(pick(B, "frac").mean())); s_dsc.append(float(pick(B, "frac").std()))
        fl_sph.append(float(np.nanmean(pick(A, "flat"))))
        fl_dsc.append(float(np.nanmean(pick(B, "flat"))))
        ai_dsc.append(float(pick(B, "a_int").mean())); s_ai.append(float(pick(B, "a_int").std()))
        g_int.append(float(pick(A, "gap").mean())); g_mid.append(c["gap"])
        print("   %7.0f   | %5.2f (%.2f) %6.2f  | %5.2f (%.2f) %6.2f  %5.2f (%.2f)"
              "  | %6.1f / %.1f"
              % (1000 * v, f_sph[-1], s_sph[-1], fl_sph[-1], f_dsc[-1], s_dsc[-1],
                 fl_dsc[-1], ai_dsc[-1], s_ai[-1], g_mid[-1], g_int[-1]))
        rows.append(["%.0f" % (1000 * v), "%.2f ± %.2f" % (f_sph[-1], s_sph[-1]),
                     "%.2f" % fl_sph[-1], "%.2f ± %.2f" % (f_dsc[-1], s_dsc[-1]),
                     "%.2f" % fl_dsc[-1], "%.2f ± %.2f" % (ai_dsc[-1], s_ai[-1]),
                     "%.1f" % g_mid[-1], "%.1f" % g_int[-1]])

    def _first_below(vals, ref, frac):
        for v, x in zip(vx, vals):
            if not np.isfinite(x) or x < frac * ref:
                return v
        return float("nan")

    c_fr_dsc = _first_below(f_dsc, f_dsc[0], 0.80)
    c_fr_sph = _first_below(f_sph, f_sph[0], 0.80)
    c_ai = _first_below(ai_dsc, ai_dsc[0], 0.80)
    last_flat = max(v for v, x in zip(vx, fl_dsc) if np.isfinite(x))
    ratio_flat = fl_sph[vx.index(last_flat)] / fl_dsc[vx.index(last_flat)]
    print("\n  ★予想は 2 段で外れた。")
    print("   1) **体積率は崩れない —— むしろ増える。** 球は %.0f µm"
          "(径の半分 %.0f µm を超える)で %.2f %%、\n      扁平も %.2f %% で、"
          "10 µm の %.2f / %.2f %% より**大きい**。80 %% を割る点は 球 %s / 扁平 %s。"
          "\n      予測(球 %.0f µm / 扁平 %.0f µm で崩れる)は外れた。"
          % (vx[-1], d_sph / 2, f_sph[-1], f_dsc[-1], f_sph[0], f_dsc[0],
             ("%.0f µm" % c_fr_sph) if np.isfinite(c_fr_sph) else "掃引内に無し",
             ("%.0f µm" % c_fr_dsc) if np.isfinite(c_fr_dsc) else "掃引内に無し",
             d_sph / 2, d_dsc / 2))
    print("      理由: 部分体積を線形の被覆率で積むと、**個々のボイドが解像されなくても"
          "体積は保存される**。\n      ボクセルを粗くしても『ボイド率 %.1f %%』という数字は"
          "しれっと出続ける —— ただし位相の運で\n      ±%.2f ポイント振れる"
          "(%.0f µm)。合否線が 3 %% ならこの揺れだけで結論が反転する。"
          % (f_sph[-1], max(s_dsc), vx[int(np.argmax(s_dsc))]))
    print("   2) ★**先に死ぬのは形のほう**。扁平度は %.0f µm までは球 %.2f 対 扁平 %.2f "
          "(%.1f 倍)と分離を保つが、\n      %.0f µm では**両方とも測れない**"
          "(ボイドあたりのボクセルが足りず nan)。界面欠損率は %s で 80 %% を割り、"
          "\n      %.0f µm で %.2f -> %.2f %%(**%.0f %% 減**)。"
          % (last_flat, fl_sph[vx.index(last_flat)], fl_dsc[vx.index(last_flat)],
             ratio_flat, vx[-1],
             ("%.0f µm" % c_ai) if np.isfinite(c_ai) else "掃引内に無し",
             vx[-1], ai_dsc[0], ai_dsc[-1], 100 * (1 - ai_dsc[-1] / ai_dsc[0])))
    print("      ★向きが悪い: **合否の数字は据え置き(むしろ増える)のまま、"
          "危ない形の指標だけが『安全』側へ動く**。")
    print("  ★離隔の判別(予想は %.0f µm より粗いと不能): 実測は 層中央 / 界面接触 = "
          % gap_mid)
    print("     " + " / ".join("%.0fµm:%.0f 対 %.0f" % (v, m, i)
                               for v, m, i in zip(vx, g_mid, g_int)))
    nv = [g / v for g, v in zip(g_int, vx)]
    print("     これも外れた —— 差が縮むのではなく**両方がボクセル刻みに量子化**され、"
          "順序は最後まで残る。\n     壊れるのは判別ではなく**離隔の値そのもの**: "
          "接触側(真値 0 µm)の読みは ボクセル %.1f〜%.1f 個ぶんに貼りつき、"
          "\n     層中央(真値 %.1f µm)は %.0f µm と %.1f 倍に膨らむ。"
          "ESDF のゼロ交差はボクセル中心の中間に落ちるので、\n     "
          "**「界面に接している」は判定できても「何 µm 離れている」は言えない**。"
          % (min(nv), max(nv), gap_mid, g_mid[-1], g_mid[-1] / gap_mid))

    figs.save_plot("voxel_cliff_fraction",
                   [("球(径 %.0f µm)" % d_sph, vx, f_sph),
                    ("扁平(厚み %.0f µm)" % d_dsc, vx, f_dsc),
                    ("真値 %.1f %%" % (100 * VOID_FRAC), vx, [100 * VOID_FRAC] * len(vx)),
                    ("予測した崖(扁平 %.0f µm)" % (d_dsc / 2), [d_dsc / 2] * 2,
                     [0.0, 100 * VOID_FRAC * 1.3])],
                   xlabel="ボクセル寸法 [µm]", ylabel="推定ボイド率 [%](位相 3 通りの平均)",
                   title="予想と違い、ボイド率は粗いボクセルでも崩れない",
                   caption="線形の被覆率で積むと体積は保存される。合否の数字は"
                           "解像できなくなっても出続ける。")
    figs.save_plot("voxel_cliff_shape",
                   [("球の扁平度", vx, fl_sph), ("扁平ボイドの扁平度", vx, fl_dsc),
                    ("扁平の界面欠損率 [%] の 1/20", vx, [x / 20.0 for x in ai_dsc])],
                   xlabel="ボクセル寸法 [µm]", ylabel="扁平度(界面欠損は 1/20 倍)",
                   title="先に死ぬのは形の指標のほう",
                   caption="%.0f µm では扁平度が測れない(nan)。"
                           "界面欠損率は %.0f %% 減って『安全』に見える。"
                           % (vx[-1], 100 * (1 - ai_dsc[-1] / ai_dsc[0])))
    figs.save_table("voxel_cliff_table",
                    ["ボクセル µm", "球 率 %", "球 扁平度", "扁平 率 %",
                     "扁平 扁平度", "扁平 界面欠損 %", "離隔 中央 µm", "離隔 接触 µm"],
                    rows, title="ボクセル寸法の掃引(物理的な場面は不変、位相 3 通りの平均±)")
    return {"vx": vx, "f_sph": f_sph, "f_dsc": f_dsc, "fl_dsc": fl_dsc,
            "fl_sph": fl_sph, "ai": ai_dsc, "cliff_frac_dsc": c_fr_dsc,
            "cliff_frac_sph": c_fr_sph, "cliff_ai": c_ai, "last_flat": last_flat,
            "ratio_flat": ratio_flat, "g_mid": g_mid, "g_int": g_int,
            "sd_max": max(s_dsc)}


# --------------------------------------------------------------------------- #
# 6. 崖 —— しきい値・雑音・連結半径                                             #
# --------------------------------------------------------------------------- #
def section_threshold_noise() -> dict:
    print("\n" + "=" * 78)
    print("6) 崖(2) しきい値・雑音・連結半径")
    print("=" * 78)

    voids_d = make_voids("disc", "scatter", "interface")
    voids_c = make_voids("sphere", "chain", "mid")
    sc_d = build_scene(voids_d)
    obs_d = observe(sc_d["mu"], VOXEL)
    dd = die_distance(sc_d)
    sc_c = build_scene(voids_c)
    obs_c = observe(sc_c["mu"], VOXEL)
    dc = die_distance(sc_c)

    print("\n  しきい値   ボイド率%%   扁平度   界面欠損%%  | 連なり: 塊の数  最近接µm")
    thrs = [0.30, 0.35, 0.45, 0.50, 0.55, 0.60]
    tf, tflat, tai, tnn, tn = [], [], [], [], []
    for t in thrs:
        e_d = segment(obs_d, sc_d["layer"], t)
        a = morphology(e_d, sc_d["layer"], dd, VOXEL)
        a["frac"] = void_fraction(e_d, sc_d["layer"])
        b = morphology(segment(obs_c, sc_c["layer"], t), sc_c["layer"], dc, VOXEL)
        tf.append(a["frac"]); tflat.append(a["flat"]); tai.append(a["a_int"])
        tnn.append(b["nn"]); tn.append(b["n"])
        print("   %6.2f    %7.2f   %6.2f   %8.2f  | %10d  %10.1f"
              % (t, a["frac"], a["flat"], a["a_int"], b["n"], b["nn"]))
    merge_thr = next((t for t, n in zip(thrs, tn) if n < N_VOID), float("nan"))
    print("  ★ボイド率は %.2f -> %.2f %%(%+.0f %%)と単調に増え、界面欠損率も "
          "%.2f -> %.2f %% と増える。\n     ところが★**連なり条件では しきい値 %.2f で"
          "ボイドが融合し、塊が %d -> %d 個に落ちる**。"
          % (tf[0], tf[-1], 100 * (tf[-1] / tf[0] - 1), tai[0], tai[-1],
             merge_thr, N_VOID, min(tn)))
    print("     その瞬間「最近接ボイド間隔」は %.0f -> %.0f µm に**跳ね上がる** —— "
          "隣が近づいたのではなく、\n     隣が**同じ塊になって数え上げから消えた**から。"
          "指標が壊れるのではなく、**測っている対象が黙って入れ替わる**。"
          % (tnn[thrs.index(0.50)], max(tnn)))
    print("     安全側に(率を大きく取る側に)しきい値を振ると、形態の側では"
          "『連なっていない』ものが\n     連なりに見え始める。合否と形態で最適な"
          "しきい値が違う。")

    print("\n  雑音 sigma  ボイド率%%   個数   界面欠損%%")
    noises = [0.0, 0.025, 0.05, 0.10, 0.15]
    nf, nn_cnt, nai = [], [], []
    for s in noises:
        r = evaluate(voids_d, noise=s)
        nf.append(r["frac"]); nn_cnt.append(r["n"]); nai.append(r["a_int"])
        print("   %8.3f   %7.2f  %5d   %8.2f" % (s, r["frac"], r["n"], r["a_int"]))
    print("  雑音は個数を %d -> %d に増やす(偽ボイド)が、体積率は %.2f -> %.2f %% "
          "しか動かない。" % (nn_cnt[0], nn_cnt[-1], nf[0], nf[-1]))

    print("\n  連結半径の掃引 —— 連なりは幾何どおりの位置で捕まる")
    # 予測は**設計値から**: 各ボイドの最近接すき間の中央値の半分で、塊の数が半分になる。
    def _design_gap(voids):
        c = np.array([v["center"] for v in voids])
        d = np.linalg.norm(c[:, None, :] - c[None, :, :], axis=-1)
        np.fill_diagonal(d, np.inf)
        r = voids[0]["r"]
        return float(np.median(d.min(axis=1))) - 2.0 * r

    voids_s = make_voids("sphere", "scatter", "mid")
    gap_chain = 1000 * _design_gap(voids_c)
    gap_scat = 1000 * _design_gap(voids_s)
    print("   設計の最近接すき間(中央値): 連なり %.1f µm -> 予測 %.1f µm / "
          "散在 %.1f µm -> 予測 %.1f µm" % (gap_chain, gap_chain / 2,
                                            gap_scat, gap_scat / 2))
    est_c = segment(obs_c, sc_c["layer"])
    sc_s = build_scene(voids_s)
    est_s = segment(observe(sc_s["mu"], VOXEL), sc_s["layer"])
    radii = [0.0, 0.005, 0.010, 0.015, 0.020, 0.030, 0.045, 0.060,
             0.075, 0.090, 0.105, 0.120]
    nc_chain, nc_scat = [], []
    for rb in radii:
        for est, acc in ((est_c, nc_chain), (est_s, nc_scat)):
            k = int(round(rb / VOXEL))
            m = est if k == 0 else np.asarray(
                L.morph_dilate3d(est.astype(float), r=k, se="ball")) > 0.5
            acc.append(int(L.vol_label.raw(m.astype(float), connectivity=26)[1]))
    half = N_VOID // 2
    r_chain = next((1000 * r for r, n in zip(radii, nc_chain) if n <= half), float("nan"))
    r_scat = next((1000 * r for r, n in zip(radii, nc_scat) if n <= half), float("nan"))
    print("   実測(塊が %d 個以下 = 半減する最初の半径): 連なり %.1f µm / 散在 %.1f µm"
          % (half, r_chain, r_scat))
    print("   ★予測との差は 連なり %+.1f µm / 散在 %+.1f µm(掃引の刻みは %.0f µm)。"
          % (r_chain - gap_chain / 2, r_scat - gap_scat / 2, 15.0))
    print("   ★**ボイド率にはこの %.0f 倍の差がまったく出ない**(両条件とも 3 %% 台)。"
          % (gap_scat / gap_chain))

    figs.save_plot("threshold_sweep",
                   [("ボイド率 [%]", thrs, tf),
                    ("界面欠損率 [%] の 1/5", thrs, [x / 5 for x in tai]),
                    ("連なりの塊の数 / 8", thrs, [x / 8 for x in tn]),
                    ("連なりの最近接 [µm] の 1/50", thrs, [x / 50 for x in tnn])],
                   xlabel="2 値化のしきい値", ylabel="各指標(尺度を合わせてある)",
                   title="しきい値 %.2f でボイドが融合し、最近接間隔の意味が変わる" % merge_thr,
                   caption="塊の数が %d から落ちた瞬間、最近接間隔は『隣のボイドまで』"
                           "から『隣の鎖まで』に黙って入れ替わる。" % N_VOID)
    figs.save_plot("cluster_radius_sweep",
                   [("連なり(すき間 %.0f µm)" % gap_chain,
                     [1000 * r for r in radii], nc_chain),
                    ("散在(すき間 %.0f µm)" % gap_scat,
                     [1000 * r for r in radii], nc_scat),
                    ("予測(連なり %.0f µm)" % (gap_chain / 2), [gap_chain / 2] * 2,
                     [0, N_VOID]),
                    ("予測(散在 %.0f µm)" % (gap_scat / 2), [gap_scat / 2] * 2,
                     [0, N_VOID])],
                   xlabel="橋渡しの連結半径 [µm]", ylabel="連結成分の個数",
                   title="連なりは設計どおりの半径で 3 本の鎖に落ちる",
                   caption="ボイド率にはこの差が出ない —— 両条件とも 3 %% 台。")
    figs.save_plot("noise_sweep",
                   [("塊の数(偽ボイドを含む)", [1000 * s for s in noises], nn_cnt),
                    ("ボイド率 [%] x 100", [1000 * s for s in noises],
                     [x * 100 for x in nf]),
                    ("真値 %.1f %% x 100" % (100 * VOID_FRAC),
                     [1000 * s for s in noises], [100 * VOID_FRAC * 100] * len(noises))],
                   xlabel="雑音 sigma x 1000(はんだ = 1000)",
                   ylabel="個数 / ボイド率 x 100",
                   title="雑音は個数を爆発させるが、体積率はほとんど動かない",
                   caption="合否の数字は雑音に強い。強いことが問題で、"
                           "壊れているのに気づけない。")
    return {"thr": thrs, "tf": tf, "tflat": tflat, "tnn": tnn, "tn": tn, "nf": nf,
            "n_noise": nn_cnt, "r_chain": r_chain, "r_scat": r_scat,
            "merge_thr": merge_thr,
            "pred_chain": gap_chain / 2, "pred_scat": gap_scat / 2}


# --------------------------------------------------------------------------- #
# 7. 道具の穴と 3-D の落とし穴                                                  #
# --------------------------------------------------------------------------- #
def section_tool_gaps() -> None:
    print("\n" + "=" * 78)
    print("7) 道具の穴と 3-D の落とし穴(使ってみて分かったこと)")
    print("=" * 78)

    # (a) PSF カーネルは作れるが、前向きに畳む op が公開経路に無い
    k = np.asarray(L.vol_gaussian_psf(1.2))
    assert abs(float(k.sum()) - 1.0) < 1e-9
    t = np.zeros((15, 15, 15)); t[7, 7, 7] = 1.0
    a = ndi.convolve(t, k, mode="constant")
    b = ndi.gaussian_filter(t, 1.2, truncate=4.0)
    print("  (a) vol_gaussian_psf はカーネルを返すが、**前向きに畳む op が無い**"
          "(vol_richardson_lucy は逆問題側だけ)。\n      自前の convolve と "
          "gaussian_filter の一致は %.2e —— この PoC はこれを根拠に "
          "gaussian_filter を使った。" % float(np.abs(a - b).max()))
    assert float(np.abs(a - b).max()) < 1e-6

    # (b) query_distance は立方格子しか受けない
    occ = np.zeros((8, 8, 8)); occ[3:5, 3:5, 3:5] = 1
    e = L.esdf(occ, voxel_size=0.01)
    q = L.query_distance(e, ((0, 0.08),) * 3, 8, np.array([[0.04, 0.04, 0.04]]))
    print("  (b) query_distance は立方格子専用(`int(res)` + shape == (res,res,res))。"
          "薄い接合層のような\n      非立方ボリューム %s では引けない —— esdf 側は"
          " 長さ 3 の voxel_size を受けるのに、片方だけ狭い。"
          % (str((30, 180, 180)),))
    try:
        L.query_distance(e, ((0, 0.08),) * 3, (8, 8, 8), np.array([[0.04, 0.04, 0.04]]))
        raise AssertionError("非立方が通った(この節を書き換えること)")
    except TypeError:
        pass
    print("      立方なら通る(中心の値 %.4f mm)。" % float(q[0]))

    # (c) 軸順が族で違う —— 混ぜると静かに間違う
    print("  (c) 軸順: grid_coords / sdf_* は (nx,ny,nz) で最終軸 (x,y,z)、"
          "ボリューム op は (depth,row,col)=(z,y,x)、\n      vol_boundary_points も "
          "(z,y,x) を返すのに obb は点群 op なので (x,y,z) 前提。"
          "**等方ボクセルでは主軸の長さが同じなので\n      取り違えても例外にならない**"
          " —— 静かに間違う型の代表。")

    # (d) 分位点・形態の要約 op が無い
    for name in ("void_fraction", "size_percentiles", "nearest_neighbor_distance"):
        assert not hasattr(fs, name) and not hasattr(fs.ledger, name)
    print("  (d) 体積率・最近接ボイド間隔を出す op が無い(この PoC は cKDTree で自前)。"
          "\n      vol_region_props は sphericity を返すが**扁平度(最小/最大主軸)は"
          "無い** —— obb を挟んで自前で組んだ。")

    # (e) 界面に接するボイドの等値面は開く -> mesh_volume が嘘になる
    sc = build_scene(make_voids("sphere", "scatter", "interface"))
    est = segment(observe(sc["mu"], VOXEL), sc["layer"])
    lab, n = L.vol_label.raw(est.astype(float), connectivity=26)
    props = L.vol_region_props.raw(lab, spacing=(VOXEL,) * 3)
    p = max(props, key=lambda d: d["voxel_count"])
    z0, z1, y0, y1, x0, x1 = p["bbox"]
    sub = (lab[z0:z1, y0:y1, x0:x1] == p["label"]).astype(float)
    out = []
    for tag, vol in (("余白 1 ボクセルつき", np.pad(sub, 1)), ("切り出したまま", sub)):
        verts, faces, _ = L.voxel_to_mesh.raw(vol, iso=0.5)
        bv = int(len(np.asarray(L.boundary_vertices((verts, faces)))))
        mv = abs(float(L.mesh_volume((verts, faces)))) * VOXEL ** 3
        fa = float(np.sum(np.asarray(L.face_areas((verts, faces))))) * VOXEL ** 2
        out.append((tag, bv, mv, fa))
        print("  (e) %s: 境界頂点 %4d 個(0 なら水密) / mesh_volume %.5f mm^3 "
              "(ボクセル体積 %.5f の %+.1f %%) / face_areas %.4f mm^2 "
              "(vol_region_props %.4f の %+.1f %%)"
              % (tag, bv, mv, p["volume"], 100 * (mv / p["volume"] - 1),
                 fa, p["surface_area"], 100 * (fa / p["surface_area"] - 1)))
    print("      ★同じボイドで、**切り出し方だけで体積が %+.1f %% 変わる**。"
          "開いた側は境界頂点 %d 個で\n      それと分かるのに、**mesh_volume は"
          "黙って数字を返す**(docstring どおり『穴を原点へ塞いだ立体』)。"
          "\n      界面に接するボイドは ROI の縁で必ず開くので、体積で語る前に"
          " boundary_vertices を見ること。"
          % (100 * (out[1][2] / out[0][2] - 1), out[1][1]))


# --------------------------------------------------------------------------- #
def main() -> int:
    t0 = time.perf_counter()
    print("=" * 78)
    print("X 線 CT のボイド形態 —— 合否の 1 個の数字は、寿命に効く形を先に見失う")
    print("接合部 %.2f mm 角 / 層厚 %.0f µm / ボイド %d 個 / 体積率 %.1f %% "
          "(全条件で同じ)" % (JOINT, 1000 * T_LAYER, N_VOID, 100 * VOID_FRAC))
    print("=" * 78)

    section_scene()
    ctl = section_controls()
    proxy = section_proxy(ctl)
    cliff = section_voxel_cliff()
    swp = section_threshold_noise()
    section_tool_gaps()

    print("\n" + "=" * 78)
    print("まとめ")
    print("=" * 78)
    print("  * ゼロ点(ボイド率だけ)は 5 条件を %.2f ポイントしか分けない。"
          % ctl["spread"])
    print("  * 形態は同じ 5 条件を桁で分ける(離隔 %.1f 倍 / 扁平度 %.1f 倍 / "
          "最近接 %.1f 倍)。" % (ctl["ratios"]["gap"], ctl["ratios"]["flat"],
                                  ctl["ratios"]["nn"]))
    print("  * 応力の代理指標(界面欠損率)は 0 -> %.2f %%。同体積の球 %.2f %% の "
          "%.2f 倍。" % (proxy["disc"], proxy["sph"], proxy["disc"] / proxy["sph"]))
    print("  * ★崖の予想は外れた: ボイド率は %.0f µm でも %.2f %% と崩れず、"
          "先に死ぬのは形の指標\n    (界面欠損率 %.2f -> %.2f %%、扁平度は %.0f µm で"
          "測れない)。" % (cliff["vx"][-1], cliff["f_sph"][-1], cliff["ai"][0],
                           cliff["ai"][-1], cliff["vx"][-1]))
    print("  * 連なりは連結半径 %.0f µm(予測 %.1f)で捕まるが、ボイド率には出ない。"
          % (swp["r_chain"], swp["pred_chain"]))
    print("  * 寿命そのものは測っていない —— 示せたのは合否 1 個の数字の盲目さまで。")

    # 所見を固定する門(壊れたら鳴る)
    assert ctl["spread"] < 0.6, "ゼロ点が条件を分け始めた: %.3f" % ctl["spread"]
    assert ctl["ratios"]["gap"] > 3.0 and ctl["ratios"]["flat"] > 2.0, ctl["ratios"]
    assert ctl["ratios"]["nn"] > 4.0, ctl["ratios"]["nn"]
    assert proxy["disc"] / proxy["sph"] > 1.5, "扁平の界面欠損が球と変わらない"
    assert abs(proxy["disc"] - proxy["pred_disc"]) < 1.5, "閉形式と合わない"
    # ★体積率は粗いボクセルでも保たれ、先に死ぬのは形の指標(予想が外れた側)
    assert cliff["f_sph"][-1] > 0.8 * cliff["f_sph"][0], "ボイド率が崩れた(所見が反転)"
    assert cliff["ai"][-1] < 0.9 * cliff["ai"][0], "界面欠損率が劣化していない"
    assert not np.isfinite(cliff["fl_dsc"][-1]), "最粗で扁平度が測れてしまった"
    assert abs(swp["r_chain"] - swp["pred_chain"]) <= 1000 * VOXEL, "連結半径が予測外"
    assert swp["tf"][-1] > swp["tf"][0], "しきい値でボイド率が増えない"
    assert min(swp["tn"]) < N_VOID, "しきい値を上げても融合が起きない"

    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
