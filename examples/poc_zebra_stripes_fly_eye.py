# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: 縞に近づくハエの眼 ―― シマウマの縞は複眼の距離感を本当に狂わせるのか、
そして複眼がフィボナッチ(Vogel 螺旋)の並びならもっと優秀か

    py -3.11 examples/poc_zebra_stripes_fly_eye.py                   # 図なし・約 30 秒
    py -3.11 examples/poc_zebra_stripes_fly_eye.py --figures         # GIF 2 本 + 図 + 表
    py -3.11 examples/poc_zebra_stripes_fly_eye.py --trajectories <dir>   # 外部真値(Dryad)を読む

【問い】アブ(tabanid)はシマウマの縞の手前で制御された減速ができず(Caro ら 2019)、縞・市松の
近くでは速く飛び・寄らず・着地しない(How ら 2020)。「縞で距離感が狂う」という俗説は、複眼と
相関型運動検出器(Hassenstein–Reichardt)の**閉じた式**でどこまで説明でき、どこからは説明できないか。
機構の説は未決着で、アパーチャ効果説は市松でも回避したので How ら 2020 が棄却、エイリアシング説は
Caro ら 2023 が「弱い」、偏光説(Egri ら 2012)も 2023 に不支持。Dettlaff(2026、arXiv:2605.17049、
**査読前・単著・コードとデータは非公開**)はモアレ説を 1〜5 m の接近で唱えるが、実測の軌跡とは
照合していない。本 PoC の差別化は 4 つ: (1) 閉形式の門(ナイキスト距離・MTF・HR の符号反転・2τ の
恒等式)、(2) 六角格子 + ガウス受容角での**解析的な**標本化(画像を介さない)、(3) How ら 2020 の
Dryad の 3D 軌跡との照合段(配置すれば走る)、(4) アパーチャ効果の **2τ の恒等式**を数で示すこと。

【すべて fullseye の op で。学習した数は 0。縞の面はこの PoC が座標から解析的に描く(画像を再標本化しない)】

第 1 章  種ごとのナイキスト距離と MTF(`sampling_alias_distance`、閉形式)
    縞の周期 P = 7 cm(How ら 2020、幅 3.5 cm)。六角格子は角周期 √3 Δφ までしか解像せず、
    正面で d > P/(√3 Δφ)、視線角 θ で d > P cos²θ/(√3 Δφ) を超えると縞は折り返す(エイリアス)。
    アブ(急峻帯 Δφ ≈ 1.1°): 正面 2.105 m / 60° で 0.526 m、受容角 1°(未発表値)で MTF 0.375。
    ショウジョウバエ(4.63° / 8.23°): 0.500 / 0.125 m、MTF 0.024 —— ぼけが縞を消して守る。
    ★アブの光学定数は弱い(急峻帯の値、受容角は未発表)ので、Δφ と Δρ/Δφ を掃引して見せる。

第 2 章  HR 相関器の符号反転(`fly_view_plane_texture` → `fly_t4t5_field(model="hr")`)
    方位 az の個眼対の位相差は ψ = 2π Δφ D/(P cos²az)。sin ψ < 0 の個眼は**反対向きの運動を報告**する。
    距離 1.7 m で |az| > 15.0° が反転帯(閉形式)、測った反転と 97 % 以上一致。接近すると反転帯は
    周辺へ逃げ、d < P cos²(az)/(2Δφ) で正しい向きに戻る —— 接近中の HR が「遠ざかる」から
    「近づく」へ切り替わる距離を予測と照合する(窓の幅ぶんの誤差つき)。
    ★正直に: 反転帯が視野を横切るのは 1 周期未満の時間なので、接近中の HR は輪を**静止像としては**
    持てない。輪の像は距離を固定した横滑りの快照で、接近では過渡としてだけ現れる(物理)。

第 3 章  τ(衝突時間)の読み出し(`fly_expansion_readout`、`fly_tau_from_expansion`)
    G5: 正面平面の流れ sinθcosθ/τ から τ を読む。縦縞では縦方向の流れが消え(アパーチャ効果)、
    放射方向の当てはめも発散も **厳密に 2τ** を返す。市松では τ に戻る。G6: 体の縁の拡大率は
    θ̇/θ = 1/τ で縞に依らない(幾何なので自明 —— 縁を眼の中で見つける段はこの PoC の外)。
    HR 経路(較正 1 つ: 市松の最初の窓)で縦縞・市松・1/f・灰を接近させ、τ̂/τ を時系列で測る。
    ショウジョウバエの眼では流れのエネルギーがアブの 1 % 未満 —— 眼のぼけで無反応。
    How ら 2020 の「市松でも避けた → アパーチャ効果説は棄却」の論理を、この数で再現する。

第 4 章  フィボナッチの複眼(`fly_vogel_lattice`、`lattice_moire_peak`)
    同じ 721 個眼・同じ平均間隔 1.1° の 3 つの眼: 六角 / Vogel 螺旋(r ∝ √n、θ = n·137.508°)/
    ジッタ付き六角(σ = 0.25 Δφ)。(a) ナイキストを超えた縞のモアレの尖り(ピーク/背景の中央値)、
    (b) 偽オプティカルフロー(真の向きと逆の HR 応答のエネルギー比)、(c) ナイキスト直下の縞の
    コントラスト再現率と残差、(d) 密度指数で中心を密にした螺旋の中心窩の効果。
    予想: 解像は六角が最良、モアレの拡散は Vogel が勝つ。違えばそのまま書く。

第 5 章  外部真値(How ら 2020、Dryad doi:10.5061/dryad.18931zctk、CC0)
    `--trajectories <dir>` に 3D 軌跡を置けば、本数(grey 107 / vertical 101 / horizontal 107 /
    checked 101)の門、0.1〜0.6 m 区間の速度と最接近距離、τ̇(`traj_tau_dot`)、予測反転距離と
    急旋回距離の照合を行う。省略時は「未配置」と明示して飛ばし、配置方法を印字する。

【Fullseye への寄与】周期パターン × 周期格子のモアレは外観検査(LCD・メッシュ・織物・ラインスキャン)、
網点、レール波状摩耗と同じ物理。`sampling_alias_distance` は検査カメラの作動距離の設計規則(画素 IFOV を
Δφ に読み替える)。「縞の上では相関型運動検出が距離情報を失う」(時間周波数 v tanθ/P は距離に依らない)は
周期構造の上に光流で着地する機体(AGV・ドローン)の故障モード。記事はハエ記事(コネクトーム追記専用の
レーン)へ追記する。

