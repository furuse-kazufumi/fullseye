# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""視触覚センサの照明を実機の較正球で較正し、勾配 LUT を第 2 実装にする —— 真値は球の半径と手当ての円(2026-10-05)。

物理シミュ × Fullseye 系列、tacsim(弾性膜 + カメラ、2026.196)の続き。tacsim は 3 色照明の Lambertian を自分で合成して自分で逆算した。
ここは**実機の画像**(arXiv:2109.04027 の作者が MIT ライセンスで公開した較正パック、置き場は環境変数 ``FULLSEYE_TAXIM_DATA``)を持ち込み、
順方向(法線 → 色)を較正して逆方向(色 → 法線)を 2 つの独立な経路で解く:
  * **線形模型**(I_c = a_c + l_c · n、12 パラメタ)+ 既存 op :func:`photometric.photometric_stereo` で逆算(被験者)。
  * **example-based の勾配 LUT**(傾き θ・向き φ を 125 × 125 に切り、色の平均。位置の 2 次式つきの版も)—— 第 2 実装。
外から来る真値: 既知球の半径(接触円の内側で膜が球面にならう → 法線は閉形式)と、手で当てた接触円(整数 px・半径 2 px 刻み = 弱い真値)。
球の半径は較正にも評価にも入るので、門が見ているのは「別の画像に一般化するか」で R そのものではない。

