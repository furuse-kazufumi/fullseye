# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""ダイの傾きと TSV の位置ずれを 1 つの CT から分ける —— 傾きは並進を偽装し、回転も偽装する。

3 次元積層(ハイブリッドボンディング / TSV 積層)の受け入れ検査です。上下 2 枚の
ダイを貼り合わせたら、貫通ビア(TSV)どうしが合っているかを確かめないといけません。
測る量は 2 つ: **ダイの傾き(tilt)**と **上下の位置ずれ(overlay)**。X 線 CT を
1 回撮れば両方入っているのですが、**傾きがあると位置ずれが見かけ上大きくなります**。
上のダイを上面から見ると、ビアの開口はダイ厚 × 傾きの分だけ横へ動いて見えるからです。
どれだけ偽装されるか、どう外せば良いか、外し切れないものは何かを測ります。

EXTEND: 実測の CT に差し替えるなら :func:`make_volume` が返す ``vol``
(``(nz, ny, nx)`` の減弱値、1 ボクセル = ``VOX_UM``)を再構成ボリュームに
置き換えます。真値の ``tilt``/``overlay`` は実測では手に入らないので、
**傾きゼロで貼った参照試料**か、断面 SEM の実測を真値に使います。
「設計値どおりに置かれている」は真値にできません —— それを測るのがこの検査です。

この PoC が示すこと(数字はいずれも実行時に印字される実測値):

1. **ゼロ点(上面のビア開口の重心差をそのまま位置ずれと呼ぶ)を先に測る**。
   真の位置ずれ (+0.800, −0.450) µm に対し、傾き (α, β) = (1.20°, 0.70°) の
   ダイでは **(+2.023, −2.545) µm**、誤差の大きさ **2.147 µm** —— 仕様
   ±1.0 µm の **2.1 倍**。真の位置ずれ 0.918 µm より**偽装のほうが大きい**。
2. **偽装量は閉形式で予測できる**。上面の開口は「ダイ厚 L × 上面法線の横成分」
   だけ動く: 予測 (+1.222, −2.094) µm、実測 (+1.223, −2.095) µm、
   **比 1.0004 / 1.0004**。ここで L も法線も**同じ CT から測る**(ビアの
   3 次元直線当てはめ)ので、外部の設計値は要りません。
3. **ビアの軸で下面へ引き直すと並進は直る**。補正後 (+0.800, −0.450) µm、
   誤差 **0.0011 µm** —— **ゼロ点の 1/1900**。
4. ★★**予想が外れた —— 傾きは回転も偽装する**。「傾きは並進と倍率だけを偽装し、
   回転は投影の対称変形なので偽装しない」と踏んでいたが**間違い**。2 軸の傾きの
   合成 Rx(α)Ry(β) の上 2×2 は **sinα·sinβ のせん断項**を持ち、その反対称成分が
   偽の回転になる: 予測 **−0.00733°**、実測 **−0.00734°**。真の回転 +0.01500° に
   対して **49 %** の大きさで、しかも**軸で下面へ引き直しても消えない**
   (所見 3 の補正は並進しか直さない)。
5. **消すには測った傾きで逆投影する**。法線から (α, β) を解いて上 2×2 の逆行列を
   掛けると回転は **+0.01500°**(真値 +0.01500°、誤差 0.00001°)に戻る。
   段は 3 つ: 素 → 軸補正(並進が直る)→ 逆投影(回転も直る)。
6. ★**倍率も偽装される**。傾きは格子を cos だけ縮める: 予測 **−147 ppm**、
   実測 −149 ppm。逆投影後は −2 ppm。360 µm の格子で 0.05 µm なので
   位置ずれの仕様には効かないが、**「倍率が合わない = 熱膨張の差」と読むと誤診**。
7. **崖は幾何で予測できる**。ゼロ点の誤差は L·sin(傾き) なので、仕様 ±1.0 µm を
   超えるのは 傾き = asin(1.0/L) = **0.573°** と予測 —— 掃引の実測は **0.574°**
   (比 **1.002**)。**傾き 0.6° を許すなら、上面だけを見た位置ずれ検査は
   1 µm 仕様に対して原理的に不合格**。補正後は 2.0° まで誤差 0.005 µm 以下。
8. **対照群(傾き 0)**では素と補正の差が **0.0004 µm**、どちらも真値を
   0.0016 µm 以内で当てる。壊していたのは当てはめでも雑音でもなく**傾き**。

