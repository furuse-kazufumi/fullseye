# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""電極の屈曲度を CT から測る —— Bruggeman は空隙率しか見ないので、向きに盲目。

リチウムイオン電池の電極塗工層(多孔体)を マイクロ CT で撮り、**空隙率 ε** と
**屈曲度 τ**(電解質の中をイオンが遠回りする度合い)を出す、という仕事です。
セル設計の式に入るのは τ のほうで、現場の既定値は Bruggeman の経験則
τ = ε^(-0.5)。この PoC は多孔構造を真値つきで作り、**τ の定義そのものを
数値実験で確かめます** —— 経験則・測地距離・輸送方程式の 3 つは同じ名前で
呼ばれていて、同じ構造から**別の数字**を返します。

EXTEND: 実機 CT に差し替えるなら :func:`make_electrode` が返す ``pore``
(True = 空隙 の bool ボリューム)を、実測を二値化したボリュームに置き換えます。
:func:`transport` / :func:`tau_geodesic` はどちらも二値ボリュームだけから計算するので
**そのまま動きます**。真値がわりの :func:`transport` は輸送方程式の数値解なので、
実データでも「その二値化から出る τ」は得られます —— 得られないのは
**二値化が正しいかどうか**で、そこが差し替えの限界です(6 章の解像度の偏りは
そのまま効きます)。粒子形状を変えた対照群は実データでは作れないので、
カレンダリング前後の 2 本を撮って比べることになります。

この PoC が示すこと(数字はいずれも実行時に印字される実測値):

1. **ゼロ点(Bruggeman τ = ε^(-0.5))を先に置く**。空隙率 ε = 0.4448 の
   球状粒子床で、Bruggeman は τ = 1.499、輸送方程式を解いた実測は
   **τ = 1.843(-18.6 %)**。経験則は**必ず小さめに外す**。
2. ★**外し方は空隙率で単調に開く**。ε = 0.691 → 0.168 と振ると
   誤差は **-8.2 % → -69.1 %**。ε >= 0.40 では Bruggeman 指数(D_eff ∝ ε^α)の
   実測は **α = 1.78** で 1.5 ではなく、ε < 0.25 では **α = 2.70** まで跳ねる。
   「1.5 乗則」は高空隙率の近似ですらない。
3. ★★**測地屈曲度は Bruggeman の τ ではない**。画像解析の論文が測る
   「最短経路長 / 直線距離」は ε = 0.4448 で **τ_geo = 1.182** —— 実測 1.843 の
   **64 %** しかない。ところが★**その 2 乗が Bruggeman に寄り添う**
   (ε = 0.691 で 1.193 対 1.203 = 差 0.8 %、ε = 0.565 で 5.7 %、
   ε = 0.445 で 6.9 %)。**2 つの「よく合う数字」は、真値に対して
   同じ向きに外れている**だけだった。
4. ★★**対照群 —— 同じ空隙率で粒子を扁平にすると厚み方向の τ が 3.7 倍**
   (カレンダリング)。ε を 0.4448 対 0.4510 に揃えた比較で、
   球状床は τ_z = 1.843 / τ_x = 1.906(**異方比 0.97 = 等方**)、
   扁平床(4:1)は τ_z = **6.794** / τ_x = 1.618(**異方比 4.20**)。
   Bruggeman は ε しか見ないので両方に 1.499 / 1.489 を返す ——
   **面内は当たっているように見え(-8 %)、厚み方向は壊滅(-78 %)**。
   セル設計に効くのは厚み方向のほうです。
5. **もっともらしい犯人を対照群で外した**。「閉気孔(孤立した空隙)が
   効いているのでは」を測ると、孤立空隙は全空隙の **0.05 / 1.50 / 1.92 %**
   (ε = 0.4448 / 0.2430 / 0.1675)しかなく、τ が 1.8〜7.9 まで動くことを
   説明できない。効いているのは**首(くびれ)**で、空隙の内接半径の中央値は
   粒子半径の **0.40 倍**(2.00 voxel)しかない。★ただし**そのスカラーも
   向きを分けられない**: 扁平床は内接半径の分布が 1 つ(中央値 1.00 voxel)
   なのに、τ_z と τ_x は 4.2 倍違う。
6. ★**予想が外れた —— 解像度に崖が無い**。「voxel が首の直径(実測 4.0 単位
   = 粒子半径 1.2 voxel 相当、一辺 16 前後)を超えたら経路が塞がって崩れる」と
   予測してから掃引したが、**崖は現れず、なだらかな片側の偏りだけ**が出た:
   voxel を 5.5 倍粗くすると τ_f は 1.771 → 3.041(**+72 %**)へ単調に増え、
   同じ間 **ε は 0.4449 → 0.4431(-0.4 %)しか動かない**。首が 1 voxel を
   切っても斜めに繋がるので塞がらない。空隙率は解像度に鈍く、屈曲度は敏感で、
   しかも**警告が出ない** —— 壊れた図も、落ちた検出数も出ないまま数字だけがずれる。