門(既定 9 本、numpy だけ・データ不要): 較正の往復(12 パラメタ 1e-9、位置つき 72 パラメタ)/ 位置で利得が変わる非 Lambertian の合成で
LUT の往復(位置つき LUT が位置なしより良い)/ 試作で残った**不感帯**(傾き 0〜15° が 0 か 15° に寄る)が「行の少ないビンに近いビンの
位置の項を借りる」で消えること / 粗 → 細の逆引きと総当たりの一致・速さ / 外部の位置 2 次 LUT の書式へ係数を閉形式で写して同じ答え /
球冠の高さと法線の整合 / 列数・ビン数の下限と train・test の分離 / 綴り壊しで ValueError・角度は atan2(acos の床 1.1e-4°)/ 位置の掃引。
--full(データ門 10 本、``FULLSEYE_TAXIM_DATA`` が無ければ [skip]): hold-out の RGB 残差、角誤差(線形 vs 位置つき LUT)、接触円
(tacsim.contact_radius_ring = 被験者)、復元高さ vs 球冠、位置依存、背景差分の要否、較正枚数、2 台目のパック、実機の不感帯、粗 → 細の一致。
図(既定でも出る、FULLSEYE_FIGURES=off で止める): 合成の押し込みと 3 経路の誤差地図(等倍)、光を回す GIF(復元 vs 真値)、不感帯の
前後の傾き断面。--full で実機の 1 枚 → 復元 → 真の球冠、光を回す GIF、断面、残差地図、誤差地図、センサ面の誤差地図、較正枚数の曲線。
正直に: 力・押し込み深さの真値は無い。角誤差は最近傍の LUT(補間なし)の値。外部の較正済み LUT との比較は hold-out でない(参考値)。
2 台目のパックは球径・ピッチの一次情報が無く、半径に依らない量(線形の残差の比)だけを門にする。
Run: py -3.11 examples/poc_tacscalib_sphere_lut.py [--full] [--measure]
"""
from __future__ import annotations

import math
import os
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import annotate as AN  # noqa: E402
import examplefig as figs  # noqa: E402
import photometric as PH  # noqa: E402
import tacscalib as T  # noqa: E402
import tacsim as TS  # noqa: E402

FULL = "--full" in sys.argv
MEASURE = "--measure" in sys.argv          # 閾値を当てずに数だけ出す(閾値を決めた手順)
ENV_DATA = "FULLSEYE_TAXIM_DATA"
#: 2 台目のパック(較正パックの下のサブフォルダ名、ピッチは外部コードのコメントの値 = 一次情報なし)
PACK2_DIR, PACK2_PITCH_MM = "digit", 0.0266
#: 実機で位置つき LUT を引くときに使うビンの行数の下限(較正 24 枚のとき。枚数に比例させる)。1 行だけのビン(1 台目で 624 個)は
#: 色の平均がノイズ(背景の揺らぎ 3.6 DN)そのもので、1 のままだと深さが +16 % 偏る(門 18 で両方を測る)。合成(ノイズなし)は 1。
MC_REAL = 10


def min_count_for(n_frames: int) -> int:
    """較正枚数に比例させた行数の下限(24 枚で MC_REAL、1 枚なら 1)。"""
    return max(1, int(round(MC_REAL * n_frames / 24.0)))
_GATES: list[tuple[str, bool]] = []
_NUM: dict = {}

# 閾値(--measure の実測の外側に余裕を置いて固定。実測は各門の detail に出る)
THR = {
    # 実測(OPENBLAS_NUM_THREADS=1、2026-10-05): 1.1e-15 / 7.5e-15 / 2.7e-6°
    "fit_rel": 1e-9, "fit2_rel": 1e-9, "inv_deg": 1e-3,
    # 0.430° / 0.726° / 差 3.87°
    "lut0_med": 0.6, "lutpos_med": 1.0, "lut_margin": 3.0,
    # 13.24° → 0.58°
    "band_new": 1.5, "band_gain": 5.0,
    # 同じビン 99.3 %、中央値の差 0.002°(速さは測って出すだけ: CI の BLAS のスレッド数で比が変わる)
    "coarse_same": 0.98, "coarse_dmed": 0.05,
    # 100 %、7e-15 DN
    "adapter_same": 0.999,
    # 35,345 行・7,552 ビン
    "rows": 30000, "bins": 6000,
    "atan2_rel": 0.01,
    # データ門(実測): 7.92 / 4.63 DN
    "D_rms_lin": 9.0, "D_rms_pos": 5.5,
    # 4.17°、線形との差 6.54°
    "D_lutpos_med": 5.0, "D_margin": 5.0,
    # −0.25 px(MAD 1.10、手当ては 2 px 刻み)
    "D_ring_px": 2.0,
    # +4.7 %、7.1 µm
    "D_depth_rel": 0.08, "D_rms_um": 15.0,
    # ρ 0.79
    "D_lut_rho": 0.6,
    # +3.60° / −0.28°
    "D_nobg_worse": 2.0, "D_pos_delta": 1.0,
    # 1 → 24 枚で線形 +3.42°、位置つき 4 → 24 枚で −5.13°
    "D_lin_k1": 5.0, "D_pos_k4": 3.0,
    # 3.9 倍
    "D_rms_ratio": 2.5,
    # 4.84° → 1.89°、床 3.3°、深さ +18.5 % → +6.0 %
    "D_band_new": 2.5, "D_band_gain": 2.0, "D_floor": 4.5, "D_mc_gain": 0.06,
    # 90.0 %、最大 0.101°、2.5 倍
    "D_same": 0.85, "D_dmed": 0.3, "D_speed": 1.5,
}


def gate(name, ok, detail=""):
    if MEASURE:
        print("  [measure] %s %s" % (name, detail))
        return
    _GATES.append((name, bool(ok)))
    print("  [%s] %s %s" % ("ok" if ok else "NG", name, detail))


def skip(name, why):
    print("  [skip] %s —— %s" % (name, why))


def _raises(fn, exc=ValueError):
    try:
        fn()
    except exc:
        return True
    return False


# ======================================================================================================================
# 合成の場面(既定の門): 反射 max(n·l, 0)^1.5(非 Lambertian)× 光源ごとの位置利得
SH, SW, SR, SA = 180, 240, 51.0, 37.5        # 実機(480×640、R 68 px)の 3/8 の大きさ(CI の時間)
_LD = np.array([[0.0, 1.0, 1.0], [0.87, -0.5, 1.0], [-0.87, -0.5, 1.0]])
_LD /= np.linalg.norm(_LD, axis=1, keepdims=True)


def render_synth(normals, amp):
    """合成の膜の色(背景差分に相当): 各灯は自分の側が明るい(±amp の位置利得)。"""
    yy, xx = np.mgrid[0:SH, 0:SW]
    Xn, Yn = (xx - SW / 2) / SW, (yy - SH / 2) / SH
    return np.stack([np.maximum(normals @ _LD[c], 0.0) ** 1.5 * 60.0 * (1.0 + 2.0 * amp * (Xn * _LD[c, 0] + Yn * _LD[c, 1]))
                     for c in range(3)], axis=-1)


def synth_rows(centres, amp):
    rgb, nrm, pos = [], [], []
    for c in centres:
        s = T.sphere_normals_known((SH, SW), c, SA, SR)
        img = render_synth(s["normals"], amp)
        rgb.append(img[s["mask"]])
        nrm.append(s["normals"][s["mask"]])
        pos.append(np.argwhere(s["mask"]))
    assert len(rgb) >= 1
    return np.concatenate(rgb), np.concatenate(nrm), np.concatenate(pos)


def quarter(mask):
    m = mask.copy()
    m[1::2, :] = False
    m[:, 1::2] = False
    return m


def unit_to_pixel_coef(coef, H, W):
    """位置の基底を −1..1 の正規化から画素へ閉形式で写す: x = αX + β(α = 2/(W−1)、β = −1)、y も同じ。
    [x², y², xy, x, y, 1] の係数 c → [X², Y², XY, X, Y, 1] の係数 P。"""
    ax, bx, ay, by = 2.0 / (W - 1.0), -1.0, 2.0 / (H - 1.0), -1.0
    c0, c1, c2, c3, c4, c5 = (coef[..., k, :] for k in range(6))
    P = np.stack([c0 * ax * ax, c1 * ay * ay, c2 * ax * ay,
                  2 * c0 * ax * bx + c2 * ax * by + c3 * ax,
                  2 * c1 * ay * by + c2 * bx * ay + c4 * ay,
                  c0 * bx * bx + c1 * by * by + c2 * bx * by + c3 * bx + c4 * by + c5], axis=-2)
    return P


def numpy_part() -> dict:
    print("== 1. numpy の門(合成、データ不要)")
    t0, c0 = time.time(), time.process_time()
    out = {}
    rng = np.random.default_rng(7)
    # ── 1. 較正の往復
    L_true = np.array([[30.0, -41.0, 9.5], [22.0, 44.0, 7.4], [-69.0, 2.0, 21.5]]) + rng.normal(0, 1, (3, 3))
    amb = np.array([-8.5, -11.4, -23.9])
    sc = [T.sphere_normals_known((SH, SW), c, 45.0, SR) for c in ((90, 75), (82, 165), (98, 120))]
    fit_true = {"L": L_true, "ambient": amb}
    diffs = [T.membrane_predict_rgb(s["normals"], fit_true) for s in sc]
    fit = T.lights_fit_from_sphere(diffs[:2], [s["normals"] for s in sc[:2]], [s["mask"] for s in sc[:2]])
    rel = max(np.abs(fit["L"] - L_true).max() / np.abs(L_true).max(), np.abs(fit["ambient"] - amb).max() / np.abs(amb).max())
    m = sc[2]["mask"]
    assert int(m.sum()) >= 1000
    inv = float(T.normal_error_map(T.linear_invert(diffs[2], fit), sc[2]["normals"])[m].max())
    # 位置つき(72 パラメタ): 真の係数を作って往復
    coef_true = rng.normal(0, 3, (4, 6, 3))
    coef_true[1:, 5, :] = L_true.T
    coef_true[0, 5, :] = amb
    fit2_true = {"order": 2, "coef": coef_true, "image_shape": (SH, SW), "L": L_true, "ambient": amb}
    d2 = [T.membrane_predict_rgb(s["normals"], fit2_true) for s in sc]
    fit2 = T.lights_fit_from_sphere(d2, [s["normals"] for s in sc], [s["mask"] for s in sc], order=2)
    rel2 = float(np.abs(fit2["coef"] - coef_true).max() / np.abs(coef_true).max())
    gate("門 1 照明の較正の往復(合成): 線形 12 パラメタの L・ambient の相対誤差 %.1e、hold-out 球を photometric_stereo で逆算して最大 %.1e°"
         "(float32 を返す床)、位置つき 72 パラメタの係数 %.1e" % (rel, inv, rel2),
         rel <= THR["fit_rel"] and inv <= THR["inv_deg"] and rel2 <= THR["fit2_rel"])
    _NUM["fit"] = {"rel": rel, "inv_max_deg": inv, "rel_order2": rel2}

    # ── 2. LUT の往復(位置で利得が変わる非 Lambertian)
    # 中心に副画素のずれ: 全部整数だと球ごとの画素の法線が同じになり、どのビンも「球の数 × 同じ行数」で行の少ないビンが生まれない
    # (= 不感帯の罠が合成では原理的に見えない。実機の手当ての中心は整数でも膜の押し込みは画素格子に揃わない)
    cents = [(52 + 38 * i + 0.37 * ((3 * i + j) % 5), 52 + 34 * j + 0.29 * ((i + 2 * j) % 7)) for i in range(3) for j in range(5)]
    train = [c for k, c in enumerate(cents) if k % 2 == 0]
    test = [c for k, c in enumerate(cents) if k % 2 == 1][::2]
    assert set(train).isdisjoint(test) and len(train) >= 6 and len(test) >= 3
    res = {}
    for amp in (0.0, 0.4):
        rr, rn, rp = synth_rows(train, amp)
        lut = T.gradient_lut_build(rr, rn, 125, positions=rp, image_shape=(SH, SW), min_rows_poly=8)
        e_pos, e_np = [], []
        for c in test:
            s = T.sphere_normals_known((SH, SW), c, SA, SR)
            img = render_synth(s["normals"], amp)
            mq = quarter(s["mask"])
            assert int(mq.sum()) >= 1000
            e_pos.append(T.normal_error_map(T.gradient_lut_invert(img, lut, mq), s["normals"])[mq])
            lut_np = {k: v for k, v in lut.items() if k != "coef"} | {"coef": None}
            e_np.append(T.normal_error_map(T.gradient_lut_invert(img, lut_np, mq), s["normals"])[mq])
        res[amp] = (float(np.median(np.concatenate(e_pos))), float(np.median(np.concatenate(e_np))))
        out["lut_%.1f" % amp] = lut
    (p0, n0), (p4, n4) = res[0.0], res[0.4]
    gate("門 2 LUT の往復(合成: 反射 max(n·l,0)^1.5、光源ごとの位置利得): 利得なし LUT %.3f°(125 ビンの量子化の床)、利得 ±40 %%: 位置つき %.3f° vs "
         "位置なし %.3f°(差 %.2f°)" % (n0, p4, n4, n4 - p4),
         n0 <= THR["lut0_med"] and p4 <= THR["lutpos_med"] and n4 - p4 >= THR["lut_margin"])
    _NUM["lut_roundtrip"] = {"amp0_lut": n0, "amp0.4_pos": p4, "amp0.4_nopos": n4}

    # ── 3. 不感帯: 行の少ないビン(傾きの小さい所)が位置の項を持たないと 0〜15° が寄る
    rr, rn, rp = synth_rows(train, 0.4)
    lut_pool = T.gradient_lut_build(rr, rn, 125, positions=rp, image_shape=(SH, SW), min_rows_poly=8, pool=True)
    lut_nopool = T.gradient_lut_build(rr, rn, 125, positions=rp, image_shape=(SH, SW), min_rows_poly=8, pool=False)
    band = {"poly_only": [], "const_small": [], "pooled": []}
    prof = {}
    for ci, c in enumerate(test):
        s = T.sphere_normals_known((SH, SW), c, SA, SR)
        img = render_synth(s["normals"], 0.4)
        mb = s["mask"] & (s["theta"] < math.radians(15.0))
        assert int(mb.sum()) >= 300
        th_t = s["theta"][mb]
        for key, tab, mc in (("poly_only", lut_nopool, 8), ("const_small", lut_nopool, 1), ("pooled", lut_pool, 1)):
            th_r = T.normals_to_angles(T.gradient_lut_invert(img, tab, mb, min_count=mc))[0][mb]
            band[key].append(np.degrees(np.abs(th_r - th_t)))
            if ci == 0:
                prof[key] = (np.degrees(th_t), np.degrees(th_r))
    bmed = {k: float(np.median(np.concatenate(v))) for k, v in band.items()}
    gate("門 3 不感帯(傾き < 15° の画素の |Δθ| 中央値): 位置の項を当てたビン(8 行以上)だけで引く %.2f° / 行の少ないビンを位置なしの平均で足す %.2f° / "
         "近いビンの位置の項を借りる %.2f°(試作の罠の直し)" % (bmed["poly_only"], bmed["const_small"], bmed["pooled"]),
         bmed["pooled"] <= THR["band_new"] and bmed["poly_only"] - bmed["pooled"] >= THR["band_gain"])
    _NUM["deadband_synth"] = bmed | {"pooled_bins": lut_pool["pooled_bins"], "poly_bins": lut_pool["poly_bins"]}
    out["band_profile"] = prof

    # ── 4. 粗 → 細 vs 総当たり
    same, dmed = [], []
    for c in test:
        s = T.sphere_normals_known((SH, SW), c, SA, SR)
        img = render_synth(s["normals"], 0.4)
        mq = quarter(s["mask"])
        ne = T.gradient_lut_invert(img, lut_pool, mq, method="exact")
        nc = T.gradient_lut_invert(img, lut_pool, mq)
        same.append(T.normal_error_map(ne, nc)[mq] < 1e-9)
        dmed.append(np.median(T.normal_error_map(nc, s["normals"])[mq]) - np.median(T.normal_error_map(ne, s["normals"])[mq]))
    s = T.sphere_normals_known((SH, SW), test[0], SA, SR)            # 速さは接触円 1 つ分の全画素で(1/4 間引きだと区画ごとの画素が少なすぎる)
    img = render_synth(s["normals"], 0.4)
    ta = time.perf_counter()
    T.gradient_lut_invert(img, lut_pool, s["mask"], method="exact")
    tb = time.perf_counter()
    T.gradient_lut_invert(img, lut_pool, s["mask"])
    t_ex, t_co = tb - ta, time.perf_counter() - tb
    fs_ = float(np.mean(np.concatenate(same)))
    dm = float(np.max(np.abs(dmed)))
    gate("門 4 粗 → 細の逆引き(3 × 3 ビンの区画の代表 → 上位 2 区画の周りだけ)vs 総当たり: 同じビン %.1f %%、角誤差の中央値の差 最大 %.3f°、"
         "速さ %.1f 倍(接触円 1 つ %d 画素: %.2f s → %.2f s)" % (100 * fs_, dm, t_ex / max(t_co, 1e-9), int(s["mask"].sum()), t_ex, t_co),
         fs_ >= THR["coarse_same"] and dm <= THR["coarse_dmed"])
    _NUM["coarse_synth"] = {"same": fs_, "dmed_max": dm, "t_exact": t_ex, "t_coarse": t_co}

    # ── 5. アダプタ: 外部の書式(画素の基底)へ係数を閉形式で写す → 同じ逆引き
    Pc = unit_to_pixel_coef(lut_pool["coef"], SH, SW)
    poly = {"bins": np.array(125), "grad_r": Pc[..., 0], "grad_g": Pc[..., 1], "grad_b": Pc[..., 2]}
    s = T.sphere_normals_known((SH, SW), test[0], SA, SR)
    img = render_synth(s["normals"], 0.4)
    mm = quarter(s["mask"])
    full_tab = dict(lut_pool, count=np.ones_like(lut_pool["count"]))         # 外部の表は全ビンが埋まっている扱い
    na = T.gradient_lut_invert(img, full_tab, mm, method="exact")
    nb = T.poly_lut_invert(img, poly, mm, method="exact")
    sa = float(np.mean(T.normal_error_map(na, nb)[mm] < 1e-9))
    yy, xx = np.nonzero(mm)
    k0 = (60, 40)
    v_unit = T._pos_basis(yy[:50], xx[:50], "unit", (SH, SW)) @ lut_pool["coef"][k0]
    v_pix = T._pos_basis(yy[:50], xx[:50], "pixel") @ Pc[k0]
    cf = float(np.abs(v_unit - v_pix).max())
    gate("門 5 外部の位置 2 次 LUT の書式(x, y = 画素のまま)へ係数を閉形式で写す(x = 2X/(W−1) − 1 を展開): 予測色の差 %.1e DN、poly_lut_invert と"
         " gradient_lut_invert が同じビンを選ぶ画素 %.2f %%(丸めで同点が割れる分だけ違ってよい)、係数の形が違えば ValueError"
         % (cf, 100 * sa), sa >= THR["adapter_same"] and cf < 1e-9
         and _raises(lambda: T.poly_lut_invert(img, {"bins": np.array(125), "grad_r": Pc[..., 0][:, :3], "grad_g": Pc[..., 1], "grad_b": Pc[..., 2]}, mm)))
    _NUM["adapter"] = {"same": sa, "coef_diff": cf}

    # ── 6. 球冠の高さと法線の整合
    pitch = 0.0295e-3
    cap = T.sphere_cap_height((SH, SW), (90.3, 120.7), SA, SR, pitch)
    s = T.sphere_normals_known((SH, SW), (90.3, 120.7), SA, SR)
    hpx = cap["h"] / pitch
    gy, gx = np.gradient(hpx)
    inner = s["mask"] & (s["r"] < SA - 2.0)
    p_true = -s["normals"][..., 0] / s["normals"][..., 2]
    q_true = -s["normals"][..., 1] / s["normals"][..., 2]
    gerr = float(max(np.abs(gx - p_true)[inner].max(), np.abs(gy - q_true)[inner].max()))
    delta_ok = abs(cap["delta"] - (SR - math.sqrt(SR * SR - SA * SA)) * pitch) < 1e-15
    edge = float(np.abs(cap["h"][(s["r"] > SA - 0.5) & (s["r"] < SA + 0.5)]).max() / cap["delta"])
    gate("門 6 球冠の高さと既知球の法線: 中心差分の勾配 = −n_x/n_z・−n_y/n_z が縁の 2 px 内側まで最大 %.1e(中心差分の打ち切り誤差)、"
         "深さ δ = R − √(R² − a²) が閉形式と 1e-15、縁 r = a の ±0.5 px で |h|/δ ≤ %.3f(連続)" % (gerr, edge),
         gerr < 0.02 and delta_ok and edge < 0.05)

    # ── 7. 列数・ビン数の下限と分離
    nb_ = int((lut_pool["count"] > 0).sum())
    gate("門 7 LUT の行 %d・中身のあるビン %d(下限 %d / %d)、train %d 球・test %d 球で重なり 0" % (lut_pool["n_rows"], nb_, THR["rows"], THR["bins"],
                                                                        len(train), len(test)),
         lut_pool["n_rows"] >= THR["rows"] and nb_ >= THR["bins"] and set(train).isdisjoint(test))

    # ── 8. fail-closed と atan2
    tmpd = Path(os.environ.get("TMP", os.environ.get("TEMP", "."))) / ("tacscalib_probe_%d" % os.getpid())
    tmpd.mkdir(parents=True, exist_ok=True)
    z = np.zeros((4, 4, 3), np.uint8)
    np.savez(tmpd / "bad_key.npz", f0=z, imgs=z[None], touch_centre=np.zeros((1, 2)), touch_radius=np.ones(1))
    np.savez(tmpd / "zero_r.npz", f0=z, imgs=z[None], touch_center=np.zeros((1, 2)), touch_radius=np.zeros(1))
    np.savez(tmpd / "ok.npz", f0=z, imgs=z[None], touch_center=np.array([[1.0, 2.0]]), touch_radius=np.ones(1))
    try:
        T.calib_pack_load(str(tmpd / "bad_key.npz"), 0.0295, 2.0)
        key_msg = False
    except ValueError as e:
        key_msg = "touch_center" in str(e)
    pk = T.calib_pack_load(str(tmpd / "ok.npz"), 0.0295, 2.0)
    swapped = tuple(pk["centers"][0]) == (2.0, 1.0)
    probes = [_raises(lambda: T.calib_pack_load(str(tmpd / "zero_r.npz"), 0.0295, 2.0)),
              _raises(lambda: T.calib_pack_load(str(tmpd / "ok.npz"), 0.0, 2.0)),
              _raises(lambda: T.calib_pack_load(str(tmpd / "missing.npz"), 0.0295, 2.0), FileNotFoundError),
              _raises(lambda: T.sphere_normals_known((SH, SW), (1.0, float("nan")), SA, SR)),
              _raises(lambda: T.gradient_lut_invert(img, lut_pool, mm, method="exactly")),
              _raises(lambda: T.lights_fit_from_sphere(diffs[0], sc[0]["normals"], sc[0]["mask"], order=1)),
              _raises(lambda: T.gradient_lut_build(rr, rn, 125, positions=rp))]
    for f in tmpd.iterdir():
        f.unlink()
    tmpd.rmdir()
    ang = 1e-7
    n1 = np.array([[0.0, 0.0, 1.0]])
    n2 = np.array([[math.sin(math.radians(ang)), 0.0, math.cos(math.radians(ang))]])
    e_at = float(T.normal_error_map(n1, n2)[0])
    e_ac = float(PH.angular_error_deg(n1[None], n2[None])[0, 0])
    gate("門 8 fail-closed: 綴りを壊した鍵 touch_centre は欠けた鍵の名で ValueError=%s、(x, y) → (行, 列)=%s、半径 0・ピッチ 0・無いパス・nan の中心・"
         "method の綴り・order 1・positions だけ = %d/%d 拒否 / 角度 1e-7° を atan2 で %.4e°(既存の acos 版は %.3e° = 床)"
         % (key_msg, swapped, sum(probes), len(probes), e_at, e_ac),
         key_msg and swapped and all(probes) and abs(e_at - ang) / ang <= THR["atan2_rel"])
    _NUM["atan2"] = {"atan2_deg": e_at, "acos_deg": e_ac}

    # ── 9. 位置の掃引
    cen = np.array([[SH / 2 - 0.5 + 10 * k, SW / 2 - 0.5] for k in range(5)])
    sw = T.field_position_sweep(cen, 1.0 + 0.3 * np.arange(5), (SH, SW))
    sw_t = T.field_position_sweep(cen, np.array([1.0, 1.0, 2.0, 2.0, 3.0]), (SH, SW))
    gate("門 9 位置の掃引: 距離に線形な誤差 → 傾き %.3f / 100 px(真 3.000)・Spearman %.3f、同順位を含む列でも ρ = %.3f、3 組未満は ValueError"
         % (sw["slope_per_100px"], sw["spearman"], sw_t["spearman"]),
         abs(sw["slope_per_100px"] - 3.0) < 1e-9 and abs(sw["spearman"] - 1.0) < 1e-12 and 0.9 < sw_t["spearman"] < 1.0
         and _raises(lambda: T.field_position_sweep(cen[:2], np.ones(2), (SH, SW))))
    out["t_numpy"] = time.time() - t0
    print("  (numpy の門 %.2f s、この process の CPU %.2f s)" % (out["t_numpy"], time.process_time() - c0))
    out["synth"] = {"train": train, "test": test, "lut": lut_pool}
    return out


# ======================================================================================================================
# 実機データ
def external_bg(f0, sigma=50.0, thr=5.0, mix=0.15):
    """外部の較正手順と同じ背景(読んで再現、コードは写していない): σ = 50 の平滑(反射端)→ 平滑 − 原画の平均 < 5 の画素は
    0.15·平滑 + 0.85·原画。外部の手順は uint8 の配列に代入するので切り捨てまで再現する。"""
    from scipy.ndimage import gaussian_filter1d
    f = np.asarray(f0, np.float64)
    sm = gaussian_filter1d(gaussian_filter1d(f, sigma, axis=0, mode="reflect", truncate=4.0), sigma, axis=1, mode="reflect", truncate=4.0)
    sm = np.floor(np.clip(sm, 0, 255))
    sel = np.mean(sm - f, axis=2) < thr
    out = sm.copy()
    out[sel] = np.floor(mix * sm[sel] + (1.0 - mix) * f[sel])
    return out


def radial_profile(img, centre, r_max, step=1.0):
    a = np.asarray(img, np.float64)
    yy, xx = np.mgrid[0:a.shape[0], 0:a.shape[1]]
    r = np.hypot(yy - centre[0], xx - centre[1])
    nb = int(r_max / step)
    idx = (r / step).astype(int)
    sel = (idx < nb) & np.isfinite(a)
    s = np.bincount(idx[sel], a[sel], nb)
    c = np.bincount(idx[sel], None, nb)
    return (np.arange(nb) + 0.5) * step, np.where(c > 0, s / np.maximum(c, 1), np.nan)


def height_from_normals_radial(normals, centre, r_max, step=0.5):
    """法線の半径方向スロープを方位平均して中心から 1D 積分した h(r) − h(0)、単位 px(FFT 積分の減衰を受けない経路)。"""
    p, q = PH.normals_to_gradients(np.asarray(normals, np.float64))
    yy, xx = np.mgrid[0:p.shape[0], 0:p.shape[1]].astype(np.float64)
    dy, dx = yy - centre[0], xx - centre[1]
    r = np.hypot(dx, dy)
    sr = np.where(r > 1e-9, (p * dx + q * dy) / np.maximum(r, 1e-9), 0.0)
    rr, sm = radial_profile(sr, centre, r_max, step)
    return rr, np.cumsum(np.nan_to_num(sm)) * step


class Pack:
    """1 台分の較正パック + 偶数 / 奇数の train / test + 較正済みの経路。"""

    def __init__(self, path, pitch_mm, R_mm, n_test=None, stride=2):
        self.pk = T.calib_pack_load(path, pitch_mm, R_mm)
        self.f0 = self.pk["f0"].astype(np.float64)
        self.H, self.W = self.f0.shape[:2]
        n = self.pk["n"]
        self.train, self.test = list(range(0, n, 2)), list(range(1, n, 2))
        if n_test is not None:
            self.test = self.test[:n_test]
        assert set(self.train).isdisjoint(self.test) and len(self.train) >= 2 and len(self.test) >= 3
        self.stride = stride

    def item(self, i, bg=True):
        d = self.pk["imgs"][i].astype(np.float64) - (self.f0 if bg else 0.0)
        s = T.sphere_normals_known((self.H, self.W), self.pk["centers"][i], self.pk["radii"][i], self.pk["R_px"])
        return d, s

    def calibrate(self, idx, bg=True, flat=True, fit2=True):
        assert len(idx) >= 1
        items = [self.item(i, bg) for i in idx]
        D, N, M = [d for d, s in items], [s["normals"] for d, s in items], [s["mask"] for d, s in items]
        fit = T.lights_fit_from_sphere(D, N, M)
        fit2 = T.lights_fit_from_sphere(D, N, M, order=2) if fit2 else None
        rr = np.concatenate([d[s["mask"]] for d, s in items])
        rn = np.concatenate([s["normals"][s["mask"]] for d, s in items])
        rp = np.concatenate([np.argwhere(s["mask"]) for d, s in items])
        lut = T.gradient_lut_build(rr, rn, 125)                                          # 位置なし
        fr = fp = None
        if flat:
            # 平らな例: 接触から遠い輪 2.2a〜2.6a(3 px 間引き)を n = (0, 0, 1) として足す(弱い真値: 膜の裾は遠方で消える)
            sub = (np.arange(self.H)[:, None] % 3 == 0) & (np.arange(self.W)[None, :] % 3 == 0)
            fr, fp = [], []
            for (d, s), i in zip(items, idx):
                a = float(self.pk["radii"][i])
                f = (s["r"] > 2.2 * a) & (s["r"] < 2.6 * a) & sub
                fr.append(d[f])
                fp.append(np.argwhere(f))
            fr, fp = np.concatenate(fr), np.concatenate(fp)
        pos = T.gradient_lut_build(rr, rn, 125, positions=rp, image_shape=(self.H, self.W), flat_rgb=fr, flat_positions=fp)
        # 試作の最終形(平らな例あり・借りない・30 行以上のビンだけで引く)= 不感帯の比べ相手
        old = T.gradient_lut_build(rr, rn, 125, positions=rp, image_shape=(self.H, self.W), flat_rgb=fr, flat_positions=fp, pool=False)
        return {"fit": fit, "fit2": fit2, "lut": lut, "old": old, "pos": pos, "mc": min_count_for(len(idx))}

    def mask_eval(self, s):
        m = s["mask"].copy()
        if self.stride > 1:
            sub = np.zeros_like(m)
            sub[::self.stride, ::self.stride] = True
            m &= sub
        return m

    @staticmethod
    def invert(cal, d, m, which=("lin", "lut", "pos")):
        out = {}
        if "lin" in which:
            out["lin"] = T.linear_invert(d, cal["fit"])
        if "lut" in which:
            out["lut"] = T.gradient_lut_invert(d, cal["lut"], m)
        if "old" in which:
            out["old"] = T.gradient_lut_invert(d, cal["old"], m, min_count=30)
        if "pos" in which:
            out["pos"] = T.gradient_lut_invert(d, cal["pos"], m, min_count=cal["mc"])
        return out


def data_part(out: dict, root: str) -> dict:
    print("== 2. データ門(較正パック、%s の下)" % ENV_DATA)
    t0, c0 = time.time(), time.process_time()
    A = Pack(os.path.join(root, "calibs", "dataPack.npz"), 0.0295, 2.00)
    pk = A.pk
    cal = A.calibrate(A.train)
    poly = dict(np.load(os.path.join(root, "calibs", "polycalib.npz")))
    bgx = external_bg(pk["f0"])
    per = []
    for i in A.test:
        d, s = A.item(i)
        m = A.mask_eval(s)
        assert int(m.sum()) >= 2000, "評価マスクが小さすぎる"
        inv = A.invert(cal, d, m, which=("lin", "lut", "old", "pos"))
        mq = m.copy()
        mq[1::2, :] = False
        mq[:, 1::2] = False
        inv["ext"] = T.poly_lut_invert(pk["imgs"][i].astype(np.float64) - bgx, poly, mq)
        th_t = s["theta"]
        rec = {"i": i, "centre": pk["centers"][i], "a": pk["radii"][i]}
        band = m & (th_t < math.radians(15.0))
        for k, nn in inv.items():
            mm = mq if k == "ext" else m
            th = T.normals_to_angles(nn)[0]
            rec[k] = {"med": float(np.median(T.normal_error_map(nn, s["normals"])[mm])),
                      "band": float(np.median(np.degrees(np.abs(th - th_t))[band])) if band.any() else float("nan"),
                      "bias": float(np.degrees(np.mean((th - th_t)[mm])))}
        rec["pred_rms"] = float(np.sqrt(np.mean((T.membrane_predict_rgb(s["normals"], cal["fit"]) - d)[s["mask"]] ** 2)))
        rec["pred2_ms"] = float(np.mean((T.membrane_predict_rgb(s["normals"], cal["fit2"]) - d)[s["mask"]] ** 2))
        rec["bg_rms"] = float(np.sqrt(np.mean(d[s["r"] > 2.5 * pk["radii"][i]] ** 2)))
        per.append(rec)
    assert len(per) >= 20
    t_main = time.time() - t0
    keys = ("lin", "lut", "old", "pos", "ext")
    med = {k: float(np.median([r[k]["med"] for r in per])) for k in keys}
    # ── 10. hold-out の RGB 残差
    rms_lin = float(np.sqrt(np.mean([r["pred_rms"] ** 2 for r in per])))
    rms_pos = float(np.sqrt(np.mean([r["pred2_ms"] for r in per])))
    bg_rms = float(np.median([r["bg_rms"] for r in per]))
    gate("門 10 hold-out の RGB 残差(偶数 %d 枚で較正 → 奇数 %d 枚を予測): 線形 12 パラメタ %.2f DN(train %.2f)/ 位置つき 72 パラメタ %.2f DN / "
         "接触の遠方の背景差 %.2f DN(下限の目安)" % (len(A.train), len(A.test), rms_lin, float(np.sqrt(np.mean(cal["fit"]["rms"] ** 2))), rms_pos, bg_rms),
         rms_lin <= THR["D_rms_lin"] and rms_pos <= THR["D_rms_pos"])
    _NUM["D_residual"] = {"lin": rms_lin, "pos": rms_pos, "bg": bg_rms, "L": cal["fit"]["L"].tolist(), "ambient": cal["fit"]["ambient"].tolist()}
    # ── 11. 角誤差
    bias = {k: float(np.median([r[k]["bias"] for r in per])) for k in keys}
    gate("門 11 法線の角誤差の中央値(hold-out %d 枚、接触円の内側): 線形 %.2f° / 位置なし LUT %.2f° / 位置つき LUT(平らな例 + 借りる)%.2f° / 外部の較正済み LUT "
         "%.2f°(※同じ 48 枚で較正済み = hold-out でない、参考値)。傾きの偏り 線形 %+.2f° / 位置つき %+.2f°"
         % (len(per), med["lin"], med["lut"], med["pos"], med["ext"], bias["lin"], bias["pos"]),
         med["pos"] <= THR["D_lutpos_med"] and med["lin"] - med["pos"] >= THR["D_margin"])
    _NUM["D_angle"] = {"median": med, "bias": bias}
    # ── 12. 接触円(被験者 = tacsim.contact_radius_ring)と ── 13. 復元高さ
    hw = 100
    ring_rows, fig_case = [], None
    assert len(per) >= 8
    for r in per[:8]:
        i = r["i"]
        d, s = A.item(i)
        c = pk["centers"][i]
        y0 = max(0, min(A.H - 2 * hw - 1, int(round(c[0])) - hw))
        x0 = max(0, min(A.W - 2 * hw - 1, int(round(c[1])) - hw))
        win = np.zeros((A.H, A.W), bool)
        win[y0:y0 + 2 * hw + 1, x0:x0 + 2 * hw + 1] = True
        nfull = T.gradient_lut_invert(d, cal["pos"], win, min_count=cal["mc"])
        nc = nfull[y0:y0 + 2 * hw + 1, x0:x0 + 2 * hw + 1]
        z = PH.integrate_normals(nc)
        ring = TS.contact_radius_ring(z * pk["pitch"], pk["pitch"], r_max_px=hw - 10)
        ring_def = TS.contact_radius_ring(z * pk["pitch"], pk["pitch"])            # 既定の探索半径(罠の記録)
        rc = (c[0] - y0, c[1] - x0)
        rr, prof = height_from_normals_radial(nc, (ring["cy"], ring["cx"]), 0.8 * r["a"])
        true = pk["R_px"] - np.sqrt(pk["R_px"] ** 2 - rr ** 2)
        yy, xx = np.mgrid[0:nc.shape[0], 0:nc.shape[1]]
        rg = np.hypot(yy - ring["cy"], xx - ring["cx"])
        hz = -z * pk["pitch_mm"] * 1000
        um = pk["pitch_mm"] * 1000
        ring_rows.append({"i": i, "ring": ring["r_px"], "ring_default": ring_def["r_px"], "hand": r["a"],
                          "ctr": float(math.hypot(ring["cy"] - rc[0], ring["cx"] - rc[1])),
                          "depth_rad": float(prof[-1] * um), "depth_true": float(true[-1] * um),
                          "depth_fft": float(hz[rg < 2].mean() - hz[np.abs(rg - 0.8 * r["a"]) < 0.75].mean()),
                          "rms": float(np.sqrt(np.mean((prof - true) ** 2)) * um)})
        if fig_case is None:
            fig_case = {"i": i, "y0": y0, "x0": x0, "hw": hw, "nc": nc, "z": z, "ring": ring, "rr": rr, "prof": prof, "true": true}
    dr = np.array([x["ring"] - x["hand"] for x in ring_rows])
    dr_def = float(np.median([x["ring_default"] - x["hand"] for x in ring_rows]))
    gate("門 12 tacsim.contact_radius_ring(被験者: 位置つき LUT の法線を FFT 積分した高さ)vs 手当ての円: 半径の差 中央値 %+.2f px(MAD %.2f)、中心の差 "
         "%.2f px(8 枚)/ 探索半径を既定のままにすると %+.1f px(窓の半分の半分で打ち切る罠 —— 直す案は INTEGRATE に)"
         % (np.median(dr), np.median(np.abs(dr - np.median(dr))), np.median([x["ctr"] for x in ring_rows]), dr_def),
         abs(float(np.median(dr))) <= THR["D_ring_px"])
    rel = float(np.median([x["depth_rad"] / x["depth_true"] - 1.0 for x in ring_rows]))
    relf = float(np.median([x["depth_fft"] / x["depth_true"] - 1.0 for x in ring_rows]))
    rmsu = float(np.median([x["rms"] for x in ring_rows]))
    gate("門 13 復元高さ(r = 0.8a までの深さ)vs 球冠: 真 %.0f µm に対し 半径積分 %+.1f %%、FFT 積分 %+.1f %%、断面の RMS %.1f µm(8 枚)"
         % (np.median([x["depth_true"] for x in ring_rows]), 100 * rel, 100 * relf, rmsu),
         abs(rel) <= THR["D_depth_rel"] and rmsu <= THR["D_rms_um"])
    _NUM["D_ring"] = {"median_px": float(np.median(dr)), "default_rmax_px": dr_def, "depth_rel": rel, "depth_rel_fft": relf, "rms_um": rmsu}
    # ── 14. 位置依存
    cen = np.array([r["centre"] for r in per])
    sws = {k: T.field_position_sweep(cen, np.array([r[k]["med"] for r in per]), (A.H, A.W)) for k in ("lin", "lut", "pos")}
    gate("門 14 位置依存(画像中心からの距離 vs 角誤差): 線形 %+.2f°/100 px ρ = %.2f / 位置なし LUT %+.2f ρ = %.2f / 位置つき LUT %+.2f ρ = %.2f"
         % tuple(v for k in ("lin", "lut", "pos") for v in (sws[k]["slope_per_100px"], sws[k]["spearman"])),
         sws["lut"]["spearman"] >= THR["D_lut_rho"] and sws["pos"]["slope_per_100px"] < sws["lut"]["slope_per_100px"])
    _NUM["D_position"] = {k: {"slope": v["slope_per_100px"], "rho": v["spearman"]} for k, v in sws.items()}
    # ── 15. 背景差分の要否
    cal_nb = A.calibrate(A.train, bg=False, flat=False, fit2=False)
    nb, wb = {"lin": [], "lut": [], "pos": []}, {"lin": [], "lut": [], "pos": []}
    for r in per[:8]:
        d, s = A.item(r["i"], bg=False)
        m = A.mask_eval(s)
        for k, nn in A.invert(cal_nb, d, m).items():
            nb[k].append(float(np.median(T.normal_error_map(nn, s["normals"])[m])))
        for k in wb:
            wb[k].append(r[k]["med"])
    nbm = {k: float(np.median(v)) for k, v in nb.items()}
    wbm = {k: float(np.median(v)) for k, v in wb.items()}
    gate("門 15 背景差分の要否(引かずに同じ手順、同じ 8 枚): 引かない / 引く = 線形 %.2f / %.2f°、位置なし LUT %.2f / %.2f°(悪化 %+.2f°)、"
         "位置つき LUT %.2f / %.2f°(差 %+.2f° = 背景も位置の 2 次式に吸収される)" % (nbm["lin"], wbm["lin"], nbm["lut"], wbm["lut"], nbm["lut"] - wbm["lut"],
                                                           nbm["pos"], wbm["pos"], nbm["pos"] - wbm["pos"]),
         nbm["lut"] - wbm["lut"] >= THR["D_nobg_worse"] and abs(nbm["pos"] - wbm["pos"]) <= THR["D_pos_delta"])
    _NUM["D_background"] = {"no_bg": nbm, "with_bg": wbm}
    # ── 16. 較正枚数
    ks = [1, 4, 24]
    test4 = A.test[:4]
    assert len(test4) >= 4
    curve = {}
    for k in ks:
        idx = sorted({A.train[int(round(j))] for j in np.linspace(0, len(A.train) - 1, k)})
        ck = A.calibrate(idx, flat=False, fit2=False)
        errs = {"lin": [], "lut": [], "pos": []}
        for i in test4:
            d, s = A.item(i)
            m = s["mask"].copy()
            m[1::3, :] = False
            m[2::3, :] = False
            m[:, 1::3] = False
            m[:, 2::3] = False
            for kk, nn in A.invert(ck, d, m).items():
                errs[kk].append(np.median(T.normal_error_map(nn, s["normals"])[m]))
        curve[k] = {kk: float(np.median(v)) for kk, v in errs.items()} | {"poly_bins": int(ck["pos"]["poly_bins"])}
    g1, g2 = curve[1]["lin"] - curve[24]["lin"], curve[4]["pos"] - curve[24]["pos"]
    d1, s1 = A.item(A.train[0])
    refuse1 = _raises(lambda: T.lights_fit_from_sphere(d1, s1["normals"], s1["mask"], order=2))   # 1 枚では n_x と x が同じ向き = 退化
    gate("門 16 較正枚数(1 / 4 / 24 枚、hold-out 4 枚): 線形 %.2f → %.2f → %.2f°(12 パラメタは 1 枚でも解ける)/ 位置つき LUT %.2f → %.2f → %.2f°(位置の項は"
         "枚数が要る、多項式ビン %d → %d → %d)。位置つき 72 パラメタの照明は 1 枚では退化(球の中では n_x が x の 1 次式)で ValueError=%s"
         % (curve[1]["lin"], curve[4]["lin"], curve[24]["lin"], curve[1]["pos"], curve[4]["pos"], curve[24]["pos"],
            curve[1]["poly_bins"], curve[4]["poly_bins"], curve[24]["poly_bins"], refuse1),
         g1 <= THR["D_lin_k1"] and g2 >= THR["D_pos_k4"] and refuse1)
    _NUM["D_count"] = curve
    # ── 18. 実機の不感帯(位置の項を当てたビンだけで引く試作 vs 借りる)と平地の床
    bnd = {k: float(np.nanmedian([r[k]["band"] for r in per])) for k in ("lin", "lut", "old", "pos")}
    floor = {"old": [], "pos": []}
    for r in per[:4]:
        d, s = A.item(r["i"])
        far = (s["r"] > 2.8 * r["a"]) & (s["r"] < 3.2 * r["a"]) & A.mask_eval({"mask": np.ones_like(s["mask"])})
        assert int(far.sum()) >= 200
        inv = A.invert(cal, d, far, which=("old", "pos"))
        for k in floor:
            floor[k].append(float(np.degrees(np.median(T.normals_to_angles(inv[k])[0][far]))))
    flm = {k: float(np.median(v)) for k, v in floor.items()}
    dep1, dep10 = [], []
    for r in per[:4]:                     # 行 1 のビンまで使うと深さが偏る(ノイズの平均を「傾き」と読む)
        d, s = A.item(r["i"])
        win = s["r"] < 0.85 * r["a"]
        for mc, acc in ((1, dep1), (cal["mc"], dep10)):
            rr_, pf = height_from_normals_radial(T.gradient_lut_invert(d, cal["pos"], win, min_count=mc), r["centre"], 0.8 * r["a"])
            acc.append(pf[-1] / (pk["R_px"] - math.sqrt(pk["R_px"] ** 2 - rr_[-1] ** 2)) - 1.0)
    dmc = (float(np.median(dep1)), float(np.median(dep10)))
    t_main2 = time.time() - t0
    # ── 17. 2 台目のパック
    t8 = time.time()
    p2 = os.path.join(root, "calibs", PACK2_DIR, "dataPack.npz")
    if os.path.isfile(p2):
        B = Pack(p2, PACK2_PITCH_MM, 2.00, n_test=12)
        calB = B.calibrate(B.train, flat=False, fit2=False)
        eB, resB = {"lin": [], "lut": [], "pos": []}, []
        for i in B.test:
            d, s = B.item(i)
            m = B.mask_eval(s)
            assert int(m.sum()) >= 300
            for k, nn in B.invert(calB, d, m).items():
                eB[k].append(float(np.median(T.normal_error_map(nn, s["normals"])[m])))
            resB.append(np.mean((T.membrane_predict_rgb(s["normals"], calB["fit"]) - d)[s["mask"]] ** 2))
        medB = {k: float(np.median(v)) for k, v in eB.items()}
        rmsB = float(np.sqrt(np.mean(resB)))
        rad, cnt = np.unique(B.pk["radii"], return_counts=True)
        gate("門 17 2 台目のパック(%d 枚、同じ手順): 線形の RGB 残差 %.1f DN = 1 台目の %.1f 倍(球半径の仮定に依らない量)/ 角誤差の順位 線形 %.1f° > "
             "位置なし LUT %.1f° > 位置つき LUT %.1f°(球 2.00 mm・%.4f mm/px の仮定つき = 絶対値は未検証、手当て半径の最頻 %d px が %d 枚 ≈ R %.1f px で頭打ち)"
             % (B.pk["n"], rmsB, rmsB / rms_lin, medB["lin"], medB["lut"], medB["pos"], PACK2_PITCH_MM, int(rad[np.argmax(cnt)]), int(cnt.max()), B.pk["R_px"]),
             medB["pos"] < medB["lut"] < medB["lin"] and rmsB / rms_lin >= THR["D_rms_ratio"])
        _NUM["D_pack2"] = {"rms": rmsB, "ratio": rmsB / rms_lin, "median": medB}
    else:
        skip("門 17 2 台目のパック", "%s の下に calibs/%s/dataPack.npz が無い" % (ENV_DATA, PACK2_DIR))
    t_p2 = time.time() - t8
    gate("門 18 実機の不感帯(真の傾き < 15° の画素の |Δθ| 中央値): 試作(平らな例あり・30 行以上のビンだけ)%.2f° → 借りる %.2f°(線形 %.2f°・位置なし LUT %.2f°)。"
         "代償に平地(接触の 2.8a〜3.2a)の傾きの床は %.1f° → %.1f°(小さい傾きと平らの色の差がノイズに埋もれる = 分解能の限界、両立しない)。使うビンの下限: 行 1 から "
         "= 深さ %+.1f %% / 行 %d から = %+.1f %%(4 枚)" % (bnd["old"], bnd["pos"], bnd["lin"], bnd["lut"], flm["old"], flm["pos"], 100 * dmc[0], cal["mc"], 100 * dmc[1]),
         bnd["pos"] <= THR["D_band_new"] and bnd["old"] - bnd["pos"] >= THR["D_band_gain"] and flm["pos"] <= THR["D_floor"] and flm["old"] <= THR["D_floor"]
         and dmc[0] - dmc[1] >= THR["D_mc_gain"])
    _NUM["D_deadband"] = {"band": bnd, "floor": flm, "depth_mc1": dmc[0], "depth_mc": dmc[1]}
    # ── 19. 粗 → 細 vs 総当たり(実機)
    same, dmed, te, tc = [], [], 0.0, 0.0
    for r in per[:6]:
        d, s = A.item(r["i"])
        m = A.mask_eval(s)
        ta = time.perf_counter()
        ne = T.gradient_lut_invert(d, cal["pos"], m, method="exact")
        tb = time.perf_counter()
        nc = T.gradient_lut_invert(d, cal["pos"], m)
        te, tc = te + tb - ta, tc + time.perf_counter() - tb
        same.append(T.normal_error_map(ne, nc)[m] < 1e-9)
        dmed.append(np.median(T.normal_error_map(nc, s["normals"])[m]) - np.median(T.normal_error_map(ne, s["normals"])[m]))
    fs_ = float(np.mean(np.concatenate(same)))
    gate("門 19 粗 → 細 vs 総当たり(実機 6 枚、ビン %d): 同じビン %.1f %%(色 → 法線は多峰)、角誤差の中央値の差 %+.3f°(最大 |%.3f|°)、速さ %.1f 倍"
         % (int((cal["pos"]["count"] > 0).sum()), 100 * fs_, float(np.median(dmed)), float(np.max(np.abs(dmed))), te / max(tc, 1e-9)),
         fs_ >= THR["D_same"] and float(np.max(np.abs(dmed))) <= THR["D_dmed"] and te / max(tc, 1e-9) >= THR["D_speed"])
    _NUM["D_coarse"] = {"same": fs_, "dmed": dmed, "speed": te / max(tc, 1e-9)}
    _NUM["time_data"] = {"main_s": t_main, "main_all_s": t_main2, "pack2_s": t_p2}
    print("  (データ門: 主パック %.1f s(較正と hold-out の逆引き %.1f s)+ 2 台目 %.1f s、この process の CPU 計 %.1f s)"
          % (t_main2, t_main, t_p2, time.process_time() - c0))
    out.update({"A": A, "cal": cal, "per": per, "fig_case": fig_case, "curve": curve, "poly": poly, "bgx": bgx})
    return out


# ======================================================================================================================
# 図(既定でも出る。等倍・縮小なし・減色なし)
def _hstack(panels, gap=6):
    Hm = max(p.shape[0] for p in panels)
    cols = []
    for k, p in enumerate(panels):
        p = np.repeat(p[..., None], 3, axis=2) if p.ndim == 2 else p
        cols.append(np.concatenate([p, np.full((Hm - p.shape[0], p.shape[1], 3), 255, np.uint8)], 0))
        if k < len(panels) - 1:
            cols.append(np.full((Hm, gap, 3), 255, np.uint8))
    return np.concatenate(cols, 1)


def _labels(img8, texts, xs, size=13):
    img = img8.astype(np.float64) / 255.0
    for t, x in zip(texts, xs):
        try:
            img = np.asarray(AN.text_box(img, t, (x + 3, 3), anchor="lt", font_size=size))
        except Exception as exc:  # noqa: BLE001  文字が収まらないときは図を落とさず素のパネル
            figs._errors.append("text_box: %r" % (exc,))
    return (np.clip(img, 0, 1) * 255).astype(np.uint8)


def _err8(E):
    return figs._to_rgb8(np.where(np.isfinite(E), E, 0.0), False, vrange=(0.0, 20.0))


def _shade(h_px, az_deg=315.0, el_deg=40.0):
    n = PH.surface_normals(h_px)
    az, el = math.radians(az_deg), math.radians(el_deg)
    v = np.clip(n @ np.array([math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)]), 0, 1)
    return (np.repeat(v[..., None], 3, axis=2) * 255).astype(np.uint8)


def _rgb_diff8(d, scale=60.0):
    return np.clip(np.asarray(d, np.float64) / scale * 127 + 128, 0, 255).astype(np.uint8)


def figures_synth(out):
    sy = out["synth"]
    c = sy["test"][1]
    s = T.sphere_normals_known((SH, SW), c, SA, SR)
    img = render_synth(s["normals"], 0.4)
    m = s["mask"]
    # 線形(同じ合成で較正)/ 位置なし LUT / 位置つき LUT
    rr, rn, rp = synth_rows(sy["train"], 0.4)
    D, N, M = [], [], []
    for cc in sy["train"]:
        ss = T.sphere_normals_known((SH, SW), cc, SA, SR)
        D.append(render_synth(ss["normals"], 0.4))
        N.append(ss["normals"])
        M.append(ss["mask"])
    fit = T.lights_fit_from_sphere(D, N, M)
    lut = sy["lut"]
    lut_np = {k: v for k, v in lut.items() if k != "coef"} | {"coef": None}
    inv = {"linear": T.linear_invert(img, fit), "LUT": T.gradient_lut_invert(img, lut_np, m), "LUT + position": T.gradient_lut_invert(img, lut, m)}
    panels, names = [_rgb_diff8(img)], ["synthetic press (gain +/-40%)"]
    for k, nn in inv.items():
        E = np.where(m, T.normal_error_map(nn, s["normals"]), np.nan)
        panels.append(_err8(E))
        names.append("%s %.2f deg" % (k, float(np.nanmedian(E))))
    w = SW + 6
    figs.save("tacscalib_synthetic_error_maps", _labels(_hstack(panels), names, [k * w for k in range(len(panels))]),
              caption="合成の押し込み(反射 max(n·l,0)^1.5、各灯は自分の側が ±40 %% 明るい)と、法線の角誤差の地図 0〜20°(等倍 %d×%d)。線形模型は反射の"
                      "非線形と位置の利得の両方を背負い、位置なし LUT は利得だけを背負う。位置つき LUT が残すのは 125 ビンの量子化だけ。" % (SW, SH))
    # 光を回す GIF: 位置つき LUT の法線を積分した高さ vs 真の球冠
    hw = 44                                                                    # 接触円(a = 37.5 px)が入る窓、画像の中に収める
    y0 = int(min(max(c[0] - hw, 0), SH - 2 * hw - 1))
    x0 = int(min(max(c[1] - hw, 0), SW - 2 * hw - 1))
    y1, x1 = y0 + 2 * hw + 1, x0 + 2 * hw + 1
    nc = inv["LUT + position"][y0:y1, x0:x1]
    z = PH.integrate_normals(nc)
    z -= np.median(z[:6, :])
    cap = T.sphere_cap_height(nc.shape[:2], (c[0] - y0, c[1] - x0), SA, SR, 1.0)["h"]
    frames = []
    for az in range(0, 360, 15):
        fr = _hstack([_rgb_diff8(img[y0:y1, x0:x1]), _shade(z, az), _shade(cap, az)])
        frames.append(_labels(fr, ["input", "recovered", "truth (cap)"], [0, (x1 - x0) + 6, 2 * (x1 - x0 + 6)], size=12))
    figs.save_gif("tacscalib_synthetic_relight", frames, fps=8.0,
                  caption="位置つき LUT の法線を Frankot–Chellappa で積分した面に光を 1 周させる(中央)、右は真の球冠。等倍 %d×%d、24 コマ。" % (x1 - x0, y1 - y0))
    # 不感帯の前後: 真の傾き vs 復元した傾き
    prof = out.get("band_profile") or {}
    series = [("truth", np.array([0.0, 15.0]), np.array([0.0, 15.0]))]
    styles, kinds = ["dashed"], ["line"]
    for key, lab in (("poly_only", "only bins with a position fit (prototype)"), ("pooled", "small bins borrow the position terms")):
        if key in prof:
            tt, tr = prof[key]
            o = np.argsort(tt)
            series.append((lab, tt[o][::3], tr[o][::3]))
            styles.append(None)
            kinds.append("scatter")
    figs.save_plot("tacscalib_deadband_before_after", series, xlabel="true tilt [deg]", ylabel="recovered tilt [deg]",
                   title="Small tilts: dead band of the positional LUT, before and after", kinds=kinds, styles=styles, xlim=(0, 15), ylim=(0, 30),
                   caption="合成の 1 球、真の傾き < 15° の画素。位置の 2 次式を当てたビン(8 行以上)だけで引くと小さい傾きのビンが全部落ち、0〜15° の"
                           "画素が位置の項を持つ傾きの大きいビン(この合成では 21° 以上)に吸われる。行の少ないビンが角度で最も近い多項式ビンの位置の項を"
                           "借りると真値の破線に乗る。")


def figures_data(out):
    A, cal, per, fc, curve = out["A"], out["cal"], out["per"], out["fig_case"], out["curve"]
    pk = A.pk
    i, y0, x0, hw = fc["i"], fc["y0"], fc["x0"], fc["hw"]
    sl = (slice(y0, y0 + 2 * hw + 1), slice(x0, x0 + 2 * hw + 1))
    raw = pk["imgs"][i][sl]
    d, s = A.item(i)
    z = fc["z"]
    rc = (pk["centers"][i][0] - y0, pk["centers"][i][1] - x0)
    cap = T.sphere_cap_height(z.shape, rc, pk["radii"][i], pk["R_px"], 1.0)["h"]
    zr = z - np.median(z[:8, :])
    lo = float(min(zr.min(), cap.min()))
    w = 2 * hw + 1 + 6
    p1 = _hstack([raw, _rgb_diff8(d[sl]), _shade(zr), _shade(cap), figs._to_rgb8(zr, False, vrange=(lo, 0.0)), figs._to_rgb8(cap, False, vrange=(lo, 0.0))])
    figs.save("tacscalib_real_frame_to_sphere", _labels(p1, ["real frame", "minus background", "recovered", "sphere cap (truth)", "recovered h", "truth h"],
                                                       [k * w for k in range(6)], size=12),
              caption="実機の hold-out 1 枚(枠 %d)→ 背景差分 → 位置つき LUT の法線を積分した面 → 真の球冠(R = 2.00 mm、手当ての円)。等倍 201×201。"
                      "最近傍の LUT なので段々が見え、接触円の外にも膜の裾が続く(球冠の模型は縁で 0)。" % i)
    frames = []
    for az in range(0, 360, 15):
        frames.append(_labels(_hstack([raw, _shade(zr, az), _shade(cap, az)]), ["real", "recovered", "truth"], [0, w, 2 * w], size=12))
    figs.save_gif("tacscalib_real_relight", frames, fps=8.0, caption="実機の 1 枚から復元した面に光を 1 周させる(中央)、右は真の球冠。等倍 201×201、24 コマ。")
    um = pk["pitch_mm"] * 1000
    figs.save_plot("tacscalib_height_profile", [("sphere cap (truth)", fc["rr"] * pk["pitch_mm"], fc["true"] * um),
                                                ("recovered: radial slope integral", fc["rr"] * pk["pitch_mm"], fc["prof"] * um)],
                   xlabel="r [mm]", ylabel="h(r) - h(0) [um]", title="Height profile up to r = 0.8a (frame %d)" % i, styles=["dashed", None],
                   caption="法線の半径スロープを方位平均して 1D 積分した断面と真の球冠(破線)。")
    # 残差地図と誤差地図(接触の窓、等倍)
    pred = T.membrane_predict_rgb(s["normals"], cal["fit"])
    pred2 = T.membrane_predict_rgb(s["normals"], cal["fit2"])
    rs1 = np.where(s["mask"], np.sqrt(np.mean((d - pred) ** 2, axis=2)), np.nan)
    rs2 = np.where(s["mask"], np.sqrt(np.mean((d - pred2) ** 2, axis=2)), np.nan)
    p2 = _hstack([_rgb_diff8(d[sl]), _rgb_diff8(np.where(s["mask"][..., None], pred, 0)[sl]),
                  figs._to_rgb8(np.nan_to_num(rs1[sl]), False, vrange=(0, 25)), figs._to_rgb8(np.nan_to_num(rs2[sl]), False, vrange=(0, 25))])
    figs.save("tacscalib_residual_maps", _labels(p2, ["diff (hold-out)", "linear model", "linear |resid| 0-25", "position-linear |resid|"],
                                                 [k * w for k in range(4)], size=12),
              caption="hold-out 1 枚の背景差分、線形模型の予測、残差の大きさ 0〜25 DN(線形 12 パラメタ / 位置つき 72 パラメタ)。線形の残差は左右で偏る。")
    m = s["mask"]
    inv = A.invert(cal, d, m, which=("lin", "lut", "old", "pos"))
    inv["ext"] = T.poly_lut_invert(pk["imgs"][i].astype(np.float64) - out["bgx"], out["poly"], m)
    panels, names = [], []
    for k, nm in (("lin", "linear"), ("lut", "LUT"), ("old", "LUT+pos (prototype)"), ("pos", "LUT+pos (borrow)"), ("ext", "external LUT*")):
        E = np.where(m, T.normal_error_map(inv[k], s["normals"]), np.nan)
        panels.append(_err8(E[sl]))
        names.append("%s %.1f" % (nm, float(np.nanmedian(E))))
    figs.save("tacscalib_angle_error_maps", _labels(_hstack(panels), names, [k * w for k in range(5)], size=11),
              caption="法線の角誤差 0〜20°(同じ hold-out 1 枚、等倍)。*外部の較正済み LUT は同じ 48 枚から作られている = hold-out でない参考値。")
    acc = {k: np.zeros((A.H, A.W)) for k in ("lin", "pos")}
    cnt = np.zeros((A.H, A.W))
    assert len(per) >= 1
    for r in per:
        d2, s2 = A.item(r["i"])
        m2 = s2["mask"]
        inv2 = A.invert(cal, d2, m2, which=("lin", "pos"))
        for k in acc:
            acc[k][m2] += T.normal_error_map(inv2[k], s2["normals"])[m2]
        cnt[m2] += 1
    maps = [_err8(np.where(cnt > 0, acc[k] / np.maximum(cnt, 1), np.nan)) for k in ("lin", "pos")]
    figs.save("tacscalib_sensor_plane_error", _labels(_hstack(maps), ["linear (0-20 deg)", "LUT + position"], [0, A.W + 6]),
              caption="hold-out %d 枚の角誤差をセンサ面の位置に置いた地図(等倍 %d×%d を 2 枚)。位置つき LUT は四隅で破れる(較正球の少ない所への外挿)。"
                      % (len(per), A.W, A.H))
    cen = np.array([r["centre"] for r in per])
    dd = np.hypot(cen[:, 0] - (A.H - 1) / 2, cen[:, 1] - (A.W - 1) / 2)
    figs.save_plot("tacscalib_position_scatter", [(k, dd, np.array([r[k]["med"] for r in per])) for k in ("lin", "lut", "pos")],
                   xlabel="contact centre distance from image centre [px]", ylabel="median angle error [deg]", kinds=["scatter"] * 3,
                   title="Where on the sensor it breaks", caption="接触中心の画像中心からの距離 vs 角誤差の中央値(hold-out 各 1 点)。")
    ks = sorted(curve)
    ser = [(k, np.array(ks, float), np.array([curve[q][k] for q in ks])) for k in ("lin", "lut", "pos")]
    ser += [("", x, y) for _, x, y in ser]                                     # 測った点(凡例に載せない)
    figs.save_plot("tacscalib_calibration_count", ser, kinds=["line"] * 3 + ["scatter"] * 3,
                   xlabel="calibration frames", ylabel="median angle error [deg]", title="How many calibration presses",
                   caption="較正枚数 1 / 4 / 24 枚(hold-out 4 枚)。線形は 1 枚でもほぼ同じ、位置つき LUT は位置の項に枚数が要る。")
    big = s["r"] < 1.8 * pk["radii"][i]
    series = []
    for k, lab, mc in (("old", "LUT + position (prototype)", 30), ("pos", "LUT + position, borrow + flat", cal["mc"])):
        nn = T.gradient_lut_invert(d, cal[k], big, min_count=mc)
        rr, pr = radial_profile(np.degrees(T.normals_to_angles(nn)[0]), pk["centers"][i], 1.8 * pk["radii"][i])
        series.append((lab, rr, pr))
    rr, pr = radial_profile(np.degrees(s["theta"]), pk["centers"][i], 1.8 * pk["radii"][i])
    series.append(("sphere cap model (0 outside a)", rr, pr))
    figs.save_plot("tacscalib_where_it_breaks", series, xlabel="r [px]", ylabel="tilt [deg]", styles=[None, None, "dashed"],
                   title="Radial tilt: dead band near the centre, membrane skirt outside a",
                   caption="半径方向の傾き(方位平均)。試作(平らな例あり・30 行以上のビンだけ)は中心付近の小さい傾きが 0 か 15° に寄る(不感帯)。"
                           "行の少ないビンが近いビンの位置の項を借りると真値の破線に乗るが、平地には約 3° の床が残る(分解能の限界)。a の外では実機の膜は"
                           "傾き続ける(球冠の模型は 0)= 深さの門を 0.8a までに限る理由。")


# ======================================================================================================================
def main() -> int:
    t_all = time.time()
    out = numpy_part()
    root = os.environ.get(ENV_DATA, "").strip()
    if FULL:
        if root and os.path.isfile(os.path.join(root, "calibs", "dataPack.npz")):
            out = data_part(out, root)
        else:
            skip("門 10〜19(実機データ)", "環境変数 %s が未設定か、その下に calibs/dataPack.npz が無い" % ENV_DATA)
    else:
        skip("門 10〜19(実機データ)", "--full のときだけ(%s)" % ENV_DATA)
    if figs.enabled():
        figures_synth(out)
        if "A" in out:
            figures_data(out)
        print("  figures:", figs.errors() or "ok")
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    n_ng = sum(1 for _, ok in _GATES if not ok)
    print("gates: %d / %d ok  (%.1f s)" % (len(_GATES) - n_ng, len(_GATES), time.time() - t_all))
    if MEASURE:
        return 0
    if n_ng or figs.errors():
        print("FAIL")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