【グラウンドトゥルース】下ダイ(厚 100 µm)に 7×7 の TSV(半径 6 µm、ピッチ
60 µm)、上ダイに同じ格子を **(+0.800, −0.450) µm 並進 + 0.01500° 回転**して配置し、
上ダイ全体を接合面を軸に Rx(1.20°)Ry(0.70°) 傾ける。Si 0.30 / Cu 1.00 の減弱値で
部分体積を含めて描き、雑音 σ 0.015 を足した (89, 176, 176) のボリューム 1 個が
測定のすべて。真値はこの仕込みそのもの。

来歴(公開文献のみ): Kabsch, *Acta Cryst.* A32 (1976) 922 —— 対応点からの剛体/相似
当てはめ / Gower, *Psychometrika* 40 (1975) 33 —— Procrustes 解析 / Beyne,
*Proc. IEEE* 105 (2017) 2288 —— 3-D 積層と TSV の概観。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

# --- 場面の諸元 -------------------------------------------------------------- #
VOX_UM = 2.5            # ボクセル [µm]
FIELD_UM = 440.0        # 視野の一辺 [µm]
MARGIN_UM = 10.0        # 上下の空気 [µm]
NG = 7                  # TSV の並び NG x NG = 49 本/層
PITCH_UM = 60.0         # TSV ピッチ [µm]
R_TSV_UM = 6.0          # TSV 半径 [µm]
H_DIE_UM = 100.0        # ダイ厚 = TSV の長さ [µm]
GAP_UM = 20.0           # 接合層の厚み [µm]。★傾き 2° で格子の端が 10 µm 下がるので、
#                         これより薄いと隅で上下の Cu がくっついて連結成分が 98 -> 96 に減る
#                         (最初 6 µm で踏んだ。物理でなく計測の都合で決まる下限)。
DIE_HALF_UM = 210.0     # ダイの半幅 [µm]
MU_SI, MU_CU = 0.30, 1.00   # 減弱値(Si / Cu)
NOISE = 0.015           # CT の雑音 1σ(減弱値)
CU_THR = 0.65           # Cu を切るしきい値(Si と Cu のちょうど中間 = 幾何境界)

DX_UM, DY_UM = 0.800, -0.450    # 真の位置ずれ(並進)
THETA_DEG = 0.01500             # 真の位置ずれ(回転)
TILT_A_DEG, TILT_B_DEG = 1.20, 0.70   # 上ダイの傾き(x 軸まわり / y 軸まわり)
SPEC_UM = 1.0           # 位置ずれの仕様 [µm]
SEED = 3

_L = fs.ledger


# --------------------------------------------------------------------------- #
# 幾何 —— 上ダイの姿勢は 1 つの回転行列で決まる                                  #
# --------------------------------------------------------------------------- #
def tilt_matrix(a_deg: float, b_deg: float) -> np.ndarray:
    """``Rx(α) @ Ry(β)`` を (X, Y, Z) 順で返す。第 3 列 = 上面の法線。"""
    a, b = np.deg2rad(a_deg), np.deg2rad(b_deg)
    rx = np.array([[1, 0, 0], [0, np.cos(a), -np.sin(a)], [0, np.sin(a), np.cos(a)]])
    ry = np.array([[np.cos(b), 0, np.sin(b)], [0, 1, 0], [-np.sin(b), 0, np.cos(b)]])
    return rx @ ry