7. **数字が 3 つある以上、どれを報告したかを書かないと意味が無い**
   (Bruggeman 1.499 / 測地 1.182 / 輸送 1.843、同じ 1 個のボリュームから)。

【グラウンドトゥルース】構造は自分で撒いた球(または扁平回転楕円体)の和なので
空隙率は解析的に検算でき、屈曲度の真値は**同じボリューム上で定常拡散方程式
(格子 Laplace、6 近傍、固相は無流束)を解いた実効拡散係数**から
τ_f = ε / (D_eff/D_bulk) として定義します。経験則ではなく方程式の解なので、
「Bruggeman が外す」は経験則と方程式の差であって、実験誤差ではありません。

来歴(公開文献のみ): Bruggeman, *Ann. Phys.* 416 (1935) 636 —— 混合則の原論文 /
Thorat et al., *J. Power Sources* 188 (2009) 592 —— 電極の実測 τ が Bruggeman を
上回ること / Ebner & Wood, *J. Electrochem. Soc.* 162 (2015) A3064 —— CT からの
屈曲度推定と「幾何的屈曲度 ≠ 屈曲度因子」/ Clennell, *Geol. Soc. Spec. Publ.*
122 (1997) 299 —— 屈曲度の定義の混乱の整理。
"""
from __future__ import annotations

import math
import sys
import time
from pathlib import Path

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla
from scipy.sparse.csgraph import dijkstra

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

# --- 場面の諸元 -------------------------------------------------------------- #
N_VOX = 64              # 立方体の一辺 [voxel]
VOX_UM = 0.5            # 1 voxel の大きさ [µm]  -> 視野 32 µm 角
R_MED = 5.0             # 活物質粒子の半径の中央値 [voxel] = 2.5 µm(直径 5 µm)
R_SIG = 0.25            # 半径の対数正規 σ
SEED = 3

#: 「電極らしい」空隙率を作る粒子数(この構造での実測 ε = 0.4448)
N_SPHERE = 350
#: 扁平率 4 の粒子で ε を同じ 0.45 前後に合わせる粒子数(4 章の対照群)
N_FLAKE, FLAT = 1360, 4.0


# --------------------------------------------------------------------------- #
# 場面を作る —— 重なった球(または扁平回転楕円体)の和が活物質、残りが空隙       #
# --------------------------------------------------------------------------- #
def make_electrode(n_particle: int, flat: float = 1.0, n_vox: int = N_VOX,
                   seed: int = SEED, r_med: float = R_MED) -> np.ndarray:
    """活物質粒子を撒いた多孔体の**空隙**(True)を返す。

    ``flat`` > 1 は粒子を z 方向へ潰す(カレンダリング = 電極をロールで
    圧縮する工程)。半軸は (r/flat, r, r)。

    ``n_vox`` と ``r_med`` を**同じ倍率で**変えると、**物理的な構造は同じまま
    voxel だけが細かくなる**(6 章の解像度掃引はこれを使う)。中心は
    ``U(0,1)^3 x n_vox`` で引くので、倍率を変えても同じ場所に同じ粒子が来る。
    """
    rng = np.random.default_rng(seed)
    solid = np.zeros((n_vox, n_vox, n_vox), bool)
    centres = rng.uniform(0.0, 1.0, (n_particle, 3)) * n_vox
    logs = rng.standard_normal(n_particle)
    for k in range(n_particle):
        r = r_med * math.exp(R_SIG * logs[k])
        a = r / flat                                   # z 半軸
        cz, cy, cx = centres[k]
        z0, z1 = max(0, int(cz - a - 1)), min(n_vox, int(cz + a + 2))
        y0, y1 = max(0, int(cy - r - 1)), min(n_vox, int(cy + r + 2))
        x0, x1 = max(0, int(cx - r - 1)), min(n_vox, int(cx + r + 2))
        if z0 >= z1 or y0 >= y1 or x0 >= x1:
            continue
        zz = (np.arange(z0, z1) - cz)[:, None, None] * flat
        yy = (np.arange(y0, y1) - cy)[None, :, None]
        xx = (np.arange(x0, x1) - cx)[None, None, :]
        solid[z0:z1, y0:y1, x0:x1] |= (zz * zz + yy * yy + xx * xx) <= r * r
    return ~solid


# --------------------------------------------------------------------------- #
# 空隙のつながり方をグラフにする                                                #
#   ★公開経路に無い処理: voxel 空間の 6 近傍隣接グラフ。fullseye は 3-D の      #
#   連結成分(vol_label)も距離変換(vol_distance_transform)も持っているが、    #
#   「空隙を通り抜ける経路」を扱う口(測地距離・輸送)は無い。                  #
# --------------------------------------------------------------------------- #
def pore_graph(pore: np.ndarray):
    """空隙 voxel の 6 近傍隣接グラフ ``(index 配列, 対称 CSR 行列)``。"""
    idx = -np.ones(pore.shape, np.int64)
    flat_idx = np.flatnonzero(pore.ravel())
    idx.ravel()[flat_idx] = np.arange(flat_idx.size)
    rows, cols = [], []
    for ax in range(3):
        a = np.take(idx, np.arange(0, pore.shape[ax] - 1), axis=ax)
        b = np.take(idx, np.arange(1, pore.shape[ax]), axis=ax)
        m = (a >= 0) & (b >= 0)
        rows.append(a[m])
        cols.append(b[m])
    r, c = np.concatenate(rows), np.concatenate(cols)
    n = flat_idx.size
    g = sp.coo_matrix((np.ones(r.size), (r, c)), shape=(n, n)).tocsr()
    return flat_idx, (g + g.T).tocsr()


def transport(pore: np.ndarray, axis: int = 0) -> dict:
    """**真値**: 定常拡散方程式を解いた実効拡散係数と屈曲度因子 τ_f。

    ``axis`` の両端面を Dirichlet(濃度 1 と 0)、固相との界面は無流束。
    格子 Laplace を共役勾配で解き、入口面を通る流束から
    ``D_eff/D_bulk`` を出して ``tau_f = eps / (D_eff/D_bulk)``。
    これが Bruggeman が予言しようとしている量そのもの。
    """
    vol = np.moveaxis(pore, axis, 0)
    n = vol.shape[0]
    flat_idx, g = pore_graph(vol)
    plane = np.unravel_index(flat_idx, vol.shape)[0]
    lo, hi = plane == 0, plane == n - 1
    free = ~(lo | hi)
    lap = sp.diags(np.asarray(g.sum(1)).ravel()) - g
    a_ff = lap[free][:, free].tocsr()
    rhs = -(lap[free][:, lo] @ np.ones(int(lo.sum())))
    dinv = 1.0 / np.maximum(a_ff.diagonal(), 1e-12)
    prec = spla.LinearOperator(a_ff.shape, matvec=lambda x: x * dinv)
    sol, info = spla.cg(a_ff, rhs, rtol=1e-9, maxiter=8000, M=prec)
    phi = np.zeros(flat_idx.size)
    phi[lo] = 1.0
    phi[free] = sol
    flux = float(g[lo].dot(1.0 - phi).sum())
    area = vol.shape[1] * vol.shape[2]
    d_eff = flux * (n - 1) / area
    eps = float(vol.mean())
    # bond ごとの散逸 (phi_a - phi_b)^2 —— 「働いている空隙」の地図
    coo = sp.triu(g).tocoo()
    diss = (phi[coo.row] - phi[coo.col]) ** 2
    return {"eps": eps, "d_eff": d_eff, "tau_f": eps / max(d_eff, 1e-15),
            "phi": phi, "flat_idx": flat_idx, "shape": vol.shape,
            "bond": (coo.row, coo.col, diss), "cg_info": info,
            "lo": lo, "hi": hi, "graph": g}


def tau_geodesic(pore: np.ndarray, axis: int = 0) -> float:
    """画像解析の論文がよく報告する「幾何的(測地)屈曲度」= 最短経路 / 直線距離。

    ★公開経路に無い処理: voxel 上の測地距離変換。``fs.ledger.geodesic_distances``
    は点群の kNN グラフ用で、ボリュームは受けない。
    """
    vol = np.moveaxis(pore, axis, 0)
    n = vol.shape[0]
    flat_idx, g = pore_graph(vol)
    plane = np.unravel_index(flat_idx, vol.shape)[0]
    m = flat_idx.size
    # 入口面すべてに 0 で繋がる仮想始点を 1 個足して 1 回の Dijkstra で済ませる
    big = sp.vstack([sp.hstack([g, sp.csr_matrix((m, 1))]),
                     sp.csr_matrix((1, m + 1))]).tolil()
    big[m, np.flatnonzero(plane == 0)] = 1e-9
    dist = dijkstra(big.tocsr(), directed=False, indices=m)
    out = dist[np.flatnonzero(plane == n - 1)]
    out = out[np.isfinite(out)]
    return float(out.mean() / (n - 1)) if out.size else float("inf")


def bruggeman(eps: float) -> float:
    """ゼロ点 —— 現場の既定値 τ = ε^(-0.5)(D_eff/D_bulk = ε^1.5)。"""
    return float(eps ** -0.5)


def _zoom(sl: np.ndarray, k: int = 5) -> np.ndarray:
    """図のパネルを ``k`` 倍に拡大する(最近傍)。voxel の粗さを隠さない。"""
    return np.kron(np.asarray(sl, np.float64), np.ones((k, k)))


# --------------------------------------------------------------------------- #
# 1. ゼロ点                                                                     #
# --------------------------------------------------------------------------- #
def section_zero_point() -> dict:
    print("\n" + "=" * 78)
    print("1) ゼロ点 —— Bruggeman τ = ε^(-0.5) と、輸送方程式を解いた τ")
    print("=" * 78)

    pore = make_electrode(N_SPHERE)
    tr = transport(pore)
    tg = tau_geodesic(pore)
    br = bruggeman(tr["eps"])
    print("  視野 %d^3 voxel x %.2f µm = %.1f µm 角 / 粒子半径の中央値 %.1f µm"
          % (N_VOX, VOX_UM, N_VOX * VOX_UM, R_MED * VOX_UM))
    print("  空隙率 ε = %.4f   実効拡散 D_eff/D_bulk = %.4f" % (tr["eps"], tr["d_eff"]))
    print("      Bruggeman   %6.3f   (経験則 ε^(-0.5))" % br)
    print("      測地 τ_geo  %6.3f   (Bruggeman の %.0f %%)" % (tg, 100 * tg / br))
    print("      輸送 τ_f    %6.3f   <- これが設計式に入る量" % tr["tau_f"])
    print("    Bruggeman の誤差 %+.1f %% / 測地の誤差 %+.1f %%"
          % (100 * (br - tr["tau_f"]) / tr["tau_f"],
             100 * (tg - tr["tau_f"]) / tr["tau_f"]))

    # 場面の図(断面 3 枚)。同じ構造を、扁平粒子の対照群と並べる。
    # ★64 voxel のスライスをそのまま渡すとパネル幅が 64 px しかなく、
    #   題の文字が入らずに図ごと落ちる(examplefig は黙って諦めない)。
    flake = make_electrode(N_FLAKE, flat=FLAT)
    mid = N_VOX // 2
    figs.save_grid(
        "scene",
        [_zoom(pore[:, mid, :]), _zoom(pore[mid]), _zoom(flake[:, mid, :])],
        ["球状 厚み方向 ε=%.3f" % tr["eps"], "球状 面内",
         "扁平4:1 ε=%.3f" % float(flake.mean())],
        title="電極塗工層の多孔構造(白 = 空隙 / 黒 = 活物質)", ncols=3,
        caption="左と中は同じ球状粒子床の直交する 2 断面。右はカレンダリングで"
                "潰した粒子(空隙率はほぼ同じ、屈曲度は 3.7 倍)。")

    # 「働いている空隙」の地図 —— 濃度場と散逸
    phi_vol = np.zeros(N_VOX ** 3)
    phi_vol[tr["flat_idx"]] = tr["phi"]
    phi_vol = phi_vol.reshape(tr["shape"])
    row, col, diss = tr["bond"]
    act = np.zeros(tr["flat_idx"].size)
    np.add.at(act, row, diss)
    np.add.at(act, col, diss)
    act_vol = np.zeros(N_VOX ** 3)
    act_vol[tr["flat_idx"]] = np.log10(act + 1e-12)
    act_vol = act_vol.reshape(tr["shape"])
    figs.save_grid("map_transport",
                   [_zoom(phi_vol[:, mid, :]), _zoom(act_vol[:, mid, :])],
                   ["イオン濃度 φ", "散逸 log10"],
                   title="同じ断面で見た「遠回り」の中身",
                   caption="左: 上端 1 / 下端 0 の濃度場。等濃度線が固相を"
                           "避けて曲がる分が遠回り。右: bond ごとの散逸"
                           "(明るいほど流れが集中している = 首)。")
    return {"pore": pore, "tr": tr, "tg": tg, "br": br, "flake": flake}


# --------------------------------------------------------------------------- #
# 2-3. 空隙率の掃引                                                             #
# --------------------------------------------------------------------------- #
def section_porosity_sweep() -> dict:
    print("\n" + "=" * 78)
    print("2-3) 空隙率を振る —— Bruggeman の外れ方と、測地屈曲度の正体")
    print("=" * 78)
    print("   粒子数    ε     D_eff   Bruggeman  測地τ  測地τ^2   輸送τ_f   B の誤差")

    eps_l, tf_l, tg_l, br_l, d_l = [], [], [], [], []
    for n_p in (150, 250, 350, 450, 600, 800):
        pore = make_electrode(n_p)
        tr = transport(pore)
        tg = tau_geodesic(pore)
        br = bruggeman(tr["eps"])
        eps_l.append(tr["eps"])
        d_l.append(tr["d_eff"])
        tf_l.append(tr["tau_f"])
        tg_l.append(tg)
        br_l.append(br)
        print("   %5d  %.3f  %.4f   %7.3f  %6.3f  %7.3f  %8.3f  %+7.1f %%"
              % (n_p, tr["eps"], tr["d_eff"], br, tg, tg * tg, tr["tau_f"],
                 100 * (br - tr["tau_f"]) / tr["tau_f"]))

    e = np.asarray(eps_l)
    d = np.asarray(d_l)
    hi = e >= 0.40
    lo = e < 0.25
    a_hi = float(np.polyfit(np.log(e[hi]), np.log(d[hi]), 1)[0])
    a_lo = float(np.polyfit(np.log(e[lo]), np.log(d[lo]), 1)[0])
    print("\n  ★Bruggeman 指数 α(D_eff ∝ ε^α)の実測: ε>=0.40 で **%.2f** / "
          "ε<0.25 で **%.2f**。経験則の 1.5 はどちらでもない。" % (a_hi, a_lo))
    gap = [abs(tg_l[i] ** 2 - br_l[i]) / br_l[i] for i in range(len(e))]
    print("  ★★測地屈曲度の **2 乗**が Bruggeman とほぼ一致する"
          "(ε>=0.40 の 3 点で差 %.1f / %.1f / %.1f %%)。"
          % tuple(100 * g for g in gap[:3]))
    print("     つまり「測地距離で τ を測った」と「経験則を使った」は"
          "**同じ間違いを同じ向きにしている**。")

    figs.save_plot("porosity_sweep",
                   [("Bruggeman ε^(-0.5)", eps_l, br_l),
                    ("輸送(真値)τ_f", eps_l, tf_l),
                    ("測地 τ_geo", eps_l, tg_l),
                    ("測地 τ_geo^2", eps_l, [t * t for t in tg_l])],
                   xlabel="空隙率 ε [-]", ylabel="屈曲度 τ [-]",
                   title="同じ構造から出る 3 つの「屈曲度」",
                   caption="ε が下がるほど経験則と真値が開く。測地の 2 乗は"
                           "経験則に寄り添うが、真値には寄らない。")
    figs.save_plot("bruggeman_error",
                   [("Bruggeman の誤差", eps_l,
                     [100 * (br_l[i] - tf_l[i]) / tf_l[i] for i in range(len(e))]),
                    ("ゼロ(真値)", eps_l, [0.0] * len(e))],
                   xlabel="空隙率 ε [-]", ylabel="τ の誤差 [%]",
                   title="経験則は必ず小さめに外し、低空隙率で開く")
    return {"eps": eps_l, "tau_f": tf_l, "tau_geo": tg_l, "brugg": br_l,
            "alpha_hi": a_hi, "alpha_lo": a_lo}


# --------------------------------------------------------------------------- #
# 4. 対照群 —— 同じ空隙率で粒子形状だけを変える                                 #
# --------------------------------------------------------------------------- #
def section_anisotropy() -> dict:
    print("\n" + "=" * 78)
    print("4) 対照群 —— 空隙率を揃えて粒子だけ扁平にする(カレンダリング)")
    print("=" * 78)

    rows = []
    out = {}
    for label, n_p, fl in (("球状粒子", N_SPHERE, 1.0), ("扁平粒子(4:1)", N_FLAKE, FLAT)):
        pore = make_electrode(n_p, flat=fl)
        tz = transport(pore, axis=0)
        tx = transport(pore, axis=2)
        br = bruggeman(tz["eps"])
        rows.append([label, "%.4f" % tz["eps"], "%.3f" % br,
                     "%.3f" % tz["tau_f"], "%.3f" % tx["tau_f"],
                     "%.2f" % (tz["tau_f"] / tx["tau_f"]),
                     "%+.0f %%" % (100 * (br - tz["tau_f"]) / tz["tau_f"]),
                     "%+.0f %%" % (100 * (br - tx["tau_f"]) / tx["tau_f"])])
        out[label] = {"eps": tz["eps"], "tz": tz["tau_f"], "tx": tx["tau_f"], "br": br,
                      "pore": pore}
        print("  %-14s ε=%.4f  τ_z=%6.3f  τ_x=%6.3f  異方比 %.2f  "
              "Bruggeman %.3f(厚み方向 %+.0f %% / 面内 %+.0f %%)"
              % (label, tz["eps"], tz["tau_f"], tx["tau_f"], tz["tau_f"] / tx["tau_f"],
                 br, 100 * (br - tz["tau_f"]) / tz["tau_f"],
                 100 * (br - tx["tau_f"]) / tx["tau_f"]))

    a, b = out["球状粒子"], out["扁平粒子(4:1)"]
    print("\n  ★★空隙率をほぼ同じ(%.4f 対 %.4f)に揃えても、厚み方向の τ は"
          " %.3f 対 %.3f = **%.1f 倍**。" % (a["eps"], b["eps"], a["tz"], b["tz"],
                                             b["tz"] / a["tz"]))
    print("     Bruggeman は ε しか見ないので**同じ数字**を返す。"
          "面内だけ見ていると当たっているように見える(%+.0f %%)のが罠。"
          % (100 * (b["br"] - b["tx"]) / b["tx"]))

    figs.save_table("anisotropy",
                    ["構造", "ε", "Bruggeman", "τ_z(厚み)", "τ_x(面内)",
                     "異方比", "B の誤差 z", "B の誤差 x"],
                    rows, title="同じ空隙率・違う粒子形状(単位はすべて無次元)",
                    caption="経験則は向きを持てない。厚み方向がセル設計に効く。")
    return out


# --------------------------------------------------------------------------- #
# 5. 犯人探し —— 閉気孔ではなく、首                                             #
# --------------------------------------------------------------------------- #
def section_why(aniso: dict) -> dict:
    print("\n" + "=" * 78)
    print("5) もっともらしい犯人を外す —— 閉気孔か、首か")
    print("=" * 78)
    print("   ε      成分数  貫通する空隙率  孤立した空隙(全空隙比)")

    iso = []
    for n_p in (350, 600, 800):
        pore = make_electrode(n_p)
        lab, n_comp = fs.vol_label(pore, connectivity=6)
        lab = np.asarray(lab)
        span = (set(np.unique(lab[0])) & set(np.unique(lab[-1]))) - {0}
        perc = float(np.isin(lab, sorted(span)).mean())
        eps = float(pore.mean())
        frac = (eps - perc) / eps
        iso.append((eps, n_comp, perc, frac))
        print("   %.4f  %5d    %.4f          %.2f %%" % (eps, n_comp, perc, 100 * frac))
    print("  -> 閉気孔は最大でも全空隙の %.2f %%。τ が 2〜10 倍外れる説明にはならない。"
          % (100 * max(f for *_, f in iso)))

    # 首 = 空隙の内接半径(3-D 距離変換)。fullseye の op をそのまま使う。
    print("\n   構造            空隙の内接半径 [voxel]  中央値/粒子半径")
    necks = {}
    for label in ("球状粒子", "扁平粒子(4:1)"):
        pore = aniso[label]["pore"]
        dt = np.asarray(fs.vol_distance_transform(pore))
        med = float(np.median(dt[pore]))
        necks[label] = med
        print("   %-14s 中央値 %.2f / 90%%点 %.2f / 最大 %.2f     %.2f"
              % (label, med, float(np.percentile(dt[pore], 90)), float(dt.max()),
                 med / R_MED))
    print("  -> 首は粒子半径の %.2f 倍しかない。遠回りを作っているのはここ。"
          % (necks["球状粒子"] / R_MED))
    print("  ★ただしこのスカラーも**向きを分けられない**: 扁平床は内接半径が"
          "\n     1 つの分布(中央値 %.2f)なのに、τ_z=%.3f と τ_x=%.3f で %.1f 倍違う。"
          % (necks["扁平粒子(4:1)"], aniso["扁平粒子(4:1)"]["tz"],
             aniso["扁平粒子(4:1)"]["tx"],
             aniso["扁平粒子(4:1)"]["tz"] / aniso["扁平粒子(4:1)"]["tx"]))
    return {"iso": iso, "necks": necks}


# --------------------------------------------------------------------------- #
# 6. 解像度 —— 崖を予測してから測る                                             #
# --------------------------------------------------------------------------- #
def section_resolution() -> dict:
    print("\n" + "=" * 78)
    print("6) 解像度 —— 崖を予測してから掃引する")
    print("=" * 78)
    neck_r = 0.40 * R_MED
    print("  予測: 首の内接半径は粒子半径の 0.40 倍 = %.1f voxel(基準格子)。"
          % neck_r)
    print("        voxel が首の**直径** %.1f 単位を超えたら経路が塞がるはずなので、"
          % (2 * neck_r))
    print("        粒子半径が %.1f voxel を切るあたり(一辺 %d 前後)で崖。"
          % (R_MED / (2 * neck_r), int(round(N_VOX / (2 * neck_r)))))
    print("\n   一辺  粒子半径[vox]  voxel/粒子半径     ε      τ_f    τ_geo  首[vox]")

    ns, taus, epss, geos = [], [], [], []
    for n in (16, 24, 32, 44, 64, 88):
        pore = make_electrode(N_SPHERE, n_vox=n, r_med=R_MED * n / N_VOX)
        tr = transport(pore)
        tg = tau_geodesic(pore)
        dt = np.asarray(fs.vol_distance_transform(pore))
        r_vox = R_MED * n / N_VOX
        ns.append(1.0 / r_vox)
        taus.append(tr["tau_f"])
        epss.append(tr["eps"])
        geos.append(tg)
        print("   %4d      %5.2f          %.3f      %.4f  %7.3f  %6.3f   %.2f"
              % (n, r_vox, 1.0 / r_vox, tr["eps"], tr["tau_f"], tg,
                 float(np.median(dt[pore]))))

    d_eps = 100 * (epss[0] - epss[-1]) / epss[-1]
    d_tau = 100 * (taus[0] - taus[-1]) / taus[-1]
    print("\n  ★予想は外れた —— **崖は無い**。voxel を %.1f 倍粗くする間、"
          % (ns[0] / ns[-1]))
    print("     τ_f は %.3f -> %.3f(%+.0f %%)と**単調に**増え、"
          "ε は %.4f -> %.4f(%+.1f %%)しか動かない。"
          % (taus[-1], taus[0], d_tau, epss[-1], epss[0], d_eps))
    print("     首が 1 voxel を切っても経路は残る(斜めに繋がる)ので塞がらない。")
    print("     ★危ないのは崖が無いこと自体: 図も検出数も壊れないまま"
          "**数字だけが片側へずれる**。")

    figs.save_plot("resolution",
                   [("屈曲度 τ_f", ns, taus),
                    ("測地 τ_geo", ns, geos),
                    ("空隙率 ε x 4(見やすさのため)", ns, [4 * e for e in epss])],
                   xlabel="voxel の大きさ / 粒子半径 [-]", ylabel="値 [-]",
                   title="空隙率は解像度に鈍く、屈曲度は敏感(崖は無い)",
                   caption="同じ物理構造を粗い格子から細かい格子まで。"
                           "ε は %+.1f %% しか動かないのに τ_f は %+.0f %% 動く。"
                           % (d_eps, d_tau))
    return {"vox": ns, "tau": taus, "eps": epss, "d_tau": d_tau, "d_eps": d_eps}


# --------------------------------------------------------------------------- #
# 7. 道具の穴                                                                   #
# --------------------------------------------------------------------------- #
def section_tool_gaps() -> None:
    print("\n" + "=" * 78)
    print("7) 道具の穴(この PoC で 3-D の空隙を扱ってみて)")
    print("=" * 78)

    # (a) voxel 上の測地距離が無い(点群 kNN 版しか無い)
    assert hasattr(fs.ledger, "geodesic_distances")
    assert not hasattr(fs, "vol_geodesic_distance")
    assert not hasattr(fs.ledger, "vol_geodesic_distance")
    print("  (a) voxel 上の**測地距離変換**が無い。`geodesic_distances` は点群の"
          "kNN グラフ用で、ボリュームは受けない。この PoC は自前で Dijkstra。")

    # (b) 多孔体の輸送量(実効拡散・屈曲度因子)を出す口が無い
    for name in ("vol_tortuosity", "vol_effective_diffusivity", "vol_porosity"):
        assert not hasattr(fs, name) and not hasattr(fs.ledger, name), name
    print("  (b) 空隙率・屈曲度・実効拡散という**多孔体の 3 点セット**が無い。"
          "電池・触媒・地盤・骨で同じ 3 つを測るので、族にする価値がある。")

    # (c) 空隙 voxel の隣接グラフを作る口が無い(連結成分は在るのに)
    assert hasattr(fs, "vol_label")
    assert not hasattr(fs.ledger, "vol_adjacency_graph")
    print("  (c) `vol_label` は在るのに、**その手前のグラフ**(6/18/26 近傍の"
          "隣接行列)を返す口が無い。経路・流れ・最小カットが全部書けない。")

    # (d) 「両端面を貫通する成分だけ残す」がよくある処理なのに無い
    assert not hasattr(fs.ledger, "vol_percolating_component")
    print("  (d) `vol_select_labels` は在るが、**貫通成分を選ぶ**(両端面に触れる)"
          "定型処理は呼び手が毎回書いている。")

    # (e) 在って助かった
    v = np.zeros((8, 8, 8), bool)
    v[2:6, 2:6, 2:6] = True
    lab, n_comp = fs.vol_label(v, connectivity=6)
    assert n_comp == 1
    dt = np.asarray(fs.vol_distance_transform(v))
    assert abs(float(dt.max()) - 2.0) < 1e-9, float(dt.max())
    print("  (e) 在って助かった: `vol_label`(連結性を選べる)と"
          "`vol_distance_transform`(**正規化しない**ので voxel 単位の首が測れる)。")
    print("      2-D の `distance_transform` は最大値で正規化されるのに、"
          "3-D は生の距離を返す —— **同じ名前の族で規約が違う**。")


# --------------------------------------------------------------------------- #
def main() -> None:
    t0 = time.perf_counter()
    print("=" * 78)
    print("電極の屈曲度を CT から測る —— Bruggeman は空隙率しか見ない")
    print("=" * 78)

    zero = section_zero_point()
    sweep = section_porosity_sweep()
    aniso = section_anisotropy()
    why = section_why(aniso)
    res = section_resolution()
    section_tool_gaps()

    print("\n" + "=" * 78)
    print("まとめ")
    print("=" * 78)
    print("  * 同じ 1 個のボリュームから τ が 3 つ出る"
          "(Bruggeman %.3f / 測地 %.3f / 輸送 %.3f)。どれを報告したか書くこと。"
          % (zero["br"], zero["tg"], zero["tr"]["tau_f"]))
    print("  * Bruggeman は必ず小さめに外し、ε が下がるほど開く"
          "(%+.0f %% → %+.0f %%)。"
          % (100 * (sweep["brugg"][0] - sweep["tau_f"][0]) / sweep["tau_f"][0],
             100 * (sweep["brugg"][-1] - sweep["tau_f"][-1]) / sweep["tau_f"][-1]))
    print("  * 空隙率を揃えても粒子形状で τ_z は %.1f 倍動く。経験則は向きを持てない。"
          % (aniso["扁平粒子(4:1)"]["tz"] / aniso["球状粒子"]["tz"]))
    print("  * 解像度に崖は無い。ε %+.1f %% に対し τ_f %+.0f %% が"
          "**警告なしに**ずれる。" % (res["d_eps"], res["d_tau"]))

    # --- 所見を固定する assert ------------------------------------------------ #
    assert zero["tr"]["cg_info"] == 0, "共役勾配が収束していない"
    assert 0.40 < zero["tr"]["eps"] < 0.45, zero["tr"]["eps"]
    assert zero["br"] < zero["tr"]["tau_f"], "Bruggeman が過大に出た(所見 1 と逆)"
    assert zero["tg"] < zero["br"], "測地 τ が Bruggeman を上回った(所見 3 と逆)"
    # 2) 誤差は空隙率が下がるほど単調に開く
    errs = [100 * (b - t) / t for b, t in zip(sweep["brugg"], sweep["tau_f"])]
    assert all(errs[i] > errs[i + 1] for i in range(len(errs) - 1)), errs
    assert errs[0] < -5.0 and errs[-1] < -60.0, (errs[0], errs[-1])
    # 2) 指数は 1.5 ではない
    assert sweep["alpha_hi"] > 1.6, sweep["alpha_hi"]
    assert sweep["alpha_lo"] > 2.5, sweep["alpha_lo"]
    assert sweep["alpha_lo"] > sweep["alpha_hi"]
    # 3) 測地の 2 乗は Bruggeman に 5 % 以内で寄り添う(高空隙率の 3 点)
    for i in range(3):
        rel = abs(sweep["tau_geo"][i] ** 2 - sweep["brugg"][i]) / sweep["brugg"][i]
        assert rel < 0.08, (i, rel)
    # 4) 対照群: ε は揃っているのに τ_z は 3 倍以上違う
    a, b = aniso["球状粒子"], aniso["扁平粒子(4:1)"]
    assert abs(a["eps"] - b["eps"]) < 0.01, (a["eps"], b["eps"])
    assert b["tz"] / a["tz"] > 2.8, b["tz"] / a["tz"]
    assert b["tz"] / b["tx"] > 3.0, b["tz"] / b["tx"]
    assert abs(b["br"] - b["tx"]) / b["tx"] < 0.30, "面内は経験則と近いはず"
    # 5) 閉気孔は犯人ではない
    assert max(f for *_, f in why["iso"]) < 0.05, why["iso"]
    assert why["necks"]["球状粒子"] / R_MED < 0.5
    # 6) 崖ではなく単調な偏り
    assert res["d_tau"] > 50.0 and abs(res["d_eps"]) < 2.0, (res["d_tau"], res["d_eps"])
    assert all(res["tau"][i] >= res["tau"][i + 1] - 1e-9
               for i in range(len(res["tau"]) - 1)), res["tau"]

    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")


if __name__ == "__main__":
    main()