参考: T. Caro ら, *PLoS ONE* 14:e0210831 (2019); M. J. How ら, *Proc. R. Soc. B* 287:20201521 (2020);
T. Caro ら, *J. Exp. Biol.* 226:jeb244778 (2023); Á. Egri ら, *J. Exp. Biol.* 215:736 (2012);
K. M. Dettlaff, arXiv:2605.17049 (2026、査読前・単著); P. T. Gonzalez-Bellido ら, *PNAS* 108:4224 (2011);
D. P. Petersen & D. Middleton, *Inf. Control* 5:279 (1962); J. I. Yellott, *Science* 221:382 (1983);
D. N. Lee, *Perception* 5:437 (1976); H. Wagner, *Nature* 297:147 (1982).
"""
from __future__ import annotations

import argparse
import glob
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import examplefig as figs  # noqa: E402
import fullseye as fs  # noqa: E402

L = fs.ledger

# ---------------------------------------------------------------------------- #
#  世界と種                                                                       #
# ---------------------------------------------------------------------------- #
P = 0.07                               # 縞の周期 [m](How ら 2020: 幅 3.5 cm)
#: 種: (Δφ[度], Δρ[度], 出典 / 弱さ)
SPECIES = {
    "アブ(急峻帯)": (1.1, 1.0, "Δφ は急峻帯の値、Δρ は未発表の目安(弱い)"),
    "ショウジョウバエ": (4.63, 8.23, "Gonzalez-Bellido ら 2011(暗順応)"),
    "蚊(目安)": (2.5, 2.5, "Δφ 2.5°、Δρ/Δφ = 1 と仮定(弱い)"),
}
DPHI, DRHO = SPECIES["アブ(急峻帯)"][:2]
DT = 0.005                             # 200 Hz
TAU_HR = 0.02                          # 相関器の時定数 [s]


def centre_index(lat):
    uv = np.asarray(lat["uv"])
    return int(np.where((uv[:, 0] == 0) & (uv[:, 1] == 0))[0][0])


def mtf(drho_deg, f_cyc_per_rad):
    d = np.deg2rad(drho_deg)
    return float(np.exp(-np.pi ** 2 * d * d * f_cyc_per_rad ** 2 / (4.0 * np.log(2.0))))


def render_movie(lat, dists, pattern, drho, lateral=None, contrast=1.0):
    """距離の列(と横位置の列)で縞の面を見た個眼動画 (T, n)。画像は 1 枚も作らない。"""
    out = []
    for k, d in enumerate(dists):
        lat_m = (0.0, 0.0) if lateral is None else (float(lateral[k]), 0.0)
        out.append(L.fly_view_plane_texture(lat, float(d), P, pattern, drho_deg=drho,
                                            contrast=contrast, mean=0.5, lateral_m=lat_m))
    return np.array(out)


def hr_flow(movie, lat):
    """個眼動画 → HR(6 方向)→ 局所フロー (n, 2)。直流は時間平均で落とす(ラミナの定常順応)。"""
    m = movie - movie.mean(axis=0)
    field = L.fly_t4t5_field(m, lat, DT, model="hr", tau_hr_s=TAU_HR)
    return field, L.fly_flow_from_directions(field, lat)


def plane_flow(lat, tau, axis=None):
    """正面平面を τ で接近するときの真の流れ sinθ cosθ/τ(外向き)。"""
    dirs = lat["dirs"]
    a = dirs[centre_index(lat)] if axis is None else np.asarray(axis, float)
    el = np.asarray(lat["el_rad"])
    az = np.asarray(lat["az_rad"])
    e_az = np.stack([-np.sin(az), np.cos(az), np.zeros_like(az)], axis=-1)
    e_el = np.stack([-np.sin(el) * np.cos(az), -np.sin(el) * np.sin(az), np.cos(el)], axis=-1)
    cosang = np.clip(dirs @ a, -1.0, 1.0)
    th = np.arccos(cosang)
    r = -(a[None, :] - cosang[:, None] * dirs)
    rn = np.linalg.norm(r, axis=1)
    r[rn > 1e-12] /= rn[rn > 1e-12, None]
    radial = np.stack([(r * e_az).sum(1), (r * e_el).sum(1)], axis=1)
    return (np.sin(th) * np.cos(th) / tau)[:, None] * radial, th, radial


def stripe_normal_in_eye(lat, dist):
    """縦縞の濃淡勾配(面の y 方向)が各個眼の接平面でどの向きに見えるか(単位ベクトル)。"""
    dirs = lat["dirs"]
    az = np.asarray(lat["az_rad"])
    el = np.asarray(lat["el_rad"])
    e_az = np.stack([-np.sin(az), np.cos(az), np.zeros_like(az)], axis=-1)
    e_el = np.stack([-np.sin(el) * np.cos(az), -np.sin(el) * np.sin(az), np.cos(el)], axis=-1)
    dx = dirs[:, 0]
    # y = D d_y/d_x の接平面での勾配(方位・仰角成分)
    gy_az = dist * (e_az[:, 1] * dx - dirs[:, 1] * e_az[:, 0]) / (dx * dx)
    gy_el = dist * (e_el[:, 1] * dx - dirs[:, 1] * e_el[:, 0]) / (dx * dx)
    g = np.stack([gy_az, gy_el], axis=1)
    return g / np.maximum(np.linalg.norm(g, axis=1, keepdims=True), 1e-12)


# ---------------------------------------------------------------------------- #
#  格子に依らない相関器(第 4 章): Delaunay の辺ごとの HR                               #
# ---------------------------------------------------------------------------- #
def gnomonic(lat):
    a = lat["dirs"][centre_index(lat)]
    az0, el0 = float(np.arctan2(a[1], a[0])), float(np.arcsin(a[2]))
    b_az = np.array([-np.sin(az0), np.cos(az0), 0.0])
    b_el = np.array([-np.sin(el0) * np.cos(az0), -np.sin(el0) * np.sin(az0), np.cos(el0)])
    den = lat["dirs"] @ a
    return np.degrees(np.stack([(lat["dirs"] @ b_az) / den, (lat["dirs"] @ b_el) / den], axis=1))


def delaunay_pairs(lat):
    from scipy.spatial import Delaunay
    g = gnomonic(lat)
    tri = Delaunay(g)
    e = set()
    for s in tri.simplices:
        for i, j in ((s[0], s[1]), (s[1], s[2]), (s[2], s[0])):
            e.add((min(i, j), max(i, j)))
    pairs = np.array(sorted(e), dtype=np.int64)
    return g, pairs


def lowpass_columns(x, tau, dt):
    alpha = 1.0 - np.exp(-dt / tau)
    out = np.empty_like(x)
    acc = x[0].copy()
    for t in range(x.shape[0]):
        acc += alpha * (x[t] - acc)
        out[t] = acc
    return out


def hr_pairs(movie, pairs):
    """辺 (i, j) ごとの HR の時間平均: LP[a_i] a_j − a_i LP[a_j](`fly_emd_response` と同じ式)。
    正 = i から j へ向かう運動。"""
    m = movie - movie.mean(axis=0)
    lp = lowpass_columns(m, TAU_HR, DT)
    i, j = pairs[:, 0], pairs[:, 1]
    return (lp[:, i] * m[:, j] - m[:, i] * lp[:, j]).mean(axis=0)


def jittered_hex(lat, sigma_frac, seed):
    rng = np.random.default_rng(seed)
    jit = sigma_frac * lat["dphi_rad"]
    az = np.asarray(lat["az_rad"]) + rng.normal(0.0, jit, lat["dirs"].shape[0])
    el = np.asarray(lat["el_rad"]) + rng.normal(0.0, jit, lat["dirs"].shape[0])
    ce = np.cos(el)
    dirs = np.stack([ce * np.cos(az), ce * np.sin(az), np.sin(el)], axis=-1)
    out = dict(lat)
    out.update({"az_rad": az, "el_rad": el, "dirs": dirs, "geometry": "jitter"})
    return out


def sub_eye(lat, keep):
    """個眼の部分集合だけの眼(中心を含むこと)。"""
    out = dict(lat)
    for k in ("uv", "az_rad", "el_rad", "dirs", "rho_rad", "nn_rad"):
        if k in out:
            out[k] = np.asarray(out[k])[keep]
    return out


# ---------------------------------------------------------------------------- #
#  図の小道具                                                                     #
# ---------------------------------------------------------------------------- #
def hex_raster(lat, values, step_deg=0.35, pad=1.0, dphi_deg=DPHI):
    az = np.degrees(np.asarray(lat["az_rad"]))
    el = np.degrees(np.asarray(lat["el_rad"]))
    xs = np.arange(az.min() - pad, az.max() + pad, step_deg)
    ys = np.arange(el.max() + pad, el.min() - pad, -step_deg)
    X, Y = np.meshgrid(xs, ys)
    d2 = (X[..., None] - az) ** 2 + (Y[..., None] - el) ** 2
    k = np.argmin(d2, axis=2)
    out = np.asarray(values, float)[k]
    out[np.take_along_axis(d2, k[..., None], axis=2)[..., 0] > (1.2 * dphi_deg) ** 2] = np.nan
    return out, xs, ys


def to_rgb(raster, signed, vmax=None):
    a = np.nan_to_num(raster, nan=0.0)
    if signed:
        m = vmax if vmax else max(float(np.abs(a).max()), 1e-12)
        lut = np.asarray(fs.diverging_lut(256))
        idx = np.clip(((a / m) * 0.5 + 0.5) * 255.0, 0, 255).astype(int)
        rgb = lut[idx][..., :3]
    else:
        lo, hi = (0.0, vmax) if vmax else (float(a.min()), float(a.max()))
        g = np.clip((a - lo) / max(hi - lo, 1e-12), 0.0, 1.0)
        rgb = np.repeat(g[..., None], 3, axis=2)
    rgb = np.array(rgb, dtype=float)
    rgb[np.isnan(raster)] = 1.0
    return rgb


# ---------------------------------------------------------------------------- #
#  第 5 章: Dryad の 3D 軌跡を読む                                                    #
# ---------------------------------------------------------------------------- #
CONDITIONS = ("grey", "vertical", "horizontal", "checked")
EXPECTED_COUNTS = {"grey": 107, "vertical": 101, "horizontal": 107, "checked": 101}
DRYAD = "https://datadryad.org/stash/dataset/doi:10.5061/dryad.18931zctk"


def read_trajectories(directory):
    """``<dir>/*.csv`` を読む。各ファイル = 1 本の軌跡。列は見出し行で ``x,y,z,t`` と、あれば
    ``condition``(無ければファイル名の先頭 grey / vertical / horizontal / checked)。単位 m・s。
    Dryad の .m スクリプト(zebraflytrajectories_2018.m)の出力形式は未確認なので、この CSV 形式へ
    変換して置く(repo にデータは同梱しない)。"""
    trajs = []
    for path in sorted(glob.glob(os.path.join(directory, "*.csv"))):
        with open(path, encoding="utf-8") as fh:
            head = fh.readline().strip().lower().split(",")
            rows = [ln.strip().split(",") for ln in fh if ln.strip()]
        col = {h.strip(): i for i, h in enumerate(head)}
        need = [c for c in ("x", "y", "z", "t") if c not in col]
        if need:
            raise ValueError("%s: 列 %s が無い(期待する見出し: x,y,z,t[,condition])" % (path, need))
        xyz = np.array([[float(r[col["x"]]), float(r[col["y"]]), float(r[col["z"]])] for r in rows])
        t = np.array([float(r[col["t"]]) for r in rows])
        if "condition" in col:
            cond = rows[0][col["condition"]].strip().lower()
        else:
            stem = os.path.basename(path).lower()
            cond = next((c for c in CONDITIONS if stem.startswith(c)), "unknown")
        trajs.append((cond, xyz, t))
    return trajs


def chapter5(directory, target, normal, checks, rows):
    print()
    print("5. 外部真値(How ら 2020、Dryad の 3D 軌跡)")
    if not directory:
        print("   未配置: --trajectories <dir> が無いので飛ばす。配置方法:")
        print("     1. %s から data.zip(1.21 GB、ログイン後にダウンロード)を取る" % DRYAD)
        print("     2. 軌跡を CSV(見出し x,y,z,t[,condition]、単位 m・s、1 ファイル = 1 本)に変換し、")
        print("        ファイル名の先頭を grey / vertical / horizontal / checked にする")
        print("     3. py -3.11 examples/poc_zebra_stripes_fly_eye.py --trajectories <dir> "
              "[--target x,y,z --normal nx,ny,nz]")
        print("   期待する本数: grey 107 / vertical 101 / horizontal 107 / checked 101")
        rows.append(["Dryad 軌跡", "未配置", "-", "-", "-"])
        return
    trajs = read_trajectories(directory)
    counts = {c: sum(1 for cd, _x, _t in trajs if cd == c) for c in CONDITIONS}
    print("   本数: %s(期待 %s)" % (counts, EXPECTED_COUNTS))
    checks.append(("Dryad の本数が論文と一致", counts == EXPECTED_COUNTS))
    pred = L.sampling_alias_distance(P, DPHI)["distance_m"]
    for c in CONDITIONS:
        speeds, closest, taudots, turns = [], [], [], []
        for cd, xyz, t in trajs:
            if cd != c or xyz.shape[0] < 3:
                continue
            r = L.traj_tau_dot(xyz, t, target=target, normal=normal)
            d = r["distance_m"]
            band = (d >= 0.1) & (d <= 0.6)
            if band.any():
                speeds.append(float(np.nanmedian(np.abs(r["speed_m_s"][band]))))
                taudots.append(float(np.nanmedian(r["tau_dot"][band])))
            closest.append(r["closest_m"])
            vel = np.gradient(xyz, t, axis=0)
            sp = np.linalg.norm(vel, axis=1)
            ok = sp > 1e-6
            if ok.sum() > 3:
                u = vel[ok] / sp[ok, None]
                ang = np.degrees(np.arccos(np.clip((u[1:] * u[:-1]).sum(1), -1.0, 1.0)))
                k = np.where(ang > 60.0)[0]
                if k.size:
                    turns.append(float(d[ok][k[0]]))
        med = lambda a: float(np.median(a)) if a else float("nan")  # noqa: E731
        print("   %-10s 0.1-0.6 m の速さ中央値 %.3f m/s  最接近 %.3f m  τ̇ 中央値 %.2f  "
              "急旋回(>60°)の距離 %.2f m(予測の反転距離 %.2f m)"
              % (c, med(speeds), med(closest), med(taudots), med(turns), pred))
        rows.append([c, "%.3f" % med(speeds), "%.3f" % med(closest), "%.2f" % med(taudots),
                     "%.2f" % med(turns)])


# ---------------------------------------------------------------------------- #
#  本体                                                                          #
# ---------------------------------------------------------------------------- #
def main(argv=None):
    ap = argparse.ArgumentParser(description="縞に近づくハエの眼")
    ap.add_argument("--figures", action="store_true", help="図・GIF を書く(FULLSEYE_FIGURE_DIR)")
    ap.add_argument("--trajectories", default="", help="How ら 2020 の軌跡 CSV のディレクトリ")
    ap.add_argument("--target", default="0,0,0", help="縞の面の上の 1 点 x,y,z [m]")
    ap.add_argument("--normal", default="1,0,0", help="縞の面の法線 nx,ny,nz")
    a = ap.parse_args(argv)
    if a.figures:
        os.environ.setdefault("FULLSEYE_FIGURES", "on")
    t_start = time.time()
    checks, rows = [], []
    np.set_printoptions(precision=4, suppress=True)
    print("縞に近づくハエの眼 —— 周期 P = %.0f cm、アブ Δφ = %.1f° / Δρ = %.1f°(弱い定数、掃引あり)"
          % (P * 100, DPHI, DRHO))

    # ================================================================ 1. ナイキスト距離
    print()
    print("1. 種ごとのナイキスト距離と MTF(閉形式 d = P cos²θ/(√3 Δφ))")
    nyq = {}
    for name, (dphi, drho, note) in SPECIES.items():
        r0 = L.sampling_alias_distance(P, dphi, acceptance_deg=drho)
        r60 = L.sampling_alias_distance(P, dphi, view_angle_deg=60.0)
        nyq[name] = (r0["distance_m"], r60["distance_m"], r0["mtf_at_nyquist"])
        print("   %-12s Δφ %.2f° Δρ %.2f°: 正面 %.3f m / 60° %.3f m / MTF@Nyq %.3f   (%s)"
              % (name, dphi, drho, r0["distance_m"], r60["distance_m"], r0["mtf_at_nyquist"], note))
        rows.append([name, "%.3f" % r0["distance_m"], "%.3f" % r60["distance_m"],
                     "%.3f" % r0["mtf_at_nyquist"], note])
    tb, dm = nyq["アブ(急峻帯)"], nyq["ショウジョウバエ"]
    checks.append(("アブ: 2.105 / 0.526 m、MTF 0.375",
                   abs(tb[0] - 2.105) < 2e-3 and abs(tb[1] - 0.526) < 1e-3 and abs(tb[2] - 0.375) < 1e-3))
    checks.append(("ショウジョウバエ: 0.500 / 0.125 m、MTF 0.024",
                   abs(dm[0] - 0.500) < 1e-3 and abs(dm[1] - 0.125) < 1e-3 and abs(dm[2] - 0.024) < 1e-3))
    # 解析的な面の MTF が閉形式と一致(fly_view_plane_texture の門)
    lat_c = L.fly_hex_lattice(radius=4, dphi_deg=DPHI)
    c = centre_index(lat_c)
    v0 = L.fly_view_plane_texture(lat_c, 1.0, P, "sine", drho_deg=DRHO)[c] - 0.5
    v90 = L.fly_view_plane_texture(lat_c, 1.0, P, "sine", drho_deg=DRHO, phase_deg=90.0)[c] - 0.5
    amp = float(np.hypot(v0, v90)) / 0.5
    print("   解析的な面(1 m、正弦): 中心個眼の振幅 %.6f = exp(−(πΔρ f)²/4ln2) %.6f" % (amp, mtf(DRHO, 1.0 / P)))
    checks.append(("解析的な面の MTF は閉形式に 1e-9 で一致", abs(amp - mtf(DRHO, 1.0 / P)) < 1e-9))
    print("   アブの定数の掃引(Δφ 0.7〜2.0°、Δρ/Δφ = 0.8 / 1.0 / 1.5):")
    sweep = {}
    for ratio in (0.8, 1.0, 1.5):
        ds, ms = [], []
        for dphi in (0.7, 0.9, 1.1, 1.3, 1.5, 2.0):
            r = L.sampling_alias_distance(P, dphi, acceptance_deg=ratio * dphi)
            ds.append(r["distance_m"])
            ms.append(r["mtf_at_nyquist"])
        sweep[ratio] = (np.array(ds), np.array(ms))
        print("     Δρ/Δφ %.1f: 正面の反転距離 %s m、MTF@Nyq %s"
              % (ratio, np.round(ds, 2), np.round(ms, 3)))
    checks.append(("反転距離は Δφ に反比例、MTF は Δρ/Δφ だけで決まる",
                   bool(np.all(np.diff(sweep[1.0][0]) < 0))
                   and float(np.ptp(sweep[1.0][1])) < 1e-12))

    # ================================================================ 2. 符号反転
    print()
    print("2. HR 相関器の符号反転(位相差 ψ = 2πΔφD/(P cos²az)、sin ψ < 0 で逆向きを報告)")
    eye = L.fly_hex_lattice(radius=18, dphi_deg=DPHI)
    n_eye = eye["dirs"].shape[0]
    az_e = np.asarray(eye["az_rad"])
    uv_e = np.asarray(eye["uv"])
    field_r = DPHI * 18
    print("   眼: %d 個眼、視野半径 %.1f°" % (n_eye, field_r))
    u_slip = 0.3                                           # 横滑り [m/s]
    T_slip = 60
    tt = np.arange(T_slip) * DT
    snaps = []                                             # (d, flow (n,2), R0 (n,))
    agree = []
    for d in np.linspace(1.95, 1.45, 11):
        movie = render_movie(eye, np.full(T_slip, d), "vertical", DRHO, lateral=u_slip * tt)
        field, flow = hr_flow(movie, eye)
        R0 = field[0]                                      # 方位の隣(step (0, 1))との HR
        psi = 2.0 * np.pi * np.deg2rad(DPHI) * d / (P * np.cos(az_e) ** 2)
        pred_flip = (psi % (2.0 * np.pi)) > np.pi
        s_ref = np.sign(np.sum(R0 * np.where(pred_flip, -1.0, 1.0)))   # 大勢の符号
        meas_flip = np.sign(R0) == -s_ref
        clear = (np.abs((psi % (2.0 * np.pi)) - np.pi) > 0.2) & (R0 != 0.0)
        ag = float(np.mean(meas_flip[clear] == pred_flip[clear]))
        agree.append(ag)
        snaps.append((d, flow, R0, pred_flip))
        if abs(d - 1.7) < 0.03 or d in (1.95, 1.45):
            print("   d = %.2f m: 反転の予測 |az| > %s、測定との一致 %.1f %%(境界 ±0.2 rad と縁を除く)"
                  % (d, ("%.1f°" % np.degrees(np.arccos(np.sqrt(min(1.0, 2 * np.deg2rad(DPHI) * d / P)))))
                     if 2 * np.deg2rad(DPHI) * d / P < 1.0 else "全視野", 100 * ag))
    checks.append(("反転帯は閉形式と 97 % 以上一致(11 距離)", min(agree) >= 0.97))
    frac = [float(np.mean(s[3])) for s in snaps]
    checks.append(("接近すると反転帯は周辺へ逃げる(反転する個眼の割合が単調に減る)",
                   bool(np.all(np.diff(frac) <= 0.0)) and frac[0] > 0.9 and frac[-1] < 0.3))
    # 接近中の過渡: 「遠ざかる」→「近づく」の切り替わり距離
    v_app = 0.5
    d_path = 2.0 - v_app * np.arange(int(1.2 / DT)) * DT
    movie = render_movie(eye, d_path, "vertical", DRHO)
    W = 60
    band = (np.abs(np.degrees(az_e)) > 10.0) & (np.abs(np.degrees(az_e)) < 18.0) & (np.abs(uv_e).max(1) < 18)
    _f, th_e, radial_e = plane_flow(eye, 1.0)
    series_d, series_pair, series_sum = [], [], []
    for k in range(W, len(d_path), 12):
        field, flow = hr_flow(movie[k - W:k], eye)
        R0 = field[0]
        series_d.append(float(d_path[k - W // 2]))
        # 方位の対: 外向き = az > 0 で +、az < 0 で −。「遠ざかる」の報告はその逆
        series_pair.append(float(R0[band & (az_e > 0)].mean() - R0[band & (az_e < 0)].mean()))
        series_sum.append(float((flow * radial_e).sum(1)[band].mean()))
    series_d, series_pair, series_sum = np.array(series_d), np.array(series_pair), np.array(series_sum)
    cross = np.where((series_pair[:-1] < 0) & (series_pair[1:] >= 0))[0]
    d_cross = float(series_d[cross[0]]) if cross.size else float("nan")
    d_pred = (P * np.cos(np.deg2rad(18.0)) ** 2 / (2 * np.deg2rad(DPHI)),
              P * np.cos(np.deg2rad(10.0)) ** 2 / (2 * np.deg2rad(DPHI)))
    print("   接近 %.1f m/s、|az| 10〜18° の方位の対: 「遠ざかる」→「近づく」の切り替わり d = %.2f m"
          "(予測 %.2f〜%.2f m、窓 0.3 s = ±%.2f m)" % (v_app, d_cross, d_pred[0], d_pred[1], v_app * W * DT / 2))
    d_sum_flip = 2.0 * P / (2 * np.deg2rad(DPHI))
    print("   ★6 方向を束ねた放射流れは %.1f〜%.1f m で一度も反転しない(全窓 > 0): ±60° の対は投影間隔が"
          " Δφ/2 なので d > %.1f m まで折り返さず、方位の対の反転を上書きする"
          % (d_path[-1], d_path[0], d_sum_flip))
    checks.append(("接近中の方位の対の切り替わり距離が予測の範囲(窓の幅ぶん)に入る",
                   np.isfinite(d_cross) and d_pred[0] - 0.16 <= d_cross <= d_pred[1] + 0.16))
    checks.append(("6 方向を束ねた流れは反転しない(±60° の対が上書き、閉形式 d > %.1f m)" % d_sum_flip,
                   bool(np.all(series_sum > 0.0))))
    rows.append(["符号反転の切り替わり距離(方位の対)", "%.2f m" % d_cross, "%.2f-%.2f m" % d_pred, "-", "接近 0.5 m/s"])

    # ================================================================ 3. τ の読み出し
    print()
    print("3. τ の読み出し —— アパーチャ効果の 2τ(閉形式)と HR 経路の実測")
    lat3 = L.fly_hex_lattice(radius=12, dphi_deg=DPHI)
    tau_true = 1.3
    f_true, th3, _rad = plane_flow(lat3, tau_true)
    full = L.fly_expansion_readout(f_true, lat3)
    g = stripe_normal_in_eye(lat3, tau_true * 0.5)
    f_ap = (f_true * g).sum(1)[:, None] * g                 # 縦縞: 縞の勾配の向きの成分だけ残る
    aper = L.fly_expansion_readout(f_ap, lat3)
    print("   真の流れ:   τ̂ 放射 %.6f / 発散 %.6f(真値 %.1f、等方性 %.3f)"
          % (full["tau_s"], full["tau_div_s"], tau_true, full["aperture_ratio"]))
    print("   縦縞(アパーチャ): τ̂ 放射 %.4f / 発散 %.4f = 真値の %.3f / %.3f 倍(等方性 %.3f)"
          % (aper["tau_s"], aper["tau_div_s"], aper["tau_s"] / tau_true, aper["tau_div_s"] / tau_true,
             aper["aperture_ratio"]))
    checks.append(("真の流れは τ を 1e-9 で返す", abs(full["tau_s"] - tau_true) < 1e-9
                   and abs(full["tau_div_s"] - tau_true) < 1e-9))
    checks.append(("縦縞の流れは 2τ を返す(放射・発散とも 1 % 以内)",
                   abs(aper["tau_s"] / (2 * tau_true) - 1) < 0.01 and abs(aper["tau_div_s"] / (2 * tau_true) - 1) < 0.01))
    # G6: 縁の拡大率
    tgrid = np.arange(0.0, 1.0, DT)
    d_t = 1.2 - 0.5 * tgrid
    theta_edge = 2.0 * np.arctan(0.6 / d_t)
    tau_edge = L.fly_tau_from_expansion(theta_edge, DT, shape="disk")
    err_edge = float(np.nanmax(np.abs(tau_edge[2:-2] - d_t[2:-2] / 0.5)))
    print("   縁(半径 0.6 m の体)の拡大率から: τ̂ − d/v の最大 %.2e s(縞の種類は式に入らない = 影響なし)" % err_edge)
    checks.append(("縁の拡大率の τ は幾何だけで決まる", err_edge < 1e-3))
    # G4: 正面接近の時間周波数 v tan(az)/P は距離に依らない(位相の傾きが一定)
    lat_g = L.fly_hex_lattice(radius=12, dphi_deg=DPHI)
    uv_g = np.asarray(lat_g["uv"])
    k12 = int(np.argmin(np.abs(np.degrees(np.asarray(lat_g["az_rad"])) - 12.0) + 1e3 * (uv_g[:, 0] != 0)))
    az12 = float(np.asarray(lat_g["az_rad"])[k12])
    d_g = 1.2 - 0.5 * np.arange(0.0, 1.6, DT)
    ph = []
    for d in d_g:
        v0 = L.fly_view_plane_texture(lat_g, d, P, "sine", drho_deg=DRHO)[k12] - 0.5
        v9 = L.fly_view_plane_texture(lat_g, d, P, "sine", drho_deg=DRHO, phase_deg=90.0)[k12] - 0.5
        ph.append(np.arctan2(v9, v0))
    ph = np.unwrap(np.array(ph))
    slope = np.polyfit(np.arange(ph.size) * DT, ph, 1)[0] / (2 * np.pi)
    f_g4 = 0.5 * np.tan(az12) / P
    lin = float(np.abs(ph - np.polyval(np.polyfit(np.arange(ph.size) * DT, ph, 1), np.arange(ph.size) * DT)).max())
    print("   G4: 方位 %.1f° の個眼の時間周波数 = %.4f Hz(閉形式 v tan(az)/P = %.4f Hz)、1.2 → 0.4 m の間 位相は直線"
          "(残差 %.1e rad)—— 距離が 3 倍変わっても相関器の入力の周波数は変わらない" % (np.degrees(az12), abs(slope), f_g4, lin))
    checks.append(("G4: 接近中の時間周波数は距離に依らない(閉形式と 1e-6、位相の残差 < 1e-6)",
                   abs(abs(slope) - f_g4) < 1e-6 and lin < 1e-6))
    # HR 経路の実測(較正 1 つ)
    d0, d1 = 1.2, 0.4
    n_t = int((d0 - d1) / 0.5 / DT)
    d_path3 = d0 - 0.5 * np.arange(n_t) * DT
    W3, step3 = 50, 25
    results = {}
    for sp_name, (dphi, drho, _note) in (("アブ(急峻帯)", SPECIES["アブ(急峻帯)"]),
                                         ("ショウジョウバエ", SPECIES["ショウジョウバエ"])):
        lat_s = L.fly_hex_lattice(radius=12 if dphi < 2 else 3, dphi_deg=dphi)
        rim = np.abs(np.asarray(lat_s["uv"])).max(1) == (12 if dphi < 2 else 3)
        wts = (~rim).astype(float)
        per = {}
        for pat in ("checker", "vertical", "pink", "grey"):
            movie = render_movie(lat_s, d_path3, pat, drho)
            rates, energy, ts, iso = [], [], [], []
            for k in range(W3, n_t + 1, step3):
                _field, flow = hr_flow(movie[k - W3:k], lat_s)
                r = L.fly_expansion_readout(flow, lat_s, weights=wts)
                rates.append(r["rate_1_s"])
                energy.append(float((flow[~rim] ** 2).sum()))
                ts.append(float(d_path3[k - W3 // 2] / 0.5))
                iso.append(r["aperture_ratio"])
            per[pat] = (np.array(ts), np.array(rates), np.array(energy), np.array(iso))
        results[sp_name] = per
    tab = results["アブ(急峻帯)"]
    gain = (1.0 / tab["checker"][0][0]) / tab["checker"][1][0]      # 較正 1 つ: 市松の最初の窓
    print("   HR 経路(%d 窓、較正は市松の最初の窓 1 つ):" % len(tab["checker"][0]))
    ratio = {}
    iso = {}
    for pat in ("checker", "vertical", "pink", "grey"):
        ts, rates, en, iso[pat] = tab[pat]
        tau_hat = np.where(rates > 0, 1.0 / (gain * rates), np.nan)
        ratio[pat] = tau_hat / ts
        print("     %-9s τ̂/τ = %s  等方性(縦/横の流れ) %s  流れのエネルギー %.2e"
              % (pat, np.round(ratio[pat], 2), np.round(iso[pat], 2), float(en.mean())))
        rows.append(["HR τ̂/τ " + pat, "%.2f" % float(np.nanmedian(ratio[pat])),
                     "%.2f" % float(np.nanmin(ratio[pat])), "%.2f" % float(np.nanmax(ratio[pat])), "アブ"])
    vc = float(np.nanmedian(ratio["vertical"] / ratio["checker"]))
    print("     縦縞 / 市松 の τ̂ の比の中央値 %.2f(幾何の 2 に対して)。★較正 1 つでは市松の τ̂/τ が %.2f → %.2f と"
          "流れる: 相関器は速度計ではなく、位相差 sin(2πΔφD/(P cos²az)) が距離で動く(相関器の性質、既知)"
          % (vc, ratio["checker"][0], ratio["checker"][-1]))
    checks.append(("HR 経路の流れは縦縞で一方向(等方性 < 0.15)、市松と 1/f で両方向(> 0.5)、全窓",
                   bool(np.all(iso["vertical"] < 0.15)) and bool(np.all(iso["checker"] > 0.5))
                   and bool(np.all(iso["pink"] > 0.5))))
    checks.append(("縦縞 / 市松 の τ̂ の比の中央値は 1 より大きい(2 に届かない点は上の数のまま)", vc > 1.0))
    checks.append(("灰の面には読める流れが無い",
                   float(tab["grey"][2].mean()) < 1e-6 * float(tab["checker"][2].mean())))
    dro = results["ショウジョウバエ"]
    e_ratio = float(dro["vertical"][2].mean() / tab["vertical"][2].mean())
    print("   ショウジョウバエ(Δφ 4.63°/Δρ 8.23°): 縦縞の流れのエネルギーはアブの %.2e 倍 —— 眼のぼけで無反応" % e_ratio)
    checks.append(("ショウジョウバエの眼は縞に無反応(流れのエネルギー < 1 %)", e_ratio < 0.01))
    rows.append(["ショウジョウバエ 流れ/アブ", "%.1e" % e_ratio, "-", "-", "縦縞"])
    print("   → How ら 2020 の論理: 市松の流れは等方(等方性 %.2f)で τ を幾何どおりに返すのにアブは市松も避けた → "
          "アパーチャ効果説だけでは説明できない(ここでも同じ)" % float(np.median(iso["checker"])))

    # ================================================================ 4. フィボナッチの眼
    print()
    print("4. フィボナッチ(Vogel 螺旋)の複眼 —— 六角 / Vogel / ジッタ付き六角(同じ 721 個眼・平均間隔 %.1f°)" % DPHI)
    hexl = L.fly_hex_lattice(radius=15, dphi_deg=DPHI)
    vog = L.fly_vogel_lattice(radius=15, dphi_deg=DPHI)
    jit = jittered_hex(hexl, 0.25, seed=7)
    floor = np.sqrt(3.0) * np.deg2rad(DPHI)
    lattices = (("六角", hexl), ("Vogel", vog), ("ジッタ六角", jit))
    # 相関器の式が op と同じこと(門)
    g0, p0 = delaunay_pairs(hexl)
    mv = render_movie(hexl, np.full(40, 1.0), "vertical", DRHO, lateral=u_slip * np.arange(40) * DT)
    r_pairs = hr_pairs(mv, p0[:5])
    m0 = mv - mv.mean(0)
    r_op = np.array([L.fly_emd_response(m0[:, i], m0[:, j], tau_s=TAU_HR, dt_s=DT).mean() for i, j in p0[:5]])
    checks.append(("辺ごとの HR は fly_emd_response と同じ式", float(np.abs(r_pairs - r_op).max()) < 1e-12))
    table4 = []
    stats = {}
    for name, lat in lattices:
        g, pairs = delaunay_pairs(lat)
        row = {"name": name, "pairs": pairs.shape[0]}
        # (a) モアレの尖り: ナイキストを超えた縞(λ = 0.8 √3Δφ)と直下(1.1 √3Δφ)
        for tag, frac in (("above", 0.8), ("below", 1.1)):
            D = P / (frac * floor)
            sig = L.fly_view_plane_texture(lat, D, P, "sine", drho_deg=DRHO)
            r = L.lattice_moire_peak(sig, lat)
            row["peak_" + tag] = r["peak_ratio"]
            row["fpeak_" + tag] = r["peak_cycles_per_deg"]
            # (c) コントラスト再現率(真の周波数での当てはめ)と残差
            x = g
            f_true4 = np.array([1.0 / np.degrees(P / D), 0.0])
            ph = 2.0 * np.pi * (x @ f_true4)
            A = np.stack([np.cos(ph), np.sin(ph), np.ones_like(ph)], axis=1)
            coef, *_ = np.linalg.lstsq(A, sig, rcond=None)
            amp_fit = float(np.hypot(coef[0], coef[1]))
            resid = float(np.sqrt(np.mean((sig - A @ coef) ** 2)))
            amp_true = 0.5 * mtf(DRHO, D / P)
            row["repro_" + tag] = amp_fit / amp_true
            row["resid_" + tag] = resid / amp_true
        # (b) 偽オプティカルフロー: 横滑り(ナイキスト超えの距離)で、真の向きと逆の応答のエネルギー比
        for tag, frac in (("above", 0.8), ("below", 1.3)):
            D = P / (frac * floor)
            mv = render_movie(lat, np.full(60, D), "vertical", DRHO, lateral=u_slip * tt)
            R = hr_pairs(mv, pairs)
            dx = g[pairs[:, 1], 0] - g[pairs[:, 0], 0]       # 辺の方位成分(度)
            dy = g[pairs[:, 1], 1] - g[pairs[:, 0], 1]
            # 眼が +y(左)へ滑ると模様は −方位へ流れる: 正しい応答は sign(R) == −sign(dx)
            expect = -np.sign(dx)
            ok = np.abs(dx) > 0.2 * DPHI
            wrong = (np.sign(R[ok]) != expect[ok]) & (R[ok] != 0)
            row["false_" + tag] = float((R[ok][wrong] ** 2).sum() / max((R[ok] ** 2).sum(), 1e-300))
            row["coh_" + tag] = float((R[ok] * expect[ok]).sum() / max(np.abs(R[ok]).sum(), 1e-300))
            # 向きで分ける: 方位に沿う対(|dy| < tan 20° |dx|)と、斜めの対(残り)
            along = ok & (np.abs(dy) < np.tan(np.deg2rad(20.0)) * np.abs(dx))
            diag = ok & ~along
            for sub, m in (("along", along), ("diag", diag)):
                row["coh_%s_%s" % (sub, tag)] = (float((R[m] * expect[m]).sum() / max(np.abs(R[m]).sum(), 1e-300))
                                                 if m.any() else float("nan"))
                row["n_%s" % sub] = int(m.sum())
        stats[name] = row
        print("   %-7s 辺 %4d | モアレ尖り 超え %7.1f / 直下 %7.1f | 偽フロー比 超え %.2f(一貫性 全 %+.2f: 方位の対 %+.2f"
              " / 斜めの対 %+.2f) 直下 %.2f(%+.2f) | 再現率 直下 %.3f 残差 %.3f"
              % (name, row["pairs"], row["peak_above"], row["peak_below"], row["false_above"], row["coh_above"],
                 row["coh_along_above"], row["coh_diag_above"], row["false_below"], row["coh_below"],
                 row["repro_below"], row["resid_below"]))
        table4.append([name, "%.0f" % row["peak_above"], "%.0f" % row["peak_below"],
                       "%.2f / %+.2f (%+.2f, %+.2f)" % (row["false_above"], row["coh_above"],
                                                       row["coh_along_above"], row["coh_diag_above"]),
                       "%.2f / %+.2f" % (row["false_below"], row["coh_below"]),
                       "%.3f" % row["repro_below"], "%.3f" % row["resid_below"]])
    h, v, j = stats["六角"], stats["Vogel"], stats["ジッタ六角"]
    checks.append(("ナイキスト超えの縞: 六角は鋭いモアレ(尖り > 100)、Vogel は拡散(< 1/10)",
                   h["peak_above"] > 100 and v["peak_above"] < h["peak_above"] / 10))
    checks.append(("ナイキスト超えの横滑り: 六角の方位の対は全部逆向き(< −0.95)、斜めの対(投影間隔 Δφ/2)は全部正しい(> +0.95)",
                   h["coh_along_above"] < -0.95 and h["coh_diag_above"] > 0.95))
    print("   ★偽フローは格子の規則性ではなく**対の間隔**で決まる: 六角の方位の対(間隔 Δφ)は閉形式どおり全部逆向き、"
          "斜めの対(投影 Δφ/2)は全部正しい。Vogel の方位寄りの対も一貫性 %+.2f —— 散らしても同じ間隔の対は反転する"
          % v["coh_along_above"])
    checks.append(("ナイキスト直下: 六角の再現率が最良で残差が最小",
                   h["resid_below"] < v["resid_below"] and h["resid_below"] < j["resid_below"]
                   and abs(h["repro_below"] - 1.0) <= min(abs(v["repro_below"] - 1.0), abs(j["repro_below"] - 1.0)) + 1e-9))
    print("   予想「解像は六角が最良、モアレ拡散は Vogel が勝つ」: %s"
          % ("そのとおり" if (h["resid_below"] < v["resid_below"] and v["peak_above"] < h["peak_above"] / 10) else "違った(上の数のまま)"))
    # (d) 密度指数: 中心窩
    print("   (d) 密度指数 p(中心の密度 ∝ k^(1−2p))—— 中心 5° の平均間隔と、全体のナイキストを超えた縞の中心での尖り:")
    D_ab = P / (0.8 * floor)
    f_true4 = 1.0 / np.degrees(P / D_ab)
    fov_rows = []
    for pw in (0.5, 0.65, 0.8):
        vv = L.fly_vogel_lattice(radius=15, dphi_deg=DPHI, density_power=pw)
        inner = np.degrees(vv["rho_rad"]) < 5.0
        nn_in = float(np.degrees(vv["nn_rad"][inner]).mean())
        d_in = L.sampling_alias_distance(P, nn_in)["distance_m"]
        sig = L.fly_view_plane_texture(vv, D_ab, P, "sine", drho_deg=DRHO)
        r_in = L.lattice_moire_peak(sig[inner], sub_eye(vv, inner), fmax_cycles_per_deg=2.0 * f_true4)
        found = abs(abs(r_in["peak_cycles_per_deg"][0]) - f_true4) < 0.06 * f_true4
        fov_rows.append((pw, nn_in, d_in, found, r_in["peak_ratio"]))
        print("     p = %.2f: 中心 5° の間隔 %.2f°(中心のナイキスト距離 %.2f m、縞は %.2f m)、"
              "中心 %d 個眼の最強ピークは真の周波数 %.3f c/°に %s、尖り %.1f"
              % (pw, nn_in, d_in, D_ab, int(inner.sum()), f_true4, "一致" if found else "不一致", r_in["peak_ratio"]))
        table4.append(["Vogel p=%.2f 中心 5°" % pw, "%.1f" % r_in["peak_ratio"], "-", "-", "-",
                       "間隔 %.2f°" % nn_in, "Nyq %.2f m" % d_in])
    checks.append(("中心を密にするほど(p 0.5 → 0.8)中心の間隔は狭まり、真の周波数のピークは鋭くなる",
                   all(r[3] for r in fov_rows)
                   and fov_rows[0][1] > fov_rows[1][1] > fov_rows[2][1]
                   and fov_rows[0][4] < fov_rows[1][4] < fov_rows[2][4]))
    print("   ★不規則な標本化では、既知の周波数の当てはめは平均のナイキストを超えても振幅を返す(上の再現率 %.3f)。"
          "中心窩の効き目は「見つかるか」ではなく「どれだけ鋭く見えるか」(尖り %.1f → %.1f)"
          % (v["repro_below"], fov_rows[0][4], fov_rows[2][4]))

    # ================================================================ 5. 外部真値
    target = tuple(float(x) for x in a.target.split(","))
    normal = tuple(float(x) for x in a.normal.split(","))
    chapter5(a.trajectories, target, normal, checks, rows)

    # ================================================================ 図
    if figs.enabled():
        figs.save_plot("nyquist_sweep",
                       [("Δρ/Δφ = %.1f" % r, np.array([0.7, 0.9, 1.1, 1.3, 1.5, 2.0]), sweep[r][0]) for r in sweep],
                       xlabel="個眼間角 Δφ [度]", ylabel="正面の反転距離 [m]",
                       title="7 cm の縞が複眼で折り返す距離(閉形式、Δρ/Δφ に依らない)",
                       caption="the alias distance P/(sqrt3 dphi) for a 7 cm period against the inter-ommatidial angle; "
                               "the acceptance ratio changes only the contrast left at Nyquist, not the distance")
        # GIF 1: 眼の像 + HR の反転帯(距離ごとの快照)
        frames = []
        vmax_flow = max(float(np.abs(s[2]).max()) for s in snaps)
        for d, flow, R0, pred_flip in snaps:
            img = L.fly_view_plane_texture(eye, d, P, "vertical", drho_deg=DRHO)
            left, _xs, _ys = hex_raster(eye, img, step_deg=0.5)
            right, xs, ys = hex_raster(eye, R0, step_deg=0.5)
            rgb_l = to_rgb(left, False, vmax=1.0)
            rgb_r = to_rgb(right, True, vmax=vmax_flow)
            lim = 2 * np.deg2rad(DPHI) * d / P
            if lim < 1.0:
                azb = np.degrees(np.arccos(np.sqrt(lim)))
                for xb in (-azb, azb):
                    col = int(np.argmin(np.abs(xs - xb)))
                    rgb_r[:, max(col - 1, 0):col + 2] = 0.0
            frames.append(np.concatenate([rgb_l, np.ones((rgb_l.shape[0], 6, 3)), rgb_r], axis=1))
        assert all(np.isfinite(f).all() and f.std() > 0.05 for f in frames)
        figs.save_gif("reversal_ring", frames, fps=3.0,
                      caption="left: what the 1027 ommatidia of a 1.1-degree eye see of 7 cm stripes at the distance "
                              "shown (1.95 m down to 1.45 m); right: the HR correlator between azimuthal neighbours "
                              "during a sideways slip (orange = one way, blue = the other) with the closed-form reversal "
                              "boundary |az| = acos(sqrt(2 dphi d / P)) drawn in black. Far away the whole eye reports "
                              "the stripes moving the wrong way; as the eye closes in the correct report grows from the "
                              "centre and the reversal retreats to the periphery")
        # GIF 2: 推定 τ と真 τ の時系列(窓が増えていく)
        ts_c, _r, _e = tab["checker"]
        series = {pat: ratio[pat] * ts_c for pat in ("vertical", "checker", "pink")}
        frames2 = []
        for k in range(2, len(ts_c) + 1):
            img = figs.render_plot(
                [("縦縞", ts_c[:k], series["vertical"][:k]), ("市松", ts_c[:k], series["checker"][:k]),
                 ("1/f", ts_c[:k], series["pink"][:k]), ("真値 τ", ts_c, ts_c), ("2τ", ts_c, 2 * ts_c)],
                xlabel="真の τ [s](接近 0.5 m/s、1.2 → 0.4 m)", ylabel="HR 経路の τ̂ [s]",
                title="縞の上では τ が 2 倍に読める(較正は市松の最初の窓 1 つ)",
                styles=[None, None, None, "dashed", "dotted"],
                colors=["wrong", "right", "neutral", "reference", "reference"],
                xlim=(float(ts_c.min()) - 0.1, float(ts_c.max()) + 0.1), ylim=(0.0, float(2.6 * ts_c.max())))
            frames2.append(img)
        assert all(np.isfinite(f).all() for f in frames2) and len({f.shape for f in frames2}) == 1
        figs.save_gif("tau_readout", frames2, fps=3.0,
                      caption="the time-to-contact read by the HR pathway (radial fit of the flow over the eye, one "
                              "gain calibrated on the first checkerboard window) against the true tau during an "
                              "approach at 0.5 m/s: over vertical stripes it runs near 2 tau — the aperture effect — "
                              "and over a checkerboard it tracks tau")
        figs.save_table("lattices",
                        ["格子", "モアレ尖り(超え)", "尖り(直下)", "偽フロー比/一貫性(超え)", "偽フロー比/一貫性(直下)",
                         "再現率(直下)", "残差(直下)"],
                        table4, title="六角 / Vogel 螺旋 / ジッタ付き六角(721 個眼、平均間隔 1.1°)",
                        caption="moire sharpness = strongest peak / median of the sub-Nyquist spectrum; false flow = "
                                "energy of HR pair responses with the wrong sign / total, and the coherence (+1 all "
                                "right, -1 all wrong); reproduction = fitted amplitude at the true frequency / "
                                "analytic amplitude, and the rms residual relative to it")
        figs.save_table("numbers", ["項目", "値 1", "値 2", "値 3", "注"], rows,
                        title="縞に近づくハエの眼: 測った数")

    print()
    print("走行 %.1f 秒。学習した数: 0。較正した数: 1(市松の最初の窓の利得)" % (time.time() - t_start))
    bad = [n for n, ok in checks if not ok]
    for n, ok in checks:
        print("  [%s] %s" % ("ok" if ok else "NG", n))
    if bad:
        print("FAIL: %d 件の検査が成り立たなかった" % len(bad))
        raise SystemExit(1)
    assert not figs.errors(), figs.errors()
    print("PASS")


if __name__ == "__main__":
    main()