def make_volume(a_deg: float = TILT_A_DEG, b_deg: float = TILT_B_DEG,
                dx: float = DX_UM, dy: float = DY_UM, theta_deg: float = THETA_DEG,
                h_die: float = H_DIE_UM, seed: int = SEED) -> dict:
    """CT ボリューム 1 個と、その真値を返す。**これ 1 個が測定のすべて**。

    上ダイは接合面(下ダイの上面 + 接合層)を回転中心に傾ける —— 接合層が
    くさび形になるのが実際の傾きの原因なので、回転中心はダイの重心ではなく底面。
    """
    rng = np.random.default_rng(seed)
    nx = ny = int(round(FIELD_UM / VOX_UM))
    z0, z1 = -MARGIN_UM, h_die + GAP_UM + h_die + MARGIN_UM
    nz = int(round((z1 - z0) / VOX_UM))
    zs = z0 + VOX_UM * np.arange(nz)

    gx = VOX_UM * (np.arange(nx) - (nx - 1) / 2.0)
    gy = VOX_UM * (np.arange(ny) - (ny - 1) / 2.0)
    yy, xx = np.meshgrid(gy, gx, indexing="ij")

    ext_lat = (NG - 1) / 2.0 * PITCH_UM + R_TSV_UM     # 格子の広がり

    def via_frac(u, v):
        """周期格子までの距離から部分体積の充填率(格子の外は 0)。"""
        du = u - PITCH_UM * np.round(u / PITCH_UM)
        dv = v - PITCH_UM * np.round(v / PITCH_UM)
        d = np.hypot(du, dv)
        inside = (np.abs(u) <= ext_lat) & (np.abs(v) <= ext_lat)
        return np.clip(0.5 + (R_TSV_UM - d) / VOX_UM, 0.0, 1.0) * inside

    # 下ダイ(傾いていないので z に依らない)
    bot_die = ((np.abs(xx) <= DIE_HALF_UM) & (np.abs(yy) <= DIE_HALF_UM)).astype(float)
    bot_via = via_frac(xx, yy) * bot_die

    rot = tilt_matrix(a_deg, b_deg)
    zp = h_die + GAP_UM                       # 上ダイの底面(回転中心)の高さ
    th = np.deg2rad(theta_deg)
    ct, st = np.cos(th), np.sin(th)

    vol = np.empty((nz, ny, nx), np.float32)
    for k, z in enumerate(zs):
        # 下ダイ: z 方向だけ部分体積で柔らかく
        fz = (np.clip(0.5 + z / VOX_UM, 0, 1)
              * np.clip(0.5 + (h_die - z) / VOX_UM, 0, 1))
        s = fz * (MU_SI * bot_die + (MU_CU - MU_SI) * bot_via)

        # 上ダイ: 大域座標 -> ダイ座標(回転の転置)
        zr = z - zp
        u = rot[0, 0] * xx + rot[1, 0] * yy + rot[2, 0] * zr
        v = rot[0, 1] * xx + rot[1, 1] * yy + rot[2, 1] * zr
        w = rot[0, 2] * xx + rot[1, 2] * yy + rot[2, 2] * zr
        fw = (np.clip(0.5 + w / VOX_UM, 0, 1)
              * np.clip(0.5 + (h_die - w) / VOX_UM, 0, 1))
        die = ((np.abs(u) <= DIE_HALF_UM) & (np.abs(v) <= DIE_HALF_UM)).astype(float)
        # ビアの格子はダイ座標で「並進 dx,dy + 回転 θ」だけずらして置く
        uu, vv = u - dx, v - dy
        s = s + fw * die * (MU_SI + (MU_CU - MU_SI)
                            * via_frac(ct * uu + st * vv, -st * uu + ct * vv))
        vol[k] = s

    vol += (NOISE * rng.standard_normal(vol.shape)).astype(np.float32)

    # 真値: 上面の法線の横成分 x ダイ厚 = 見かけの並進(閉形式)
    normal = rot[:, 2]
    return {"vol": vol, "zs": zs, "gx": gx, "gy": gy, "rot": rot,
            "normal": normal, "h_die": h_die,
            "overlay": np.array([dx, dy]), "theta_deg": theta_deg,
            "bias_pred": h_die * normal[:2],
            "tilt_deg": (a_deg, b_deg)}


