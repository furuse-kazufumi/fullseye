# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""配管内面の減肉を展開図で測る —— 軸を決める段が、管底の腐食を食う。

placeholder docstring(実行後に実測値を転記する)
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

_L = fs.ledger

# --- 管の諸元(すべて mm)---------------------------------------------------- #
R0 = 50.0               # 呼び内半径
T0 = 6.0                # 呼び肉厚
LZ = 300.0              # 調査した管長

# --- 仕込む欠陥(真値)------------------------------------------------------- #
OVAL_A = 1.2            # 楕円化の振幅(内外面に同じだけ効く = 減肉ではない)
OVAL_PSI = np.deg2rad(20.0)
BEND = 2.0              # 軸のたわみ(管長中央で最大)

PIT_Z, PIT_TH = 120.0, np.deg2rad(40.0)
PIT_D, PIT_SZ, PIT_SS = 2.5, 6.0, 8.0        # 深さ / z の σ / 周方向弧長の σ

BAND_Z0, BAND_Z1, BAND_D, BAND_RAMP = 160.0, 195.0, 0.6, 6.0    # 全周減肉

CRES_Z0, CRES_Z1 = 15.0, 85.0                # 管底腐食(下水管でいちばん多い形)
CRES_D, CRES_RAMP, CRES_TH = 1.5, 8.0, np.deg2rad(270.0)

WELD_Z, WELD_W, WELD_H, WELD_RAMP = 235.0, 4.0, 1.5, 3.0        # 溶接ビード(内側へ)

# --- 測定の諸元 -------------------------------------------------------------- #
NZ, NTH = 120, 180      # 展開図の格子(z × θ)
THRESH = 0.5            # 減肉と判定するしきい値 [mm]
SIGMA_D = 0.05          # 距離測定の雑音 [mm]
DROPOUT = 0.03          # 欠測率
MIN_BLOB = 6            # 減肉塊として残す最小画素数
SEED = 7

VOX = 1.5               # 体積モデルのボクセル辺長 [mm]

TH = 2.0 * np.pi * np.arange(NTH) / NTH      # 展開図の角度軸(周期格子)
ZS = np.linspace(0.0, LZ, NZ)

#: 欠陥の既定(倍率。0 にするとその欠陥だけ止まる = 対照群)
FULL = {"pit": 1.0, "band": 1.0, "cres": 1.0, "weld": 1.0, "oval": 1.0,
        "bend": 1.0, "cres_z": (CRES_Z0, CRES_Z1)}
CLEAN = {"pit": 0.0, "band": 0.0, "cres": 0.0, "weld": 0.0, "oval": 0.0,
         "bend": 0.0, "cres_z": (CRES_Z0, CRES_Z1)}


def spec(**kw) -> dict:
    """既定から差分で条件を作る(対照群を 1 行で書くため)。"""
    s = dict(FULL)
    s.update(kw)
    return s