# --------------------------------------------------------------------------- #
# 計測 —— ビア 1 本ごとに (中心, 向き, 長さ)。ここが公開経路の穴の集まり           #
# --------------------------------------------------------------------------- #
def measure_vias(sc: dict) -> dict:
    """CT から TSV を 1 本ずつ取り出し、軸と長さを測る。

    段取り: ``vol_label`` で Cu を連結成分に分ける -> 各成分の**スライスごとの
    gray 重心**(自前。台帳に gray 重み付き重心が無い)-> その点列に
    ``fit_line3`` で 3 次元直線を当てる -> 軸方向の分散から長さ
    ``L = sqrt(12·Var)``(一様な棒の閉形式)。
    """
    vol = sc["vol"]
    # ★台帳経由の vol_label は docstring と違って **labels だけ**を返す
    #   (``(labels, n)`` の n が落ちている。節 9 の (f))。
    lab = np.asarray(_L.vol_label(vol > CU_THR, connectivity=6))
    n = int(lab.max())
    idx = np.nonzero(lab)
    lid = lab[idx]
    wgt = np.clip(vol[idx].astype(np.float64) - MU_SI, 0.0, MU_CU - MU_SI)
    zc = sc["zs"][idx[0]]
    yc = sc["gy"][idx[1]]
    xc = sc["gx"][idx[2]]

    # スライス(label, z index)ごとの gray 重心 —— サブボクセルの点列を作る
    key = lid.astype(np.int64) * vol.shape[0] + idx[0]
    sw = np.bincount(key, weights=wgt)
    sy = np.bincount(key, weights=wgt * yc)
    sx = np.bincount(key, weights=wgt * xc)
    sz = np.bincount(key, weights=wgt * zc)
    ok = sw > 1e-9

    out = []
    for j in range(1, n + 1):
        k0, k1 = j * vol.shape[0], (j + 1) * vol.shape[0]
        m = ok[k0:k1]
        if int(m.sum()) < 5:
            continue
        pz = sz[k0:k1][m] / sw[k0:k1][m]
        py = sy[k0:k1][m] / sw[k0:k1][m]
        px = sx[k0:k1][m] / sw[k0:k1][m]
        line = _L.fit_line3(np.column_stack([pz, py, px]))
        d = np.asarray(line["direction"], float)          # (dz, dy, dx)
        if d[0] < 0:
            d = -d
        c = np.asarray(line["center"], float)[:3]
        # 長さ: 軸に沿った座標の分散から(一様な棒なら Var = L^2/12)
        sel = lid == j
        t = ((zc[sel] - c[0]) * d[0] + (yc[sel] - c[1]) * d[1]
             + (xc[sel] - c[2]) * d[2])
        w = wgt[sel]
        mt = float((w * t).sum() / w.sum())
        var = float((w * (t - mt) ** 2).sum() / w.sum())
        length = float(np.sqrt(12.0 * var))
        cz = c[0] + mt * d[0]
        cy = c[1] + mt * d[1]
        cx = c[2] + mt * d[2]
        out.append((cz, cy, cx, d[0], d[1], d[2], length))

    a = np.asarray(out, float)
    assert a.shape[0] == 2 * NG * NG, (a.shape, n)
    z_split = sc["h_die"] + GAP_UM / 2.0
    lower = a[a[:, 0] < z_split]
    upper = a[a[:, 0] >= z_split]
    return {"lower": lower, "upper": upper, "n_label": n}


def face_xy(v: np.ndarray, sign: float) -> np.ndarray:
    """ビアの端面(``sign=+1`` 上面 / ``-1`` 下面)の中心 (x, y)。"""
    half = sign * v[:, 6] / 2.0            # 列: cz cy cx dz dy dx L
    return np.column_stack([v[:, 2] + half * v[:, 5], v[:, 1] + half * v[:, 4]])


def pair(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """b の各点に最も近い a の点の添字(格子の対応づけ)。"""
    d = np.hypot(a[:, 0][:, None] - b[:, 0][None, :], a[:, 1][:, None] - b[:, 1][None, :])
    i = np.argmin(d, axis=0)
    assert len(set(i.tolist())) == b.shape[0], "1 対 1 で対応しない"
    return i


def similarity(src: np.ndarray, dst: np.ndarray) -> dict:
    """2-D の相似変換を ``procrustes_fit``(z=0 の平面点群)で解く。"""
    s3 = np.column_stack([src, np.zeros(len(src))])
    d3 = np.column_stack([dst, np.zeros(len(dst))])
    m = np.asarray(_L.procrustes_fit(s3, d3, scaling=True), float)
    a = m[:2, :2]
    scale = float(np.sqrt(abs(np.linalg.det(a))))
    return {"t": m[:2, 3].copy(),
            "theta_deg": float(np.rad2deg(np.arctan2(a[1, 0], a[0, 0]))),
            "scale_ppm": (scale - 1.0) * 1e6}


def estimators(sc: dict, mv: dict) -> dict:
    """3 段の推定器: 素(上面) / 軸で下面へ / 測った傾きで逆投影。"""
    lo, up = mv["lower"], mv["upper"]
    ref = face_xy(lo, +1.0)                  # 下ダイの上面 = 接合面のパッド
    top = face_xy(up, +1.0)                  # 上ダイの上面(見えている側)
    bot = face_xy(up, -1.0)                  # 上ダイの下面 = 本当のパッド面
    i = pair(ref, top)
    ref_o, top_o, bot_o = ref[i], top, bot

    # 測った姿勢: 49 本のビアの向きの平均 = 上面の法線
    d = up[:, 3:6].mean(axis=0)
    d = d / np.linalg.norm(d)
    n_meas = np.array([d[2], d[1], d[0]])    # (dz,dy,dx) -> (X,Y,Z)
    b_meas = np.arcsin(np.clip(n_meas[0], -1, 1))
    a_meas = np.arctan2(-n_meas[1], n_meas[2])
    m2 = tilt_matrix(np.rad2deg(a_meas), np.rad2deg(b_meas))[:2, :2]
    deproj = bot_o @ np.linalg.inv(m2).T     # 逆投影(前縮みとせん断を戻す)

    return {"ref": ref_o, "top": top_o, "bot": bot_o, "deproj": deproj,
            "length": float(up[:, 6].mean()),
            "tilt_meas_deg": (float(np.rad2deg(a_meas)), float(np.rad2deg(b_meas))),
            "normal_meas": n_meas,
            "raw": similarity(ref_o, top_o),
            "axis": similarity(ref_o, bot_o),
            "deprojected": similarity(ref_o, deproj)}


# --------------------------------------------------------------------------- #
# 1-3. ゼロ点・予測・補正                                                        #
# --------------------------------------------------------------------------- #
def section_bias() -> dict:
    print("\n" + "=" * 78)
    print("1-3) ゼロ点(上面の重心差)/ 偽装量の閉形式予測 / 軸による補正")
    print("=" * 78)

    sc = make_volume()
    mv = measure_vias(sc)
    es = estimators(sc, mv)
    print("  CT %s(%.1f µm/vox)-> Cu の連結成分 %d 個(TSV %d 本 x 2 層)"
          % (sc["vol"].shape, VOX_UM, mv["n_label"], NG * NG))
    print("  測った ダイ厚 %.3f µm(真値 %.1f)/ 傾き (%.4f°, %.4f°)(真値 (%.2f°, %.2f°))"
          % (es["length"], sc["h_die"], es["tilt_meas_deg"][0], es["tilt_meas_deg"][1],
             *sc["tilt_deg"]))

    tru = sc["overlay"]
    raw_t, ax_t = es["raw"]["t"], es["axis"]["t"]
    bias_meas = raw_t - ax_t
    bias_pred = sc["bias_pred"]
    e_raw = float(np.hypot(*(raw_t - tru)))
    e_ax = float(np.hypot(*(ax_t - tru)))
    print("\n            並進 x [µm]  並進 y [µm]   真値からの誤差")
    print("   真値      %+9.4f   %+9.4f          -" % (tru[0], tru[1]))
    print("   ゼロ点    %+9.4f   %+9.4f     %8.4f µm  (仕様 ±%.1f の %.1f 倍)"
          % (raw_t[0], raw_t[1], e_raw, SPEC_UM, e_raw / SPEC_UM))
    print("   軸で補正  %+9.4f   %+9.4f     %8.4f µm" % (ax_t[0], ax_t[1], e_ax))
    print("\n  偽装量 = ダイ厚 x 法線の横成分: 予測 (%+.4f, %+.4f) / 実測 (%+.4f, %+.4f) µm"
          "  比 %.4f / %.4f"
          % (bias_pred[0], bias_pred[1], bias_meas[0], bias_meas[1],
             bias_meas[0] / bias_pred[0], bias_meas[1] / bias_pred[1]))
    print("  -> ゼロ点の誤差 %.4f µm は、真の位置ずれ %.4f µm より**大きい**。"
          % (e_raw, float(np.hypot(*tru))))
    print("  -> 軸で下面へ引き直すと誤差 %.4f µm = ゼロ点の 1/%.0f。"
          % (e_ax, e_raw / e_ax))

    assert e_raw > 1.5 and e_ax < 0.02, (e_raw, e_ax)
    assert 0.99 < bias_meas[0] / bias_pred[0] < 1.01, bias_meas / bias_pred
    assert 0.99 < bias_meas[1] / bias_pred[1] < 1.01, bias_meas / bias_pred

    # --- 図: 場面 ---------------------------------------------------------- #
    vol = sc["vol"]
    kz_top = int(np.argmin(np.abs(sc["zs"] - (sc["h_die"] + GAP_UM + sc["h_die"] - 3))))
    kz_bot = int(np.argmin(np.abs(sc["zs"] - (sc["h_die"] - 3))))
    figs.save_grid(
        "scene",
        [vol[kz_bot], vol[kz_top], vol[:, vol.shape[1] // 2, :],
         np.asarray(_L.vol_label(vol > CU_THR, connectivity=6))[kz_top] > 0],
        ["下ダイの上面近く(z = %.0f µm)" % sc["zs"][kz_bot],
         "上ダイの上面近く(z = %.0f µm)" % sc["zs"][kz_top],
         "縦断面(y = 0)—— 上ダイが %.2f° 傾いている" % sc["tilt_deg"][0],
         "Cu のしきい値 %.2f で切った上ダイの開口" % CU_THR],
        title="測定は CT ボリューム 1 個(%d x %d x %d、%.1f µm/vox)"
              % (vol.shape + (VOX_UM,)), ncols=2)

    # --- 図: ビアごとの位置ずれ(散布)------------------------------------- #
    dtop = es["top"] - es["ref"]
    dbot = es["bot"] - es["ref"]
    figs.save_plot(
        "overlay_scatter",
        [("ゼロ点: 上面の開口", dtop[:, 0], dtop[:, 1]),
         ("軸で下面へ引き直す", dbot[:, 0], dbot[:, 1]),
         ("真の位置ずれ", [tru[0]], [tru[1]])],
        xlabel="Δx [µm]", ylabel="Δy [µm]",
        title="TSV %d 本ぶんの位置ずれ(傾き %.2f°, %.2f°)"
              % (NG * NG, *sc["tilt_deg"]),
        caption="雲ごと %.2f µm ずれるのが傾きの偽装。散らばりの広がりは測定精度。"
                % float(np.hypot(*bias_meas)),
        kinds=["scatter", "scatter", "scatter"])
    return {"sc": sc, "mv": mv, "es": es, "e_raw": e_raw, "e_ax": e_ax,
            "bias_pred": bias_pred, "bias_meas": bias_meas}


# --------------------------------------------------------------------------- #
# 4-6. 回転と倍率 —— 予想が外れたところ                                          #
# --------------------------------------------------------------------------- #
def section_rotation(prev: dict) -> dict:
    print("\n" + "=" * 78)
    print("4-6) ★★予想が外れた —— 傾きは回転も倍率も偽装する")
    print("=" * 78)

    sc, es = prev["sc"], prev["es"]
    a, b = np.deg2rad(sc["tilt_deg"][0]), np.deg2rad(sc["tilt_deg"][1])
    m = sc["rot"][:2, :2]
    rot_pred = np.rad2deg(0.5 * (m[1, 0] - m[0, 1]))       # 反対称成分 = 偽の回転
    scale_pred = (np.sqrt(abs(np.linalg.det(m))) - 1.0) * 1e6

    rows = []
    print("\n   推定器           並進誤差 [µm]   回転 [deg]      倍率 [ppm]")
    for name, key in (("ゼロ点(上面)", "raw"), ("軸で下面へ", "axis"),
                      ("測った傾きで逆投影", "deprojected")):
        r = es[key]
        et = float(np.hypot(*(r["t"] - sc["overlay"])))
        rows.append([name, "%.4f" % et, "%+.5f" % r["theta_deg"],
                     "%+.1f" % r["scale_ppm"]])
        print("   %-18s %10.4f   %+12.5f   %+10.1f" % (name, et, r["theta_deg"],
                                                       r["scale_ppm"]))
    print("   %-18s %10s   %+12.5f   %+10.1f" % ("真値", "-", sc["theta_deg"], 0.0))
    rows.append(["真値", "-", "%+.5f" % sc["theta_deg"], "+0.0"])

    got_rot = es["axis"]["theta_deg"] - sc["theta_deg"]
    print("\n  ★予想「傾きは回転を偽装しない(投影は対称変形だから)」は**外れ**。")
    print("     Rx(α)Ry(β) の上 2x2 = [[cosβ, 0], [sinα sinβ, cosα]] は"
          " **sinα·sinβ のせん断**を持ち、")
    print("     その反対称成分 -sinα·sinβ/2 が偽の回転になる: 予測 %+.5f° / 実測 %+.5f°"
          "(比 %.3f)。" % (rot_pred, got_rot, got_rot / rot_pred))
    print("     真の回転 %+.5f° に対して %.0f %% の大きさで、**軸で下面へ引き直しても"
          "消えない**。" % (sc["theta_deg"], 100 * abs(got_rot / sc["theta_deg"])))
    print("  倍率も偽装される: 予測 %+.1f ppm / 実測 %+.1f ppm。"
          % (scale_pred, es["axis"]["scale_ppm"]))
    print("  ★逆投影(法線から α, β を解いて上 2x2 の逆行列を掛ける)で"
          "回転 %+.5f°(真値 %+.5f°、誤差 %.5f°)/ 倍率 %+.1f ppm まで戻る。"
          % (es["deprojected"]["theta_deg"], sc["theta_deg"],
             abs(es["deprojected"]["theta_deg"] - sc["theta_deg"]),
             es["deprojected"]["scale_ppm"]))

    assert abs(got_rot / rot_pred - 1.0) < 0.05, (got_rot, rot_pred)
    assert abs(es["deprojected"]["theta_deg"] - sc["theta_deg"]) < 0.002
    assert abs(es["deprojected"]["scale_ppm"]) < 40.0, es["deprojected"]["scale_ppm"]

    figs.save_table("estimator_table",
                    ["推定器", "並進誤差 µm", "回転 deg", "倍率 ppm"], rows,
                    title="3 段の推定器 —— 並進だけ直しても回転は残る",
                    caption="偽の回転の予測 -sinα sinβ/2 = %+.5f°、倍率の予測"
                            " %+.1f ppm。逆投影で両方が戻る。"
                            % (rot_pred, scale_pred))
    return {"rot_pred": rot_pred, "rot_meas": got_rot, "scale_pred": scale_pred}


# --------------------------------------------------------------------------- #
# 7-8. 崖の掃引 と 対照群                                                        #
# --------------------------------------------------------------------------- #
def section_sweep() -> dict:
    print("\n" + "=" * 78)
    print("7-8) 崖 —— 傾きを何度まで許せるか(先に幾何で予測)と 対照群")
    print("=" * 78)

    pred_deg = float(np.rad2deg(np.arcsin(SPEC_UM / H_DIE_UM)))
    print("  予測: ゼロ点の誤差 = ダイ厚 x sin(傾き) なので、仕様 ±%.1f µm を"
          "超えるのは %.3f°。" % (SPEC_UM, pred_deg))

    tilts = [0.0, 0.2, 0.4, 0.6, 1.0, 1.4, 2.0]
    e_raw, e_ax, rot_err = [], [], []
    print("\n   傾き [deg]   ゼロ点の誤差 [µm]   軸補正後 [µm]   回転の誤差 [deg]")
    for t in tilts:
        sc = make_volume(a_deg=t, b_deg=0.6 * t)
        es = estimators(sc, measure_vias(sc))
        e_raw.append(float(np.hypot(*(es["raw"]["t"] - sc["overlay"]))))
        e_ax.append(float(np.hypot(*(es["axis"]["t"] - sc["overlay"]))))
        rot_err.append(abs(es["axis"]["theta_deg"] - sc["theta_deg"]))
        print("    %5.2f         %9.4f         %9.4f        %9.5f"
              % (t, e_raw[-1], e_ax[-1], rot_err[-1]))

    # 崖: ゼロ点の誤差が仕様を超える傾き(掃引を線形補間)
    got = float("nan")
    for i in range(1, len(tilts)):
        if e_raw[i - 1] < SPEC_UM <= e_raw[i]:
            f = (SPEC_UM - e_raw[i - 1]) / (e_raw[i] - e_raw[i - 1])
            got = tilts[i - 1] + f * (tilts[i] - tilts[i - 1])
            break
    print("\n  崖(実測 / 予測): %.3f / %.3f°(比 %.3f)。"
          % (got, pred_deg, got / pred_deg))
    print("  補正後は 2.0° でも誤差 %.4f µm。**傾きを止めるのではなく、"
          "測って外すほうが安い**。" % e_ax[-1])
    print("\n  対照群(傾き 0): ゼロ点 %.4f µm / 軸補正 %.4f µm、差 %.4f µm。"
          "壊していたのは傾きだった。"
          % (e_raw[0], e_ax[0], abs(e_raw[0] - e_ax[0])))

    assert 0.8 < got / pred_deg < 1.25, (got, pred_deg)
    assert e_raw[0] < 0.01 and e_ax[0] < 0.01, (e_raw[0], e_ax[0])
    assert e_ax[-1] < 0.02, e_ax[-1]

    figs.save_plot("tilt_cliff",
                   [("ゼロ点(上面)", tilts, e_raw),
                    ("軸で下面へ", tilts, e_ax),
                    ("仕様 %.1f µm" % SPEC_UM, [tilts[0], tilts[-1]],
                     [SPEC_UM, SPEC_UM]),
                    ("予測 L sin(傾き)", tilts,
                     [H_DIE_UM * np.sin(np.deg2rad(np.hypot(t, 0.6 * t)))
                      for t in tilts])],
                   xlabel="傾き α [deg](β = 0.6α)", ylabel="位置ずれの誤差 [µm]",
                   title="崖は幾何どおり(実測 %.3f° / 予測 %.3f°)" % (got, pred_deg),
                   caption="ゼロ点の誤差はダイ厚 x sin(傾き)。軸で下面へ引き直すと"
                           "2° でも %.4f µm。" % e_ax[-1])
    figs.save_plot("rotation_vs_tilt",
                   [("軸補正後に残る回転の誤差", tilts, rot_err),
                    ("予測 |sinα sinβ|/2", tilts,
                     [abs(np.rad2deg(0.5 * np.sin(np.deg2rad(t))
                                     * np.sin(np.deg2rad(0.6 * t)))) for t in tilts])],
                   xlabel="傾き α [deg]", ylabel="回転の誤差 [deg]",
                   title="並進を直しても回転は残る(せん断は 2 次で効く)",
                   caption="真の回転 %.5f° を超えるのは α ≈ 1.2°。" % THETA_DEG)
    return {"tilts": tilts, "e_raw": e_raw, "e_ax": e_ax, "got": got,
            "pred": pred_deg, "rot_err": rot_err}


# --------------------------------------------------------------------------- #
# 9. 道具の穴                                                                   #
# --------------------------------------------------------------------------- #
def section_tool_gaps() -> None:
    print("\n" + "=" * 78)
    print("9) 道具の穴(この PoC で使ってみて)")
    print("=" * 78)

    assert not hasattr(_L, "vol_region_gray_props")
    print("  (a) **gray 重み付きの領域統計**が無い。vol_region_props の centroid は"
          "voxel の幾何重心\n      (等重み)で、docstring も『gray 重み付きが要るなら"
          "自分で計算する』と書いている。\n      サブボクセルの位置ずれを測る仕事では"
          "ここが本体なので、`measure_vias` は自前。")

    assert not hasattr(_L, "fit_cylinder") and not hasattr(_L, "ransac_cylinder_axis")
    print("  (b) 円柱の**軸**を返す口が無い。ransac_cylinder は在るが台帳の型が"
          "点群向けで、\n      ラベルごとに軸と長さ(端面の位置)を返す口は無い。"
          "TSV/穴/ピンの検査では毎回要る。")

    # (c) 相似変換は 3-D しか無い(2-D は z=0 を足して呼ぶ)
    p = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
    m = np.asarray(_L.procrustes_fit(p, p + np.array([0.5, 0.25, 0.0])), float)
    assert m.shape == (4, 4) and abs(m[0, 3] - 0.5) < 1e-9, m
    print("  (c) 相似変換(Procrustes)は 3-D しか無い。2-D の格子どうしを合わせる"
          "のに\n      z=0 の列を足して呼んでいる —— 平面点群でも動くが、"
          "2-D の口があるべき。")

    assert not hasattr(_L, "vol_label_slice_centroids")
    print("  (d) ラベルごと・スライスごとの重心(点列)を返す口が無い。"
          "3 次元の細長い物体の\n      軸を測る定石なので、族に入れる価値はある。")

    assert hasattr(_L, "vol_label") and not hasattr(fs, "vol_label")
    print("  (e) vol_label / vol_region_props / fit_line3 / procrustes_fit は"
          "fullseye.ledger からしか呼べない。")


# --------------------------------------------------------------------------- #
def main() -> None:
    t0 = time.perf_counter()
    print("=" * 78)
    print("ダイの傾きと TSV の位置ずれを 1 つの CT から分ける")
    print("TSV %d 本/層(ピッチ %.0f µm、半径 %.0f µm)/ ダイ厚 %.0f µm / "
          "位置ずれの仕様 ±%.1f µm" % (NG * NG, PITCH_UM, R_TSV_UM, H_DIE_UM, SPEC_UM))
    print("=" * 78)

    a = section_bias()
    b = section_rotation(a)
    c = section_sweep()
    section_tool_gaps()

    print("\n" + "=" * 78)
    print("まとめ")
    print("=" * 78)
    print("  * 上面だけを見た位置ずれは %.4f µm 外す(仕様 ±%.1f µm)。偽装量は"
          "ダイ厚 x 法線の横成分で\n    予測でき(予測 %.4f / 実測 %.4f µm)、"
          "軸で下面へ引き直すと %.4f µm。"
          % (a["e_raw"], SPEC_UM, float(np.hypot(*a["bias_pred"])),
             float(np.hypot(*a["bias_meas"])), a["e_ax"]))
    print("  * ★傾きは回転も偽装する(予測 %+.5f° / 実測 %+.5f°)。並進の補正では"
          "消えず、\n    測った傾きで逆投影して初めて %+.5f°(真値 %+.5f°)に戻る。"
          % (b["rot_pred"], b["rot_meas"], a["es"]["deprojected"]["theta_deg"],
             a["sc"]["theta_deg"]))
    print("  * 崖は %.3f°(予測 %.3f°)。傾きを止めるより、測って外すほうが安い。"
          % (c["got"], c["pred"]))
    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))

    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")


if __name__ == "__main__":
    main()