# --------------------------------------------------------------------------- #
# 真値 —— 内面半径 R_in(z, θ) を式で置く                                        #
# --------------------------------------------------------------------------- #
def _ramp(t):
    """0→1 の滑らかな立ち上がり(smoothstep)。"""
    t = np.clip(np.asarray(t, float), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _window(z, a, b, ramp):
    """[a, b] で 1、外側 ``ramp`` mm で 0 に落ちる窓。"""
    return _ramp((z - (a - ramp)) / ramp) * _ramp(((b + ramp) - z) / ramp)


def _wrap(dth):
    """角度差を -π..π へ。"""
    return (np.asarray(dth, float) + np.pi) % (2.0 * np.pi) - np.pi


def axis_offset(z, s):
    """管の軸のたわみ [mm](曲がり)。z のみの関数、y 方向。"""
    u = np.asarray(z, float) / LZ
    return s["bend"] * BEND * 4.0 * u * (1.0 - u)


def loss_parts(z, th, s) -> dict:
    """欠陥ごとの減肉 [mm](正 = 肉が減った)。**これが真値**。"""
    z = np.asarray(z, float)
    th = np.asarray(th, float)
    ds = R0 * _wrap(th - PIT_TH)                       # 孔食までの弧長
    pit = s["pit"] * PIT_D * np.exp(
        -((z - PIT_Z) ** 2 / (2 * PIT_SZ ** 2) + ds ** 2 / (2 * PIT_SS ** 2)))
    band = s["band"] * BAND_D * _window(z, BAND_Z0, BAND_Z1, BAND_RAMP)
    z0, z1 = s["cres_z"]
    cres = (s["cres"] * CRES_D
            * np.clip(np.cos(_wrap(th - CRES_TH)), 0.0, None)
            * _window(z, z0, z1, CRES_RAMP))
    weld = -s["weld"] * WELD_H * _window(z, WELD_Z - WELD_W, WELD_Z + WELD_W,
                                         WELD_RAMP)
    return {"pit": pit, "band": band, "cres": cres, "weld": weld,
            "total": pit + band + cres + weld}


def ovality(th, s):
    """楕円化 [mm]。**内外面に同じだけ効くので肉厚は変わらない**。"""
    return s["oval"] * OVAL_A * np.cos(2.0 * (np.asarray(th, float) - OVAL_PSI))


def r_in_true(z, th, s):
    """内面半径(その z の軸中心から測る)。"""
    return R0 + ovality(th, s) + loss_parts(z, th, s)["total"]


# --------------------------------------------------------------------------- #
# 真の欠陥体積 —— 解析場を細かい格子で積分する(閉形式の検算つき)               #
# --------------------------------------------------------------------------- #
def true_volume(part: str, s=FULL, nz=900, nth=1440) -> float:
    """欠陥 ``part`` が奪った肉の体積 [mm^3]。

    半径場 ``r`` の環状体積は ``∫∫ (r_in² - r_ref²)/2 dθ dz``。``r_ref`` は
    その欠陥が無いときの内面(楕円化は含む)なので、楕円化は打ち消えて
    **減肉の分だけ**が残る。
    """
    z = np.linspace(0.0, LZ, nz)[:, None]
    th = (2 * np.pi * np.arange(nth) / nth)[None, :]
    d = loss_parts(z, th, s)[part]
    ref = R0 + ovality(th, s)
    dv = ((ref + d) ** 2 - ref ** 2) / 2.0
    return float(dv.sum() * (LZ / (nz - 1)) * (2 * np.pi / nth))


# --------------------------------------------------------------------------- #
# 測定 —— 管内を走るセンサから内面までの距離                                    #
# --------------------------------------------------------------------------- #
def survey(s=FULL, offset=0.0, off_dir=np.deg2rad(90.0), tilt_deg=0.0,
           noise=True, seed=SEED, nz=NZ, nth=NTH) -> dict:
    """センサの軌跡(既知のオフセットと傾き)から距離を測る。

    センサは直線上を進む。測る面は**センサの進行方向に直交する面**なので、
    傾ければ管を斜めに切る。返すのは各 (z, θ) の距離 ``dist`` と、光線が
    実際に当たった点の (z, φ)。当たった点で真値を読むのが筋(センサの
    格子の (z, θ) で読むと、傾きの分だけ真値の側がずれる)。
    """
    z_s = np.linspace(0.0, LZ, nz)
    th = 2.0 * np.pi * np.arange(nth) / nth

    a = np.deg2rad(tilt_deg)
    u = np.array([np.cos(a), np.sin(a), 0.0])            # (z, y, x) 進行方向
    v_a = np.array([0.0, 0.0, 1.0])                      # 面内基底 1 = +x
    v_b = -np.cross(u, v_a)                              # 面内基底 2 (傾き 0 で +y)
    v_b /= np.linalg.norm(v_b)

    # センサ位置: 管長中央で offset だけ横にずれ、そこから直線で進む
    t = (z_s - LZ / 2.0) / u[0]
    p0 = np.array([LZ / 2.0, offset * np.sin(off_dir), offset * np.cos(off_dir)])
    pos = p0[None, :] + t[:, None] * u[None, :]          # (nz, 3)
    dirs = (np.cos(th)[:, None] * v_a[None, :]
            + np.sin(th)[:, None] * v_b[None, :])        # (nth, 3)

    lo = np.zeros((nz, nth))
    hi = np.full((nz, nth), R0 + 40.0)
    p = pos[:, None, :]
    d = dirs[None, :, :]
    for _ in range(46):
        mid = 0.5 * (lo + hi)
        q = p + mid[..., None] * d
        zz = q[..., 0]
        yy = q[..., 1] - axis_offset(zz, s)
        xx = q[..., 2]
        rho = np.hypot(yy, xx)
        phi = np.arctan2(yy, xx)
        inside = rho < r_in_true(zz, phi, s)
        lo = np.where(inside, mid, lo)
        hi = np.where(inside, hi, mid)
    lam = 0.5 * (lo + hi)
    q = p + lam[..., None] * d
    z_hit = q[..., 0]
    th_hit = np.arctan2(q[..., 1] - axis_offset(z_hit, s), q[..., 2]) % (2 * np.pi)

    dist = lam.copy()
    valid = np.ones_like(dist, bool)
    if noise:
        rng = np.random.default_rng(seed)
        dist = dist + rng.normal(0.0, SIGMA_D, dist.shape)
        valid &= rng.random(dist.shape) > DROPOUT
        # 鏡面反射で 1 本の帯が丸ごと落ちる(実機でいちばん多い欠測の形)
        valid[:, 100:107] = False
    out = np.where(valid, dist, np.nan)
    return {"dist": out, "z": z_s, "th": th, "z_hit": z_hit, "th_hit": th_hit,
            "valid": valid, "spec": s}


# --------------------------------------------------------------------------- #
# 展開図の補正 —— 「軸をどこまで自由に動かしてよいか」の 1 本のつまみ           #
# --------------------------------------------------------------------------- #
def _fill_theta(m):
    """欠測を θ 方向の線形補間で埋める(周期境界をまたぐ)。"""
    out = np.array(m, float)
    for i in range(out.shape[0]):
        row = out[i]
        ok = np.isfinite(row)
        if ok.all():
            continue
        if ok.sum() < 4:
            row[:] = np.nanmean(out) if np.isfinite(np.nanmean(out)) else 0.0
            continue
        idx = np.nonzero(ok)[0]
        ext_i = np.concatenate([idx - NTH, idx, idx + NTH])
        ext_v = np.tile(row[idx], 3)
        row[~ok] = np.interp(np.nonzero(~ok)[0], ext_i, ext_v)
    return out


def harmonic(m, k):
    """各 z 行の k 周期成分(複素係数)。``m`` は欠測なしの (nz, nth)。"""
    return (2.0 / m.shape[1]) * (m * np.exp(-1j * k * TH)[None, :]).sum(1)


def synth(c, k):
    """複素係数を (nz, nth) の実数場へ戻す。"""
    return np.real(np.asarray(c)[:, None] * np.exp(1j * k * TH)[None, :])


def _smooth_z(c, order):
    """複素係数の z 依存を ``order`` 次多項式に落とす(``None`` = 素通し)。"""
    if order is None:
        return np.asarray(c)
    zz = ZS / LZ
    re = np.polyval(np.polyfit(zz, np.real(c), order), zz)
    im = np.polyval(np.polyfit(zz, np.imag(c), order), zz)
    return re + 1j * im


def correct(dist, k1=None, k2=None, dc=False):
    """展開図 → 減肉推定 [mm]。

    ``k1`` / ``k2`` は 1 周期 / 2 周期成分を除くときの **z 方向の多項式次数**
    (``None`` = 除かない、``"free"`` = 各 z 行で自由に除く)。``dc`` は
    各スライスの平均半径も落とす = 現場でよくやる「スライスごとの円あてはめ」。
    """
    m = _fill_theta(dist) - R0
    for k, order in ((1, k1), (2, k2)):
        if order is None:
            continue
        c = harmonic(m, k)
        m = m - synth(_smooth_z(c, None if order == "free" else int(order)), k)
    if dc:
        m = m - m.mean(1, keepdims=True)
    return m


# --------------------------------------------------------------------------- #
# 判定と採点                                                                    #
# --------------------------------------------------------------------------- #
def flag(loss_map):
    """しきい値 → 連結成分 → 小さすぎる塊を捨てる。**ゼロ点の判定器**。"""
    lab = _L.blob_label(loss_map > THRESH)
    lab = _L.blob_select(lab, "area", vmin=float(MIN_BLOB))
    return np.asarray(lab) > 0, lab


def score(sv, loss_map, s=FULL) -> dict:
    """欠陥の**種類ごとに**検出率と体積を数える(1 つの数字に畳まない)。"""
    fl, lab = flag(loss_map)
    parts = loss_parts(sv["z_hit"], sv["th_hit"], s)
    dz, dth = LZ / (NZ - 1), 2.0 * np.pi / NTH
    cell = R0 * dth * dz
    out = {"flagged": float(fl.mean()), "n_blob": int(np.asarray(lab).max())}
    for name in ("pit", "band", "cres"):
        foot = parts[name] >= THRESH
        out[name + "_rate"] = float(fl[foot].mean()) if foot.any() else 0.0
        out[name + "_vol"] = float(np.clip(loss_map, 0, None)[fl & foot].sum() * cell)
    # 偽陽性 = 本当の減肉が 0.1 mm 未満なのに旗が立った画素
    quiet = parts["total"] < 0.1
    out["false"] = float(fl[quiet].mean())
    out["false_px"] = int(np.count_nonzero(fl & quiet))
    # 溶接ビードは減肉ではない。推定した「出っ張り高さ」を符号つきで見る
    wz = np.abs(sv["z_hit"] - WELD_Z) < WELD_W
    out["weld_h"] = float(-np.median(loss_map[wz])) if wz.any() else np.nan
    return out


# --------------------------------------------------------------------------- #
# 1. 場面 —— 体積モデルを SDF の op で組み、断面と投影で見せる                   #
# --------------------------------------------------------------------------- #
def section_scene() -> dict:
    print("\n" + "=" * 78)
    print("1) 場面と真値 —— 呼び内径 %.0f mm / 呼び肉厚 %.1f mm / 管長 %.0f mm"
          % (2 * R0, T0, LZ))
    print("=" * 78)

    for name, label in (("pit", "孔食(ガウス、深さ %.1f mm)" % PIT_D),
                        ("band", "全周減肉(深さ %.2f mm)" % BAND_D),
                        ("cres", "管底腐食(最深 %.1f mm、半周)" % CRES_D),
                        ("weld", "溶接ビード(内側へ %.1f mm)" % WELD_H)):
        v = true_volume(name)
        print("   %-34s 真の体積 %+10.1f mm^3" % (label, v))
    # 閉形式の検算(孔食): ΔV = 2π σ_z σ_s D (1 次項)
    v_pit_cf = 2 * np.pi * PIT_SZ * PIT_SS * PIT_D
    v_pit = true_volume("pit")
    print("   孔食の閉形式 2π σ_z σ_s D = %.1f mm^3、数値積分 %.1f mm^3 "
          "(差 %+.2f %%、2 次項 D²/2R の分)"
          % (v_pit_cf, v_pit, 100 * (v_pit - v_pit_cf) / v_pit_cf))
    print("   楕円化 %.1f mm(内外面に同じだけ効く = 肉厚は変わらない) / "
          "曲がり 中央で %.1f mm" % (OVAL_A, BEND))

    # --- 体積モデル(ボクセル %.1f mm)を SDF の op で組む ---
    d = int(round(LZ / VOX)) + 1
    # 外面の最大半径は R0+T0+楕円化+たわみ。余白を取らないと**外壁が切れる**
    # (最初 +2 mm しか取らず、外面が volume の外に出てプローブが片側しか
    #  拾わなかった)。
    n = int(round(2 * (R0 + T0 + OVAL_A + BEND + 6) / VOX)) + 1
    zc = np.arange(d) * VOX
    yc = (np.arange(n) - (n - 1) / 2.0) * VOX
    grid = np.stack(np.meshgrid(zc, yc, yc, indexing="ij"), -1)
    # 呼びの管(直線・真円)は cylinder_sdf の差で作れる
    nom = _L.sdf_subtract(
        _L.cylinder_sdf(grid, (LZ / 2, 0, 0), (1, 0, 0), R0 + T0, LZ * 2),
        _L.cylinder_sdf(grid, (LZ / 2, 0, 0), (1, 0, 0), R0, LZ * 4))
    # 実物(楕円・曲がり・欠陥つき)は半径場から自前で組む —— 公開経路に無い
    zz = grid[..., 0]
    yy = grid[..., 1] - axis_offset(zz, FULL)
    xx = grid[..., 2]
    rho = np.hypot(yy, xx)
    phi = np.arctan2(yy, xx)
    d_out = rho - (R0 + T0 + ovality(phi, FULL))
    d_in = rho - r_in_true(zz, phi, FULL)
    built = _L.sdf_subtract(d_out, d_in)
    occ = np.asarray(_L.sdf_to_occupancy(built))
    occ_nom = np.asarray(_L.sdf_to_occupancy(nom))
    print("\n   体積モデル %s(ボクセル %.1f mm) 肉のボクセル 実物 %d / 呼び %d"
          % (str(occ.shape), VOX, int(occ.sum()), int(occ_nom.sum())))

    # esdf で肉の中心線までの距離 -> 肉厚の半分
    e = np.asarray(_L.esdf(occ, voxel_size=VOX))
    clean = slice(int(20 / VOX), int(60 / VOX))
    bandz = slice(int(BAND_Z0 / VOX) + 3, int(BAND_Z1 / VOX) - 3)
    print("   esdf の最小値(肉の芯まで): 健全部 %.2f mm / 全周減肉部 %.2f mm "
          "-> 肉厚 %.2f / %.2f mm(真値 %.2f / %.2f)"
          % (e[clean].min(), e[bandz].min(), -2 * e[clean].min(),
             -2 * e[bandz].min(), T0, T0 - BAND_D))

    # vol_wall_thickness: 産業 CT のプローブそのもの
    row = (n - 1) // 2
    zi = int(round(60 / VOX))
    th_clean = _L.vol_wall_thickness(occ, (zi, 0, row), (zi, n - 1, row),
                                     spacing=(VOX, VOX, VOX))
    zi2 = int(round((BAND_Z0 + BAND_Z1) / 2 / VOX))
    th_band = _L.vol_wall_thickness(occ, (zi2, 0, row), (zi2, n - 1, row),
                                    spacing=(VOX, VOX, VOX))
    print("   vol_wall_thickness(管を横断する 1 本のプローブ): 健全部 %s mm / "
          "全周減肉部 %s mm" % (np.round(th_clean, 2).tolist(),
                                np.round(th_band, 2).tolist()))
    print("   -> ボクセル %.1f mm では %.2f mm の全周減肉は**プローブに出ない**"
          "(量子化が %.1f mm)。" % (VOX, BAND_D, VOX))

    # 図: 断面 2 枚 + 縦断面 + 投影
    proj = np.asarray(_L.render_volume_projection(occ, azimuth=90.0, mode="xray"))
    figs.save_grid(
        "scene_pipe",
        [occ[int(PIT_Z / VOX)], occ[int((BAND_Z0 + BAND_Z1) / 2 / VOX)],
         occ[:, :, row].T, proj.T],
        ["孔食の断面 (z=%.0f mm)" % PIT_Z,
         "全周減肉の断面 (z=%.0f mm)" % ((BAND_Z0 + BAND_Z1) / 2),
         "縦断面(曲がり %.1f mm)" % BEND, "X 線積算投影"],
        title="配管の体積モデル(ボクセル %.1f mm、SDF の差で組んだ)" % VOX)

    # polar_unwrap: 1 枚の断面を (θ×r) の矩形へ
    sl = occ[int(PIT_Z / VOX)]
    pol = np.asarray(_L.polar_unwrap(sl.astype(np.float64),
                                     center=((n - 1) / 2, (n - 1) / 2),
                                     r_in=R0 - 8, r_out=R0 + T0 + 4,
                                     ntheta=360, nr=64))
    figs.save_grid("scene_polar", [sl, pol],
                   ["断面(z=%.0f mm)" % PIT_Z, "極座標展開 (θ × r)"],
                   title="円環を矩形に開く —— ここから先は 2-D の仕事")

    return {"occ": occ, "v_pit": v_pit, "v_pit_cf": v_pit_cf,
            "th_clean": th_clean, "th_band": th_band,
            "e_clean": float(e[clean].min()), "e_band": float(e[bandz].min())}


# --------------------------------------------------------------------------- #
# 2. ゼロ点 —— 軸が合っているときに素朴なしきい値がどこまで当たるか             #
# --------------------------------------------------------------------------- #
def section_zero_point() -> dict:
    print("\n" + "=" * 78)
    print("2) ゼロ点 —— 展開図の距離をそのまま R0 と比べてしきい値 %.1f mm"
          % THRESH)
    print("=" * 78)

    sv = survey(spec(oval=0.0, bend=0.0), offset=0.0)
    m0 = correct(sv["dist"])
    sc = score(sv, m0, spec(oval=0.0, bend=0.0))
    print("  【対照群 b】欠陥あり・軸ずれなし・楕円化なし・曲がりなし")
    for k, lab, tv in (("pit", "孔食", true_volume("pit")),
                       ("band", "全周減肉", true_volume("band")),
                       ("cres", "管底腐食", true_volume("cres"))):
        print("    %-10s 検出率 %5.1f %%   体積 推定 %8.1f / 真値 %8.1f mm^3 "
              "(%+6.1f %%)" % (lab, 100 * sc[k + "_rate"], sc[k + "_vol"], tv,
                               100 * (sc[k + "_vol"] - tv) / tv))
    print("    偽陽性 %.2f %% (%d 画素) / 塊 %d 個 / 溶接ビード高さ 推定 %.2f mm "
          "(真値 %.2f)" % (100 * sc["false"], sc["false_px"], sc["n_blob"],
                           sc["weld_h"], WELD_H))

    sv_all = survey(FULL, offset=0.0)
    m_all = correct(sv_all["dist"])
    sc_all = score(sv_all, m_all)
    print("\n  【対照群 c′】同じ管に楕円化 %.1f mm と曲がり %.1f mm を足しただけ"
          "(軸ずれはまだ 0)" % (OVAL_A, BEND))
    print("    偽陽性 %.2f %% (%d 画素) —— 減肉していない所に旗が立つ。"
          % (100 * sc_all["false"], sc_all["false_px"]))
    print("    楕円化は肉厚を 1 µm も変えていない(内外面に同じだけ効く)。")

    truth = loss_parts(sv_all["z_hit"], sv_all["th_hit"], FULL)["total"]
    figs.save("map_truth", truth, "真の減肉 [mm](正 = 肉が減った、"
              "溶接ビードは負)", signed=True)
    figs.save("map_naive_aligned", m0, "軸が合っているときの推定減肉 [mm]",
              signed=True)
    return {"zero": sc, "with_shape": sc_all, "truth": truth}


# --------------------------------------------------------------------------- #
# 3. 崖 —— 軸のオフセットを掃引して「腐食していない管」から偽の減肉を数える     #
# --------------------------------------------------------------------------- #
def _predict_false_fraction(e, t=THRESH, r=R0):
    """幾何の予測: 中心が e ずれた真円の管で、旗が立つ周方向の割合。

    中心から e ずれた点から角 ψ に向かって測った距離は
    ``d = -e cosψ + sqrt(R² - e² sin²ψ)``。d - R > t になる ψ の割合。
    1 次では ``d - R ≈ -e cosψ`` なので、**偽の減肉は必ず 1 周期の正弦波**で
    振幅は e。旗が立つ割合は ``arccos(t/e)/π``(e > t のときだけ)。
    """
    psi = np.linspace(0.0, np.pi, 4001)
    d = -e * np.cos(psi) + np.sqrt(np.clip(r * r - (e * np.sin(psi)) ** 2, 0.0, None))
    exact = float((d - r > t).mean())
    first = float(np.arccos(np.clip(t / e, -1, 1)) / np.pi) if e > 0 else 0.0
    return exact, first


def section_offset_sweep() -> dict:
    print("\n" + "=" * 78)
    print("3) 崖 —— 軸のオフセットを掃引(腐食ゼロ・真円・直線の管)")
    print("=" * 78)
    print("  【対照群 a】欠陥ゼロ・軸ずれあり。ここで立つ旗はすべて偽物。")
    print("   オフセット   予測(厳密)  予測(1 次)   実測    1 周期の振幅   偽の体積")

    offs = [0.0, 0.2, 0.4, 0.5, 0.55, 0.7, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0]
    meas, pred, pred1, amp1, fvol = [], [], [], [], []
    cell = R0 * (2 * np.pi / NTH) * (LZ / (NZ - 1))
    for e in offs:
        sv = survey(CLEAN, offset=e)
        m = correct(sv["dist"])
        fl, _ = flag(m)
        ex, fi = _predict_false_fraction(e)
        c1 = np.abs(harmonic(_fill_theta(sv["dist"]) - R0, 1)).mean()
        meas.append(100 * float(fl.mean()))
        pred.append(100 * ex)
        pred1.append(100 * fi)
        amp1.append(float(c1))
        fvol.append(float(np.clip(m, 0, None)[fl].sum() * cell))
        print("    %5.2f mm    %7.2f %%   %7.2f %%   %7.2f %%   %6.3f mm  "
              "%9.1f mm^3" % (e, pred[-1], pred1[-1], meas[-1], amp1[-1], fvol[-1]))

    i4 = offs.index(4.0)
    print("\n  ★軸が %.1f mm ずれただけで、**腐食していない管の %.1f %%** が"
          "減肉と判定される\n     (偽の減肉体積 %.0f mm^3 = 本物の孔食 %.0f mm^3 の"
          "%.1f 倍)。" % (offs[i4], meas[i4], fvol[i4], true_volume("pit"),
                          fvol[i4] / true_volume("pit")))
    err = max(abs(m - p) for m, p in zip(meas, pred))
    print("  ★幾何の予測(厳密)と実測の差は最大 %.2f ポイント —— "
          "偽の減肉は**必ず 1 周期**で振幅はオフセットそのもの。" % err)
    print("     1 周期の振幅の実測はオフセットの %.3f 倍(幾何の予測は 1.000)。"
          % (amp1[-1] / offs[-1]))
    i_knee = next(i for i, v in enumerate(meas) if v > 0.0)
    print("  ★崖はしきい値の所に立つ: オフセット %.2f mm(= しきい値 %.1f mm)"
          "までは偽物ゼロ、\n     %.2f mm で %.1f %% に跳ねる —— "
          "e < t なら 1 周期の正弦波はしきい値に届かないから。"
          % (offs[i_knee - 1], THRESH, offs[i_knee], meas[i_knee]))

    figs.save_plot("sweep_offset",
                   [("実測(しきい値 %.1f mm)" % THRESH, offs, meas),
                    ("幾何の予測(厳密)", offs, pred),
                    ("幾何の予測(1 次 arccos(t/e)/π)", offs, pred1)],
                   xlabel="センサ軸のオフセット [mm]",
                   ylabel="偽の減肉と判定された面積 [%]",
                   title="腐食ゼロの管から生まれる偽の減肉",
                   caption="予測を先に立ててから測った。差は最大 %.2f ポイント。" % err)

    sv = survey(CLEAN, offset=4.0)
    m = correct(sv["dist"])
    fl, _ = flag(m)
    figs.save("map_false_loss", m, "腐食ゼロの管・軸ずれ %.1f mm のときの推定減肉 "
              "[mm](1 周期の正弦波)" % 4.0, signed=True)
    figs.save_grid("map_false_flag", [m, fl.astype(float)],
                   ["推定減肉 [mm]", "旗が立った画素(%.1f %%)" % (100 * fl.mean())],
                   title="無い減肉が %.1f %% の面積に生まれる(縦 = z、横 = θ)"
                         % (100 * fl.mean()), signed=[True, False])
    return {"offs": offs, "meas": meas, "pred": pred, "amp1": amp1,
            "fvol": fvol, "err": err}


# --------------------------------------------------------------------------- #
# 4. 傾き —— 1 周期の振幅が z に比例して育つ                                    #
# --------------------------------------------------------------------------- #
def section_tilt_sweep() -> dict:
    print("\n" + "=" * 78)
    print("4) 傾きの掃引 —— 1 周期の振幅は z に比例して育つ")
    print("=" * 78)
    print("   傾き    実測の傾き   予測 tanα   偽の面積   2 周期 実測   2 周期 予測")

    tilts = [0.0, 0.1, 0.2, 0.4, 0.8, 1.2, 1.6]
    frac, slope, amp2, pred2, curves = [], [], [], [], []
    half = ZS >= LZ / 2.0            # ★|c1| は V 字なので全長で直線を引くと傾き 0
    for a in tilts:
        sv = survey(CLEAN, offset=0.0, tilt_deg=a)
        m = correct(sv["dist"])
        fl, _ = flag(m)
        raw = _fill_theta(sv["dist"]) - R0
        c1 = np.abs(harmonic(raw, 1))
        c2 = np.abs(harmonic(raw, 2))
        sl = float(np.polyfit(ZS[half], c1[half], 1)[0])
        ta = np.tan(np.deg2rad(a))
        # 2 周期に漏れる 2 つの経路: 斜め切りの楕円 R(secα-1)/2 と、
        # 傾きが作る横ずれ e(z)=tanα(z-L/2) の 2 次項 <e²>/4R
        p2 = R0 * (1 / np.cos(np.deg2rad(a)) - 1) / 2 + ta * ta * LZ * LZ / (48 * R0)
        frac.append(100 * float(fl.mean()))
        slope.append(sl)
        amp2.append(float(c2.mean()))
        pred2.append(p2)
        curves.append(c1)
        print("   %4.2f deg  %8.4f    %8.4f   %6.2f %%   %8.4f mm  %8.4f mm"
              % (a, sl, ta, frac[-1], amp2[-1], p2))

    a_last = tilts[-1]
    print("\n  ★傾き α の効きは 2 つに分かれる。1 周期は"
          "**振幅 tan α·|z - L/2| で z に線形**(実測の傾き %.4f、予測 %.4f mm/mm、"
          "\n     差 %.1f %%)。管長中央で 0 になるのは、そこでセンサが軸を横切るから。"
          % (slope[-1], np.tan(np.deg2rad(a_last)),
             100 * abs(slope[-1] - np.tan(np.deg2rad(a_last)))
             / np.tan(np.deg2rad(a_last))))
    print("     2 周期は 2 次でしか出ない(斜め切りの楕円 %.4f + 横ずれの 2 次項 "
          "%.4f = %.4f mm、\n     実測 %.4f mm)。**だから楕円化(2 周期)と軸ずれ"
          "(1 周期)は分離できる** ——\n     傾き %.1f 度が 2 周期に漏らす分は"
          " %.3f mm で、楕円化 %.1f mm の %.1f %% しかない。"
          % (R0 * (1 / np.cos(np.deg2rad(a_last)) - 1) / 2,
             np.tan(np.deg2rad(a_last)) ** 2 * LZ * LZ / (48 * R0), pred2[-1],
             amp2[-1], a_last, amp2[-1], OVAL_A, 100 * amp2[-1] / OVAL_A))

    figs.save_plot("sweep_tilt",
                   [("傾き %.1f deg" % tilts[-1], ZS, curves[-1]),
                    ("傾き %.1f deg" % tilts[4], ZS, curves[4]),
                    ("傾き %.1f deg" % tilts[2], ZS, curves[2]),
                    ("傾き 0 deg", ZS, curves[0])],
                   xlabel="管の位置 z [mm]", ylabel="1 周期成分の振幅 [mm]",
                   title="傾きは 1 周期を z に線形に育てる(V 字 = 中央で 0)",
                   caption="中央で 0 になるのは、そこでセンサが軸を横切るから。")
    figs.save_plot("tilt_leak",
                   [("2 周期の実測", tilts, amp2),
                    ("2 周期の予測(楕円 + 横ずれの 2 次項)", tilts, pred2),
                    ("楕円化の真値", tilts, [OVAL_A] * len(tilts))],
                   xlabel="センサの傾き [deg]", ylabel="2 周期成分の振幅 [mm]",
                   title="傾きが 2 周期に漏らす分は楕円化の 100 分の 1 以下")
    return {"tilts": tilts, "slope": slope, "amp2": amp2, "pred2": pred2,
            "frac": frac}


# --------------------------------------------------------------------------- #
# 5. 角周波数のスペクトル —— 3 つの対照群を分ける                               #
# --------------------------------------------------------------------------- #
def section_spectrum() -> dict:
    print("\n" + "=" * 78)
    print("5) 角周波数のスペクトル —— 何が何周期に出るか")
    print("=" * 78)

    conds = [
        ("a 欠陥ゼロ・軸ずれ %.0f mm" % 4.0, CLEAN, 4.0),
        ("b 欠陥あり・軸ずれ 0", spec(oval=0.0, bend=0.0), 0.0),
        ("c 両方", FULL, 4.0),
        ("d 楕円化だけ", spec(pit=0, band=0, cres=0, weld=0, bend=0), 0.0),
    ]
    ks = np.arange(0, 7)
    series, rows = [], []
    for name, s, e in conds:
        sv = survey(s, offset=e)
        raw = _fill_theta(sv["dist"]) - R0
        amps = [float(np.abs(harmonic(raw, k)).mean()) for k in ks]
        amps[0] *= 0.5          # k=0 は係数の定義上 2 倍になる
        series.append((name, ks, amps))
        rows.append([name] + ["%.3f" % v for v in amps])
        print("   %-24s " % name + "  ".join("k=%d:%6.3f" % (k, v)
                                             for k, v in zip(ks, amps)))
    print("\n  ★軸ずれは k=1 に、楕円化は k=2 に、全周減肉は k=0 に出る。"
          "**この 3 つは分離できる**。")
    print("     ただし管底腐食(条件 b の下半分)も k=1 に出る —— "
          "軸ずれと**同じ場所**に。")

    sv = survey(spec(pit=0, band=0, weld=0, oval=0, bend=0), offset=0.0)
    raw = _fill_theta(sv["dist"]) - R0
    cres_amps = [float(np.abs(harmonic(raw, k)).mean()) for k in ks]
    cres_amps[0] *= 0.5
    series.append(("e 管底腐食だけ", ks, cres_amps))
    rows.append(["e 管底腐食だけ"] + ["%.3f" % v for v in cres_amps])
    print("   %-24s " % "e 管底腐食だけ"
          + "  ".join("k=%d:%6.3f" % (k, v) for k, v in zip(ks, cres_amps)))
    print("   ★管底腐食の %.0f %% は k=1 に入っている"
          "(k=1 %.3f mm / 全成分の二乗和平方根 %.3f mm)。"
          % (100 * cres_amps[1] / np.sqrt(sum(v * v for v in cres_amps)),
             cres_amps[1], np.sqrt(sum(v * v for v in cres_amps))))

    figs.save_plot("spectrum", series, xlabel="角周波数 k [周期/回転]",
                   ylabel="振幅の z 平均 [mm]",
                   title="何が何周期に出るか(軸ずれと管底腐食は同じ k=1)")
    figs.save_table("spectrum_table",
                    ["条件"] + ["k=%d" % k for k in ks], rows,
                    title="角周波数ごとの振幅 [mm]")
    return {"cres_k1_share": cres_amps[1] / np.sqrt(sum(v * v for v in cres_amps)),
            "rows": rows}


# --------------------------------------------------------------------------- #
# 6. 補正の 4 段 —— 何を消すと何が消えるか                                      #
# --------------------------------------------------------------------------- #
EST = [
    ("E0 素朴(補正なし)", dict()),
    ("E1 毎スライス 1 周期除去", dict(k1="free")),
    ("E2 毎スライス円あてはめ", dict(k1="free", dc=True)),
    ("E3 軸を直線とみなす", dict(k1=1, k2=1)),
]


def section_correction() -> dict:
    print("\n" + "=" * 78)
    print("6) 補正 —— 軸ずれ %.1f mm・傾き %.1f 度・欠陥あり(条件 c)"
          % (4.0, 0.6))
    print("=" * 78)
    print("   推定器                     孔食   全周減肉  管底腐食   偽陽性   "
          "溶接高さ")

    sv = survey(FULL, offset=4.0, tilt_deg=0.6)
    tv = {k: true_volume(k) for k in ("pit", "band", "cres")}
    rows, maps, scs = [], [], []
    for name, kw in EST:
        m = correct(sv["dist"], **kw)
        sc = score(sv, m)
        scs.append(sc)
        maps.append(m)
        rows.append([name] + ["%.1f %%" % (100 * sc[k + "_rate"])
                              for k in ("pit", "band", "cres")]
                    + ["%.2f %%" % (100 * sc["false"]), "%.2f mm" % sc["weld_h"]])
        print("   %-26s %6.1f %% %7.1f %% %8.1f %% %8.2f %% %8.2f mm"
              % (name, 100 * sc["pit_rate"], 100 * sc["band_rate"],
                 100 * sc["cres_rate"], 100 * sc["false"], sc["weld_h"]))

    vrows = []
    print("\n   推定器                    孔食の体積      全周減肉の体積     "
          "管底腐食の体積   (真値との差)")
    for (name, _), sc in zip(EST, scs):
        cells = []
        for k in ("pit", "band", "cres"):
            cells.append("%.0f (%+.0f %%)" % (sc[k + "_vol"],
                                              100 * (sc[k + "_vol"] - tv[k]) / tv[k]))
        vrows.append([name] + cells)
        print("   %-26s %-16s %-18s %s" % (name, cells[0], cells[1], cells[2]))
    print("   %-26s %-16.0f %-18.0f %.0f  (真値 mm^3)"
          % ("", tv["pit"], tv["band"], tv["cres"]))

    print("\n  ★E1(毎スライス 1 周期除去)は偽陽性を %.2f → %.2f %% まで落とすが、"
          "\n     **管底腐食の検出率も %.1f → %.1f %% に落ちる** —— "
          "補正と本物が同じ k=1 に居るから。"
          % (100 * scs[0]["false"], 100 * scs[1]["false"],
             100 * scs[0]["cres_rate"], 100 * scs[1]["cres_rate"]))
    print("  ★E2(現場の定番。スライスごとに円をあてはめて残差を見る)は"
          "さらに\n     **全周減肉の検出率が %.1f → %.1f %%** に落ちる —— "
          "平均半径を捨てたから。"
          % (100 * scs[1]["band_rate"], 100 * scs[2]["band_rate"]))
    print("  ★E3(軸は直線だと**先に決めて** 1 周期の z 依存を 1 次に縛る)は"
          "\n     管底腐食 %.1f %% / 全周減肉 %.1f %% / 孔食 %.1f %% を残したまま"
          "偽陽性 %.2f %%。"
          % (100 * scs[3]["cres_rate"], 100 * scs[3]["band_rate"],
             100 * scs[3]["pit_rate"], 100 * scs[3]["false"]))

    # ★パネルごとに正規化されるので、**同じ範囲に切ってから**渡す
    #   (切らないと E0 だけ ±4 mm、他は ±1 mm で塗られて比べられない)。
    def _clip(a):
        return np.clip(a, -3.0, 3.0)

    figs.save_grid("map_corrected", [_clip(m) for m in maps],
                   [n for n, _ in EST], ncols=2, signed=True,
                   title="同じ測定を 4 通りに補正した減肉地図 [mm](±3 mm 共通尺度、"
                         "縦 = z、横 = θ)")
    truth = loss_parts(sv["z_hit"], sv["th_hit"], FULL)["total"]
    figs.save_grid("map_truth_vs_best",
                   [_clip(truth), _clip(maps[0]), _clip(maps[3])],
                   ["真の減肉 [mm]", "E0 素朴", "E3 軸を直線とみなす"], ncols=3,
                   signed=True, title="真値と、いちばん素朴な推定と、"
                                      "軸を直線に縛った推定(±3 mm 共通尺度)")
    figs.save_table("defect_table",
                    ["推定器", "孔食 検出率", "全周減肉 検出率", "管底腐食 検出率",
                     "偽陽性", "溶接ビード高さ"], rows,
                    title="欠陥の種類ごとの検出率(1 つの数字に畳まない)")
    figs.save_table("volume_table",
                    ["推定器", "孔食 [mm^3]", "全周減肉 [mm^3]", "管底腐食 [mm^3]"],
                    vrows + [["真値", "%.0f" % tv["pit"], "%.0f" % tv["band"],
                              "%.0f" % tv["cres"]]],
                    title="欠陥の種類ごとの体積(括弧内は真値との差)")
    return {"scs": scs, "tv": tv, "rows": rows}


# --------------------------------------------------------------------------- #
# 7. つまみ 1 本の崖 —— 軸のモデルの自由度                                      #
# --------------------------------------------------------------------------- #
def section_model_order() -> dict:
    print("\n" + "=" * 78)
    print("7) ★崖 —— 「軸をどこまで自由に動かしてよいか」の 1 本のつまみ")
    print("=" * 78)
    print("  1 周期の z 依存を n 次多項式に縛る。n=0 は剛体オフセット、"
          "n=1 は直線(傾き)、\n  n=2 は放物線(たわみ)、free は毎スライス自由。")
    print("   次数    偽陽性     管底腐食の検出率   管底腐食の体積   孔食の検出率")

    # 対照群 a: 減肉ゼロ。ただし**楕円化と曲がりは実物どおり残す** —— ここを
    # 真円・直線にすると次数 2 が要る理由(たわみ)が見えなくなる。
    s_clean = spec(pit=0.0, band=0.0, cres=0.0, weld=0.0)
    sv_c = survey(s_clean, offset=4.0, tilt_deg=0.6)
    sv = survey(FULL, offset=4.0, tilt_deg=0.6)             # 条件 c
    tvc = true_volume("cres")
    orders = [None, 0, 1, 2, 3, 5, 8, "free"]
    labels, false_a, cres_r, cres_v, pit_r = [], [], [], [], []
    for o in orders:
        kw = dict() if o is None else dict(k1=o, k2=1)
        m = correct(sv["dist"], **kw)
        sc = score(sv, m)
        mc = correct(sv_c["dist"], **kw)
        flc, _ = flag(mc)
        labels.append("なし" if o is None else str(o))
        false_a.append(100 * float(flc.mean()))
        cres_r.append(100 * sc["cres_rate"])
        cres_v.append(sc["cres_vol"])
        pit_r.append(100 * sc["pit_rate"])
        print("   %-6s %8.2f %% %14.1f %% %14.0f mm^3 %10.1f %%"
              % (labels[-1], false_a[-1], cres_r[-1], cres_v[-1], pit_r[-1]))
    print("   %-6s %8s %14s %14.0f mm^3 %10s" % ("真値", "0.00 %", "100.0 %",
                                                 tvc, "100.0 %"))

    x = np.arange(len(orders))
    figs.save_plot("sweep_model_order",
                   [("偽の減肉(欠陥ゼロの管)[%]", x, false_a),
                    ("管底腐食の検出率 [%]", x, cres_r),
                    ("孔食の検出率 [%]", x, pit_r)],
                   xlabel="1 周期の z 依存に許した多項式次数 "
                          "(0=平行移動 1=傾き 2=たわみ 7=毎スライス自由)",
                   ylabel="割合 [%]",
                   title="自由度を上げるほど偽物は消え、管底腐食も一緒に消える",
                   caption="孔食(局所)はどの次数でも残る —— 消えるのは"
                           "1 周期に載っている欠陥だけ。")
    return {"labels": labels, "false": false_a, "cres": cres_r, "pit": pit_r}


# --------------------------------------------------------------------------- #
# 8. E3 の崖 —— 管底腐食が管いっぱいに伸びると軸ずれと区別できない              #
# --------------------------------------------------------------------------- #
def section_cres_extent() -> dict:
    print("\n" + "=" * 78)
    print("8) ★E3 の崖 —— 管底腐食が長くなるほど「軸のずれ」に見える")
    print("=" * 78)
    print("   腐食の長さ   管長比    E3 の検出率   推定した最深部 [mm]  "
          "(真値 %.1f)" % CRES_D)

    spans, rate, depth = [], [], []
    for frac in (0.15, 0.30, 0.45, 0.60, 0.80, 1.00):
        half = frac * LZ / 2.0
        # 曲がりは止める —— たわみの残差(2 次)が管底に重なって、
        # 「長さの効き」と混ざるため(最初これを入れたまま測って取り違えた)。
        s = spec(pit=0.0, band=0.0, weld=0.0, bend=0.0,
                 cres_z=(LZ / 2 - half, LZ / 2 + half))
        sv = survey(s, offset=4.0, tilt_deg=0.6)
        m = correct(sv["dist"], k1=1, k2=1)
        sc = score(sv, m, s)
        parts = loss_parts(sv["z_hit"], sv["th_hit"], s)
        foot = parts["cres"] >= CRES_D * 0.8
        spans.append(2 * half)
        rate.append(100 * sc["cres_rate"])
        depth.append(float(np.median(m[foot])) if foot.any() else np.nan)
        print("   %6.0f mm   %5.2f     %8.1f %%      %8.2f mm"
              % (spans[-1], frac, rate[-1], depth[-1]))

    print("\n  ★腐食が管長の %.0f %% を覆うと、E3 は検出率 %.1f %%・"
          "最深部 %.2f mm(真値 %.1f mm)まで落ちる。"
          % (100, rate[-1], depth[-1], CRES_D))
    print("     **1 本の管の中で z によらず一定な腐食は、軸のずれと幾何的に"
          "区別できない**\n     —— 分けているのは「腐食は z で変わる」という"
          "仮定だけ。管を長く取るしかない。")

    figs.save_plot("sweep_cres_extent",
                   [("E3 の検出率 [%]", spans, rate),
                    ("推定した最深部 [mm] x 50", spans,
                     [d * 50 for d in depth]),
                    ("真の最深部 [mm] x 50", spans, [CRES_D * 50] * len(spans))],
                   xlabel="管底腐食が伸びている長さ [mm](管長 %.0f mm)" % LZ,
                   ylabel="検出率 [%] / 深さ x 50 [mm]",
                   title="腐食が管いっぱいに伸びると、補正がそれを軸ずれとして食う")
    return {"spans": spans, "rate": rate, "depth": depth}


# --------------------------------------------------------------------------- #
# 9. 2 次の効き —— 軸ずれは全周にも効く                                         #
# --------------------------------------------------------------------------- #
def section_dc_bias() -> dict:
    print("\n" + "=" * 78)
    print("9) 軸ずれは 1 周期だけではない —— 平均半径が 2 次で縮む")
    print("=" * 78)
    print("  幾何: 平均距離 = <sqrt(R² - e² sin²ψ) - e cosψ> ≈ R - e²/(4R)。")
    print("  つまり**軸がずれると管が細く見える** = 全周減肉を打ち消す向きに効く。")
    print("   オフセット   実測の平均のずれ   予測 -e²/4R   全周減肉 %.2f mm への影響"
          % BAND_D)

    offs = [0.0, 1.0, 2.0, 3.0, 4.0, 6.0, 8.0]
    meas, pred = [], []
    for e in offs:
        sv = survey(CLEAN, offset=e, noise=False)
        raw = _fill_theta(sv["dist"]) - R0
        meas.append(float(raw.mean()))
        pred.append(-e * e / (4 * R0))
        print("    %5.2f mm     %+8.4f mm      %+8.4f mm    %+7.1f %%"
              % (e, meas[-1], pred[-1], 100 * meas[-1] / BAND_D))
    err = max(abs(m - p) for m, p in zip(meas, pred))
    print("\n  ★予測と実測の差は最大 %.4f mm。オフセット %.0f mm で全周減肉 %.2f mm の"
          "%.0f %% を打ち消す。" % (err, offs[-2], BAND_D,
                                    abs(100 * meas[-2] / BAND_D)))
    figs.save_plot("dc_bias",
                   [("実測(平均半径のずれ)", offs, meas),
                    ("幾何の予測 -e²/4R", offs, pred)],
                   xlabel="センサ軸のオフセット [mm]",
                   ylabel="平均半径のずれ [mm]",
                   title="軸ずれの 2 次の効き —— 管が細く見えて全周減肉を隠す")
    return {"offs": offs, "meas": meas, "pred": pred, "err": err}


# --------------------------------------------------------------------------- #
# 10. 道具の穴                                                                  #
# --------------------------------------------------------------------------- #
def section_tool_gaps() -> None:
    print("\n" + "=" * 78)
    print("10) 道具の穴(この PoC で使ってみて)")
    print("=" * 78)
    import inspect

    sig = inspect.signature(fs.ledger.cylinder_unwrap.__wrapped__
                            if hasattr(fs.ledger.cylinder_unwrap, "__wrapped__")
                            else fs.ledger.cylinder_unwrap)
    assert "center" in str(sig), str(sig)
    print("  (a) cylinder_unwrap の center は **z によらず 1 つ**。"
          "曲がった管や\n      斜めに走ったセンサには追随できない"
          "(この PoC の主題そのもの)。")

    assert not hasattr(fs.ledger, "fit_cylinder")
    assert hasattr(fs.ledger, "ransac_cylinder")
    print("  (b) 円筒の当てはめは ransac_cylinder(点法線が要る)だけ。"
          "**距離画像\n      から軸を直接最小二乗で出す口が無い**"
          "(展開図の前段でいちばん要る処理)。")

    assert not any(hasattr(fs.ledger, n) for n in
                   ("angular_harmonics", "harmonic_fit", "circular_fft"))
    print("  (c) 周方向のフーリエ係数(k 周期の振幅と位相)を出す op が無い。"
          "\n      展開図の仕事はほぼこれなので、族に入れる価値がある。")

    m = np.zeros((20, 40), bool)
    m[5:10, 38:] = True
    m[5:10, :3] = True
    lab = np.asarray(_L.blob_label(m))
    assert int(lab.max()) == 2, int(lab.max())
    print("  (d) 展開図は θ で周期なのに blob_label は左右の端をつながない"
          "(継ぎ目を\n      またぐ 1 つの腐食が 2 個に数えられる。実測: "
          "%d 個)。この PoC は継ぎ目を\n      避けて欠陥を置いてある。"
          % int(lab.max()))

    z = np.zeros((4, 4, 4, 3))
    try:
        _L.cylinder_sdf(z, (0, 0, 0), (1, 0, 0), 2.0, 4.0)
        ok = True
    except Exception:                                     # noqa: BLE001
        ok = False
    assert ok
    print("  (e) cylinder_sdf は**直線・真円**のみ。楕円化・曲がり・欠陥を"
          "入れた管の\n      SDF は自前(numpy)で組んだ。"
          "sdf_subtract / sdf_to_occupancy は使えた。")


# --------------------------------------------------------------------------- #
def main() -> int:
    t0 = time.perf_counter()
    print("=" * 78)
    print("配管内面の減肉を展開図で測る —— 軸を決める段が、管底の腐食を食う")
    print("内径 %.0f mm / 肉厚 %.1f mm / 管長 %.0f mm / 展開図 %d x %d "
          "(z x θ) / しきい値 %.1f mm"
          % (2 * R0, T0, LZ, NZ, NTH, THRESH))
    print("=" * 78)

    sc1 = section_scene()
    sc2 = section_zero_point()
    sw = section_offset_sweep()
    tl = section_tilt_sweep()
    sp = section_spectrum()
    co = section_correction()
    mo = section_model_order()
    ce = section_cres_extent()
    dc = section_dc_bias()
    section_tool_gaps()

    print("\n" + "=" * 78)
    print("まとめ")
    print("=" * 78)
    print("  * 軸が %.1f mm ずれると、腐食ゼロの管の %.1f %% に減肉の旗が立つ"
          "(幾何の予測との差 %.2f ポイント)。" % (4.0, sw["meas"][8], sw["err"]))
    print("  * 1 周期を消せば偽物は消えるが、管底腐食の %.0f %% も k=1 に居るので"
          "一緒に消える(検出率 %.1f → %.1f %%)。"
          % (100 * sp["cres_k1_share"], 100 * co["scs"][0]["cres_rate"],
             100 * co["scs"][1]["cres_rate"]))
    print("  * 軸を直線と**先に決める**と両方残る(管底腐食 %.1f %%・"
          "偽陽性 %.2f %%)。ただし腐食が管長いっぱいだと %.1f %% まで落ちる。"
          % (100 * co["scs"][3]["cres_rate"], 100 * co["scs"][3]["false"],
             ce["rate"][-1]))
    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))

    # --- 所見を固定する(壊れたら鳴る)---
    assert sw["err"] < 3.0, sw["err"]
    assert sw["meas"][0] < 0.5 and sw["meas"][8] > 20.0, sw["meas"]
    assert sp["cres_k1_share"] > 0.6, sp["cres_k1_share"]
    assert co["scs"][1]["cres_rate"] < 0.5 * co["scs"][0]["cres_rate"]
    assert co["scs"][2]["band_rate"] < 0.5 * co["scs"][1]["band_rate"]
    assert co["scs"][3]["cres_rate"] > 0.5 and co["scs"][3]["band_rate"] > 0.5
    assert ce["rate"][-1] < ce["rate"][0]
    assert dc["err"] < 0.02, dc["err"]
    assert sc1["v_pit"] > 0

    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
