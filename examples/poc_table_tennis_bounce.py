# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC ㉕: 跳ねる卓球の球を高速カメラで撮って、反発係数と摩擦係数を読む —— 公表値と照合する。

卓球の球が台で跳ねると、縦の速さは反発係数 e の分だけ残り、横の速さと回転は摩擦で入れ替わる。回転が合っていれば
接地点が止まって「転がり」に移り、合っていなければ滑ったまま離れる。この PoC は台の上の跳ねを 1 台の高速カメラ
(1000 fps、横から)で撮り、**画像だけから** e と摩擦係数 μ と跳ねの種類(転がりに移ったか・滑ったままか)を読み、
公表値と照合する。

門(真値の出どころ):
  1. **Cross 2002 の閉形式**(薄い殻の球 I = (2/3) m r²): 転がりに移る跳ねは v_x' = 0.6 v_x + 0.4 rω、滑ったままの跳ねは
     Δv_t = μ(1+e)|v_z|、境目は (2/5)|s| = μ(1+e)|v_z|(s = 接地点の滑りの速さ)。bounce の力積の実装(形が違う第 2 実装)と
     乱数 300 通りで 1e-12。
  2. **ITTF の台の跳ね**(公表値): 30 cm から落とした球が約 23 cm 跳ねる(Laws 2.1.3)。動画から読んだ跳ねの高さが 23 ± 1 cm。
  3. **反発係数の速さへの依存**(公表値): 打ち込む速さを変えて動画から読んだ e(v) の傾きが、Inaba ら 2017 の実測
     −0.0058 /(km/h)と 10 % 以内。
  4. **摩擦係数**: 滑ったままの跳ねで μ = Δv_t /((1+e)|v_z|)(Inaba らの式)が真値 0.25 と 5 % 以内。
  5. **跳ねの種類**: 動画から読んだ種類が、読んだ e と μ で引いた閉形式の境目と一致(境目の ±10 % の帯は除く)。
  6. **転がり**: 転がりに移った跳ねは、跳ねた後の rω'(模様から)と v_x'(軌跡から)が 3 % 以内で一致。
  7. **零点**: 摩擦の無い台(μ = 0)では、横の速さも回転も跳ねで変わらない。

正直に書くこと: 合成映像(色が既知、実写の照明・ぼけ無し)。台の e(v) は 2 つの公表値を継いだ合成 —— ITTF の台の跳ね
(30 cm → 約 23 cm)を抗力込みで満たす e を切片に、Inaba らの傾きを速さへの依存にした。★抵抗を無視した e = √(23/30) = 0.876 では
上り下りの抗力で 1 cm 余り足りない。★Inaba らの直線そのもの(切片 1.0002)は ITTF より高く跳ねる側にずれる(実行時に cm で出す)
—— 研究室の台と規格の差か、測り方の差かは確かめていない。μ は定数(Inaba らの
実測は接地点の速さで 0.27〜0.44 に増える)。球の変形(座屈は 5.5 m/s から、Rémond ら 2022)は入れず、縦の速さを 4.5 m/s までにした。

Run: py -3.11 examples/poc_table_tennis_bounce.py   (図は FULLSEYE_FIGURE_DIR を設定したときだけ書く。MP4 は extras [video] があるときだけ)
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs  # noqa: E402
import ballistics as B  # noqa: E402
import balltrack as BT  # noqa: E402
import ballworld as BW  # noqa: E402
import driveworld as DW  # noqa: E402
import lidarsim as LS  # noqa: E402
import annotate as AN  # noqa: E402

T0 = time.time()
FPS = 1000
WIN = 0.040                            # 跳ねの前後に撮る長さ [s]
CAM_W, CAM_H, CAM_FOV, CAM_DIST = 640, 400, 40.0, 0.8
ROI = 112
BALL_COLOR = (1.0, 0.55, 0.05)
MU_TRUE = 0.25
#: ITTF の台の跳ね(30 cm → 約 23 cm)を満たす e と、その落下の衝突の速さ [km/h]。★空気抵抗を無視した √(23/30) = 0.876 では
#:   上り下りの抵抗で 1.2 cm 足りない(21.8 cm)ので、main の最初に抵抗込みで解き直す(_calibrate_ittf)。
E_ITTF, V_ITTF = 0.876, 8.74
INABA_SLOPE = -0.0058                  # Inaba ら 2017(プラスチック球): de/dv [1/(km/h)]
MARKERS = [((1, 0, 0), 11.0), ((-1, 0, 0), 11.0), ((0, 1, 0), 11.0), ((0, -1, 0), 11.0), ((0, 0, 1), 11.0), ((0, 0, -1), 11.0)]
MARKERS += [((sx, sy, sz), 11.0) for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]
OK = []


def gate(name, cond, detail=""):
    OK.append(bool(cond))
    print("  [%s] %s %s" % ("PASS" if cond else "FAIL", name, detail))


def e_table(vn):
    """台の反発係数(合成): ITTF の切片 + Inaba らの傾き。vn = 衝突の縦の速さ [m/s]。"""
    return float(np.clip(E_ITTF + INABA_SLOPE * (3.6 * abs(vn) - V_ITTF), 0.0, 1.0))


def _drop_rebound(e0, bp, H):
    """球の下端を 30 cm から落とし、定数の e0 で跳ねた後の頂点(下端の高さ)と衝突の速さ [km/h](抗力込み)。"""
    r = bp["radius"]
    sim = B.flight_simulate([0.0, 0.0, H + r + 0.30], [0, 0, 0], [0, 0, 0], bp, B.impact_params(e0, 0.25), 0.62, 1e-4, table_z=H)
    c = sim["contacts"][0]
    return float(sim["p"][sim["t"] > c["t"], 2].max() - H - r), 3.6 * abs(c["v_in"][2])


def _calibrate_ittf(bp, H):
    """ITTF の約 23 cm を抗力込みで満たす e(2 分法)を E_ITTF・V_ITTF に入れる。返り値 = (抵抗を無視した √(23/30) の跳ね, Inaba らの直線そのものの跳ね)。"""
    global E_ITTF, V_ITTF
    lo, hi = 0.8, 0.99
    for _ in range(40):
        m = 0.5 * (lo + hi)
        if _drop_rebound(m, bp, H)[0] < 0.23:
            lo = m
        else:
            hi = m
    E_ITTF = 0.5 * (lo + hi)
    V_ITTF = _drop_rebound(E_ITTF, bp, H)[1]
    return _drop_rebound(np.sqrt(0.23 / 0.30), bp, H)[0], _drop_rebound(1.0002 + INABA_SLOPE * V_ITTF, bp, H)[0]


def _interp(sim, key, t):
    return np.column_stack([np.interp(np.atleast_1d(t), sim["t"], sim[key][:, k]) for k in range(3)])


def _poses(sim, t_frames, R0):
    W = _interp(sim, "omega", t_frames)
    R, out = R0.copy(), []
    for k in range(len(t_frames)):
        if k:
            R = BW.rotation_from_omega(W[k - 1], t_frames[k] - t_frames[k - 1]) @ R
        out.append(R.copy())
    return out


def _pixel_to_plane(uv, pose, K, plane):
    """画素 (col, row) の視線と平面 ax + by + cz + d = 0 の交点(世界座標)。投影行列 [A | b] から視線を出すので、
    カメラ座標の向きの約束に依らない: X(λ) = A⁻¹(λ[u, v, 1] − b)、中心 = −A⁻¹b。"""
    M = BT._projection_matrix(pose, K)                     # render3d の規約(カメラは −Z を向き、行は下向き)込み
    A, b = M[:, :3], M[:, 3]
    C = -np.linalg.solve(A, b)
    d = np.linalg.solve(A, np.array([uv[0], uv[1], 1.0]))
    rng = LS.ray_plane_range(C, d / np.linalg.norm(d), plane)
    return C + float(rng) * d / np.linalg.norm(d)


def _film(world, ball, sim, t_frames, cam, R0):
    """1 台のカメラで撮る(ROI 読み出し: 前 2 コマの等速予測の周り ROI px。最初と見失ったコマは全画面)。
    返り値: コマごとの (中心 (col, row), 半径 px, 模様の向き(カメラの系、2 個以上見えたときだけ)) と全画面の読み直し数。"""
    P = _interp(sim, "p", t_frames)
    Rs = _poses(sim, t_frames, R0)
    out, hist, n_full = [], [], 0
    for k in range(len(t_frames)):
        BW.ball_set_pose(world, ball, P[k], Rs[k])
        img, x0, y0, K = None, 0, 0, cam["K"]
        if len(hist) >= 2:
            (c1, r1), (c2, r2) = hist[-2], hist[-1]
            x0 = int(np.clip(round(2 * c2 - c1) - ROI // 2, 0, CAM_W - ROI))
            y0 = int(np.clip(round(2 * r2 - r1) - ROI // 2, 0, CAM_H - ROI))
            K = np.array(cam["K"], dtype=np.float64)
            K[0, 2] -= x0
            K[1, 2] -= y0
            img = np.asarray(DW.world_camera(world, cam["pose"], K, ROI, ROI, ambient=0.7)["color"])
            d = BT.ball_detect(img, mode="chroma", color=BALL_COLOR, color_tol=0.2, radius_range=(6, 60))
            if not d or d[0]["col"] - d[0]["radius"] < 1 or d[0]["col"] + d[0]["radius"] > ROI - 2 \
                    or d[0]["row"] - d[0]["radius"] < 1 or d[0]["row"] + d[0]["radius"] > ROI - 2:
                img = None                                      # 見失った / ROI の縁で欠けた → 全画面で読み直す
        if img is None:
            n_full += 1
            x0 = y0 = 0
            K = cam["K"]
            img = np.asarray(DW.world_camera(world, cam["pose"], K, CAM_W, CAM_H, ambient=0.7)["color"])
            d = BT.ball_detect(img, mode="chroma", color=BALL_COLOR, color_tol=0.2, radius_range=(6, 60))
        if not d:
            out.append(None)
            continue
        cb, rb = (d[0]["col"], d[0]["row"]), d[0]["radius"] + 0.5
        hist.append((cb[0] + x0, cb[1] + y0))
        hh, ww = img.shape[:2]
        rr, cc = np.mgrid[0:hh, 0:ww]
        inside = np.hypot(cc - cb[0], rr - cb[1]) < rb * 0.85
        marks = BT.ball_detect(np.where(inside, img.mean(-1), 1.0), mode="dark", thresh=0.2, radius_range=(1.0, 10))
        dirs = np.asarray([BT.marker_direction((m["col"], m["row"]), cb, rb, K) for m in marks]) if len(marks) >= 2 else None
        out.append(((cb[0] + x0, cb[1] + y0), rb, dirs))
    return out, n_full


def _contact_time(fit, omega, bp, H, t_lo, t_hi):
    """当てはめた飛翔が中心の高さ H + r に達する時刻(2 分法)。"""
    def z(t):
        return B.flight_state_at(fit["p0"], fit["v0"], omega, bp, t - fit["t0"])["p"][2] - (H + bp["radius"])
    a, b = t_lo, t_hi
    za, zb = z(a), z(b)
    if za * zb > 0:
        return None
    for _ in range(60):
        m = 0.5 * (a + b)
        zm = z(m)
        if za * zm <= 0:
            b, zb = m, zm
        else:
            a, za = m, zm
    return 0.5 * (a + b)


def measure(throw, bp, tp, mu=MU_TRUE):
    """1 本の跳ねを撮って測る。返り値は真値(世界)と測った値(画像だけから)の辞書。"""
    H = tp["height"]
    ip = B.impact_params(e_table, mu)
    world = BW.table_world(tp)
    xc = 0.6                                              # 跳ねる点(台の中心から x = 0.6 m、ネットの向こう側)
    vx, vz, wy = throw["vx"], throw["vz"], throw["wy"]
    t_pre = 0.06
    p0 = np.array([xc - vx * t_pre, 0.0, H + bp["radius"] + vz * t_pre + 0.5 * 9.81 * t_pre ** 2])
    if throw.get("drop") is not None:
        p0 = np.array([xc, 0.0, H + bp["radius"] + throw["drop"]])
        v0 = np.zeros(3)
    else:
        v0 = np.array([vx, 0.0, -vz])
    w0 = np.array([0.0, wy, 0.0])
    t_end = np.sqrt(2 * throw["drop"] / 9.81) + 0.35 if throw.get("drop") is not None else 0.2
    sim = B.flight_simulate(p0, v0, w0, bp, ip, t_end, 1e-4, table_z=H, table_xy=world["bounds"])
    c0 = sim["contacts"][0]
    t_frames = c0["t"] + np.arange(-WIN, WIN + 1e-9, 1.0 / FPS)
    target = np.array([c0["p"][0], 0.0, H + 0.04])
    cam = {"pose": DW.camera_pose(target + np.array([0.0, -CAM_DIST, 0.08]), target), "K": DW.camera_intrinsics(CAM_FOV, CAM_W, CAM_H)}
    ball = BW.add_ball(world, BW.ball_mesh(bp["radius"], 3, BALL_COLOR, markers=MARKERS), p0, np.eye(3))
    obs, n_full = _film(world, ball, sim, t_frames, cam, np.eye(3))
    # ── 画像だけから ──
    ok = [k for k, o in enumerate(obs) if o is not None]
    tt = t_frames[ok]
    P = np.asarray([_pixel_to_plane(obs[k][0], cam["pose"], cam["K"], (0.0, 1.0, 0.0, 0.0)) for k in ok])
    bd = BT.bounce_detect(tt, P[:, 2], min_gap=2)
    zb = np.interp(bd["t"], tt, P[:, 2]) if len(bd["t"]) else np.zeros(0)
    t_b = float(bd["t"][int(np.argmin(zb))]) if len(zb) else float(tt[int(np.argmin(P[:, 2]))])
    pre = tt < t_b - 2.5e-3
    post = tt > t_b + 2.5e-3
    Rc = np.asarray(cam["pose"])[:3, :3]
    dirs = [obs[k][2] if obs[k] is not None else None for k in range(len(obs))]
    kb = int(np.searchsorted(t_frames, t_b))
    w_pre = BT.spin_from_marker_sequence(dirs[:max(0, kb - 2)], 1.0 / FPS)
    w_post = BT.spin_from_marker_sequence(dirs[kb + 3:], 1.0 / FPS)
    W_pre = Rc.T @ w_pre["omega"] if w_pre["n_pairs"] else np.zeros(3)
    W_post = Rc.T @ w_post["omega"] if w_post["n_pairs"] else np.zeros(3)
    fa = B.flight_fit(tt[pre], P[pre], W_pre, bp)
    fb = B.flight_fit(tt[post], P[post], W_post, bp)
    t_c = _contact_time(fa, W_pre, bp, H, t_b - 0.01, t_b + 0.005) or t_b
    s_in = B.flight_state_at(fa["p0"], fa["v0"], W_pre, bp, t_c - fa["t0"])
    s_out = B.flight_state_at(fb["p0"], fb["v0"], W_post, bp, t_c - fb["t0"])
    v_in, v_out = s_in["v"], s_out["v"]
    e_m = -v_out[2] / v_in[2]
    r = bp["radius"]
    slip_in = v_in[0] - r * W_pre[1]                     # 接地点の滑りの速さ(x、ω は y まわり)
    slip_out = v_out[0] - r * W_post[1]
    dvt = v_out[0] - v_in[0]
    mu_app = abs(dvt) / ((1.0 + e_m) * abs(v_in[2]))
    res = {"throw": throw, "sim": sim, "contact": c0, "cam": cam, "world": world, "ball": ball, "t_frames": t_frames, "obs": obs,
           "n_full": n_full, "e_true": e_table(c0["v_in"][2]),
           "regime_true": c0["regime"], "v_in": v_in, "v_out": v_out, "w_pre": W_pre, "w_post": W_post, "e": e_m,
           "vz_kmh": 3.6 * abs(v_in[2]), "slip_in": slip_in, "slip_out": slip_out, "mu_app": mu_app, "dvt": dvt,
           "rms": (fa["rms"], fb["rms"]), "n_pre": int(pre.sum()), "n_post": int(post.sum())}
    if throw.get("drop") is not None:
        # 跳ねの高さ: 跳ねた後の当てはめを頂点まで進める(球の下端で測る —— ITTF と同じ)
        st = B.flight_state_at(fb["p0"], fb["v0"], W_post, bp, t_c - fb["t0"])
        f = B.flight_ode(st["p"], st["v"], W_post, bp, 0.6, 1e-4)
        res["rebound"] = float(f["p"][:, 2].max() - H - r)
        res["rebound_true"] = float(sim["p"][sim["t"] > c0["t"], 2].max() - H - r)
    return res


def main() -> int:
    """PoC の本体(examples の門: 実行は __main__ の守りの下で)。"""
    bp = B.ball_params()
    tp = BW.table_params()
    H = tp["height"]
    r = bp["radius"]

    # ─────────────────────────────── 1. Cross 2002 の閉形式 ─────────────────────────────
    print("== 1. 跳ねの閉形式(Cross 2002、薄い殻の球 I = (2/3) m r²)と bounce の力積の実装を突き合わせる")
    rng = np.random.default_rng(25)
    worst, agree, n_grip = 0.0, 0, 0
    for _ in range(300):
        v = np.array([rng.uniform(-6, 6), rng.uniform(-2, 2), -rng.uniform(0.5, 6)])
        w = rng.normal(0, 250, 3)
        e, mu = rng.uniform(0.6, 0.95), rng.uniform(0.05, 0.5)
        b = B.bounce(v, w, [0, 0, 1], bp, B.impact_params(e, mu))
        s = v[:2] - r * np.array([w[1], -w[0]])            # 接地点の滑り(ω × n の接線成分 = (ω_y, −ω_x))
        sm = np.linalg.norm(s)
        grip = 0.4 * sm <= mu * (1 + e) * abs(v[2])
        if grip:                                             # 転がりに移る: v_t' = 0.6 v_t + 0.4 r(ω × n)_t
            vt2 = 0.6 * v[:2] + 0.4 * r * np.array([w[1], -w[0]])
            n_grip += 1
        else:                                                # 滑ったまま: Δv_t = −μ(1+e)|v_z| ŝ
            vt2 = v[:2] - mu * (1 + e) * abs(v[2]) * s / sm
        worst = max(worst, float(np.abs(b["v"][:2] - vt2).max()), abs(b["v"][2] + e * v[2]))
        agree += (b["regime"] == ("grip" if grip else "slip"))
    print("  乱数 300 通り(e ∈ [0.6, 0.95]、μ ∈ [0.05, 0.5]): 種類の一致 %d / 300(転がりに移る %d)、速度の差 最大 %.1e m/s" % (agree, n_grip, worst))
    gate("Cross 2002 の閉形式 = bounce の力積(種類 300/300、速度 1e-12)", agree == 300 and worst < 1e-12)

    naive, inaba = _calibrate_ittf(bp, H)
    print("  世界の台: ITTF の約 23 cm を抗力込みで満たす e = %.4f(衝突 %.2f km/h)。抵抗を無視した √(23/30) = %.4f では %.1f cm しか跳ねない"
          "(上り下りの抗力が %.1f cm 奪う)。速さへの依存は Inaba らの傾き %.4f /(km/h)" % (
              E_ITTF, V_ITTF, np.sqrt(0.23 / 0.30), 100 * naive, 100 * (0.23 - naive), INABA_SLOPE))
    print("  Inaba らの直線そのもの(e = 1.0002 − 0.0058 v = %.3f)なら 30 cm から %.1f cm 跳ねる —— ITTF の約 23 cm と公表値同士で食い違う" % (
        1.0002 + INABA_SLOPE * V_ITTF, 100 * inaba))

    # ─────────────────────────────── 2. 撮る ─────────────────────────────
    throws = [{"name": "落下 %d cm" % round(100 * h), "drop": h, "vx": 0.0, "vz": 0.0, "wy": 0.0} for h in (0.10, 0.20, 0.30, 0.50, 0.75, 1.00)]
    for vz in (2.5, 4.0):
        for vx in (3.0, 5.0):
            for wy in (-150.0, 0.0, 100.0, 200.0):
                throws.append({"name": "v = (%.0f, %.1f) m/s、ω = %+.0f rad/s" % (vx, vz, wy), "drop": None, "vx": vx, "vz": vz, "wy": wy})
    print("== 2. 台の上の跳ね %d 本を横から 1 台のカメラ(%d fps、%d × %d、ROI %d px)で撮り、画像だけから測る" % (len(throws), FPS, CAM_W, CAM_H, ROI))
    t_r = time.time()
    res = [measure(th, bp, tp) for th in throws]
    print("  撮影と計測 %.1f s(全画面で読み直したコマ %d)" % (time.time() - t_r, sum(x["n_full"] for x in res)))
    for x in res:
        print("  %-28s e = %.4f(真値 %.4f)、v_z %.1f km/h、滑り %+.2f → %+.2f m/s、Δv_t %+.3f、見かけの μ %.3f、%s(真値 %s)" % (
            x["throw"]["name"], x["e"], e_table(x["contact"]["v_in"][2]), x["vz_kmh"], x["slip_in"], x["slip_out"], x["dvt"], x["mu_app"],
            "滑る" if abs(x["slip_out"]) > 0.15 else "転がる", "転がる" if x["regime_true"] == "grip" else "滑る"))

    # ─────────────────────────────── 3. ITTF の台の跳ね ─────────────────────────────
    print("== 3. ITTF の台の跳ね: 30 cm から落とす(Laws 2.1.3「約 23 cm」)")
    d30 = [x for x in res if x["throw"].get("drop") == 0.30][0]
    print("  動画から読んだ跳ねの高さ %.1f cm(世界の真値 %.1f cm)、e = %.4f、衝突の速さ %.2f km/h" % (
        100 * d30["rebound"], 100 * d30["rebound_true"], d30["e"], d30["vz_kmh"]))
    gate("ITTF: 30 cm から落として 23 ± 1 cm", abs(d30["rebound"] - 0.23) <= 0.01)

    # ─────────────────────────────── 4. e(v) の傾き ─────────────────────────────
    print("== 4. 反発係数の速さへの依存(Inaba ら 2017: −0.0058 /(km/h))")
    vv = np.array([x["vz_kmh"] for x in res])
    ee = np.array([x["e"] for x in res])
    A = np.column_stack([vv - V_ITTF, np.ones_like(vv)])
    slope, icpt = np.linalg.lstsq(A, ee, rcond=None)[0]
    e_err = np.abs(ee - np.array([e_table(x["contact"]["v_in"][2]) for x in res]))
    print("  %d 本、v_z %.1f〜%.1f km/h: 傾き %.5f /(km/h)(Inaba %.4f、差 %.1f %%)、%.2f km/h での e %.4f(ITTF の切片 %.3f)。1 本ごとの e の誤差 中央値 %.4f・最大 %.4f" % (
        len(vv), vv.min(), vv.max(), slope, INABA_SLOPE, 100 * abs(slope / INABA_SLOPE - 1), V_ITTF, icpt, E_ITTF, np.median(e_err), e_err.max()))
    gate("e(v) の傾きが Inaba らの −0.0058 と 10 % 以内", abs(slope / INABA_SLOPE - 1) < 0.10)

    # ─────────────────────────────── 5. μ と跳ねの種類 ─────────────────────────────
    print("== 5. 摩擦係数(滑ったままの跳ねで μ = Δv_t /((1+e)|v_z|))と跳ねの種類")
    obl = [x for x in res if x["throw"].get("drop") is None]
    slipping = [x for x in obl if abs(x["slip_out"]) > 0.3 * abs(x["slip_in"])]
    mu_m = float(np.median([x["mu_app"] for x in slipping])) if slipping else float("nan")
    print("  はっきり滑った %d 本(跳ねた後も滑りが入射の 30 %% 以上)の見かけの μ: %s → 中央値 %.4f(真値 %.2f)" % (
        len(slipping), np.round([x["mu_app"] for x in slipping], 3).tolist(), mu_m, MU_TRUE))
    gate("μ が真値 0.25 と 5 % 以内", abs(mu_m / MU_TRUE - 1) < 0.05)
    agree, band, n_cls = 0, 0, 0
    for x in obl:
        thr = 2.5 * mu_m * (1 + x["e"]) * abs(x["v_in"][2])      # 境目: |s| = (5/2) μ (1+e) |v_z|
        if abs(abs(x["slip_in"]) / thr - 1) < 0.10:
            band += 1
            continue
        pred = "grip" if abs(x["slip_in"]) <= thr else "slip"
        meas = "slip" if abs(x["slip_out"]) > 0.15 else "grip"
        n_cls += 1
        agree += pred == meas
        x["regime_pred"], x["regime_meas"] = pred, meas
    print("  種類: 閉形式の境目(読んだ e・μ で引く)と動画の読みの一致 %d / %d(境目の ±10 %% の帯で除いた %d 本)" % (agree, n_cls, band))
    gate("跳ねの種類が閉形式の境目と一致", n_cls >= 10 and agree == n_cls)
    grips = [x for x in obl if x.get("regime_meas") == "grip"]
    roll = [abs(r * x["w_post"][1] - x["v_out"][0]) / abs(x["v_out"][0]) for x in grips]
    print("  転がりに移った %d 本: 跳ねた後の rω'(模様から)と v_x'(軌跡から)の差 %s %%" % (len(grips), np.round(100 * np.array(roll), 2).tolist()))
    gate("転がり: rω' と v_x' が 3 % 以内", len(grips) >= 3 and max(roll) < 0.03)

    # ─────────────────────────────── 6. 零点 ─────────────────────────────
    print("== 6. 零点: 摩擦の無い台(μ = 0)")
    z0 = measure({"name": "μ = 0", "drop": None, "vx": 4.0, "vz": 3.0, "wy": -150.0}, bp, tp, mu=0.0)
    dw = abs(z0["w_post"][1] - z0["w_pre"][1]) / 150.0
    print("  Δv_t %+.4f m/s、回転 %.1f → %.1f rad/s(変化 %.1f %%)" % (z0["dvt"], z0["w_pre"][1], z0["w_post"][1], 100 * dw))
    gate("零点: μ = 0 では Δv_t < 0.03 m/s・回転の変化 < 3 %", abs(z0["dvt"]) < 0.03 and dw < 0.03)

    if figs.enabled():
        print("== 7. 図と動画")
        t_f = time.time()
        _figures(res, bp, tp, slope, icpt, mu_m, d30)
        print("  図と動画(%.1f s)" % (time.time() - t_f))
        if figs.errors():
            print("図の書き出しで失敗:", "; ".join(figs.errors()))
            OK.append(False)
    print("所要 %.1f s" % (time.time() - T0))
    print("SUMMARY: %d / %d gates PASS" % (sum(OK), len(OK)))
    print("PASS" if all(OK) else "FAIL")
    return 0 if all(OK) else 1


def _hline(img, row, x0, x1, color, width=1):
    h, w = img.shape[:2]
    r0 = int(round(row))
    for dr in range(width):
        if 0 <= r0 + dr < h:
            img[r0 + dr, max(0, int(x0)):min(w, int(x1))] = color


def _figures(res, bp, tp, slope, icpt, mu_m, d30):
    H = tp["height"]
    r = bp["radius"]
    # (1) ITTF の落下試験(物差しつき、横から、240 fps で撮って 1/8 スロー)
    world = BW.table_world(tp)
    sim = d30["sim"]
    ball = BW.add_ball(world, BW.ball_mesh(r, 3, BALL_COLOR, markers=MARKERS), sim["p"][0], np.eye(3))
    target = np.array([d30["contact"]["p"][0], 0.0, H + 0.17])
    pose = DW.camera_pose(target + np.array([0.0, -1.1, 0.0]), target)
    K = DW.camera_intrinsics(26.0, 640, 480)
    xg = d30["contact"]["p"][0] - 0.09
    frames = []
    t_all = np.arange(0.0, min(sim["t"][-1], d30["contact"]["t"] + 0.48), 1.0 / 240)
    for t in t_all:
        p = _interp(sim, "p", t)[0]
        BW.ball_set_pose(world, ball, p, np.eye(3))
        img = np.array(DW.world_camera(world, pose, K, 640, 480)["color"], dtype=np.float64)
        for cm in range(0, 36):                                  # 物差し: 1 cm 刻み、5 cm ごとに長く
            uv = BT.reproject(np.array([[xg, 0.0, H + 0.01 * cm]]), pose, K)[0]
            L = 18 if cm % 5 == 0 else 8
            _hline(img, uv[1], uv[0] - L, uv[0], (1.0, 1.0, 1.0))
        for h_mark, col, lab in ((0.30, (0.9, 0.9, 0.2), "30 cm(落とす高さ)"), (0.23, (0.3, 0.9, 1.0), "約 23 cm(ITTF の台の跳ね)")):
            uv = BT.reproject(np.array([[xg, 0.0, H + h_mark]]), pose, K)[0]
            _hline(img, uv[1], uv[0] + 4, uv[0] + 150, col, 2)
            img = np.asarray(AN.text_box(img, lab, (int(uv[0]) + 155, int(uv[1]) - 10), font_size=13, text_color=col), dtype=np.float64)
        bottom = p[2] - r - H
        img = np.asarray(AN.text_box(img, "t = %3.0f ms  1/8 スロー  球の下端の高さ %4.1f cm" % (1e3 * t, 100 * bottom), (10, 10), font_size=15), dtype=np.float64)
        frames.append(np.clip(img, 0, 1))
    figs.save_video("drop_test", frames, fps=30.0, gif_every=3, gif_width=480,
                    caption="ITTF の台の跳ねの試験(Laws 2.1.3: 30 cm から落として約 23 cm)。球の下端を 30 cm から落とし、動画から読んだ跳ねの高さは "
                            "%.1f cm(世界の真値 %.1f cm)。物差しは 1 cm 刻み。MP4 = 240 fps の全コマ(1/8 スロー)。" % (100 * d30["rebound"], 100 * d30["rebound_true"]))

    # (2) バックスピンの跳ね(滑る)と (3) トップスピンの跳ね(転がりに移る)の近接
    def closeup(x, name, caption):
        obs, tf = x["obs"], x["t_frames"]
        wv = x["world"]
        sim_ = x["sim"]
        Rs = _poses(sim_, tf, np.eye(3))
        cu = BT.reproject(np.array([x["contact"]["p"]]), x["cam"]["pose"], x["cam"]["K"])[0]   # 表示だけ: 跳ねる点の周りを 2 倍に
        cx0 = int(np.clip(round(cu[0]) - CAM_W // 4, 0, CAM_W // 2))
        cy0 = int(np.clip(round(cu[1]) - CAM_H // 4 - 20, 0, CAM_H // 2))
        fr = []
        for k, t in enumerate(tf):
            BW.ball_set_pose(wv, x["ball"], _interp(sim_, "p", t)[0], Rs[k])
            img = np.array(DW.world_camera(wv, x["cam"]["pose"], x["cam"]["K"], CAM_W, CAM_H, ambient=0.7)["color"], dtype=np.float64)
            if obs[k] is not None:
                c = obs[k][0]
                img = np.asarray(AN.crosshair(img, (float(c[0]), float(c[1])), color="emphasis", width=1, gap=int(obs[k][1]) + 3,
                                              extent=int(obs[k][1]) + 10), dtype=np.float64)
            img = np.kron(img[cy0:cy0 + CAM_H // 2, cx0:cx0 + CAM_W // 2], np.ones((2, 2, 1)))
            side = "跳ねる前" if t < x["contact"]["t"] else "跳ねた後"
            wtxt = x["w_pre"][1] if t < x["contact"]["t"] else x["w_post"][1]
            img = np.asarray(AN.text_box(img, "1000 fps  t = %+3.0f ms  %s  模様から ω = %+.0f rad/s" % (1e3 * (t - x["contact"]["t"]), side, wtxt),
                                         (8, 8), font_size=14), dtype=np.float64)
            fr.append(np.clip(img, 0, 1))
        figs.save_video(name, fr, fps=25.0, gif_every=2, gif_width=480, caption=caption)

    back = [x for x in res if x["throw"]["name"] == "v = (5, 4.0) m/s、ω = -150 rad/s"][0]
    top = [x for x in res if x["throw"]["name"] == "v = (3, 2.5) m/s、ω = +200 rad/s"][0]
    closeup(back, "backspin_bounce",
            "バックスピン(ω = −150 rad/s)の跳ね(当たる瞬間 v = (%.1f, −%.1f) m/s)、1000 fps を 1/40 スローで。接地点が大きく滑ったまま離れる(滑り %+.2f → %+.2f m/s)。"
            "模様から読んだ回転 %+.0f → %+.0f rad/s、横の速さの減り %.3f m/s → 見かけの μ %.3f。" % (
                back["v_in"][0], abs(back["v_in"][2]), back["slip_in"], back["slip_out"], back["w_pre"][1], back["w_post"][1], -back["dvt"], back["mu_app"]))
    closeup(top, "topspin_bounce",
            "トップスピン(ω = +200 rad/s)の跳ね(当たる瞬間 v = (%.1f, −%.1f) m/s)。接地点の滑りが小さいので跳ねの途中で止まり、転がりに移って離れる"
            "(滑り %+.2f → %+.2f m/s、跳ねた後の rω' = %.3f m/s と v_x' = %.3f m/s)。" % (
                top["v_in"][0], abs(top["v_in"][2]), top["slip_in"], top["slip_out"], r * top["w_post"][1], top["v_out"][0]))

    # (4) e(v) と (5) 種類の地図
    vv = np.array([x["vz_kmh"] for x in res])
    ee = np.array([x["e"] for x in res])
    xs = np.linspace(vv.min() - 1, vv.max() + 1, 50)
    figs.save_plot("restitution_vs_speed", [("動画から読んだ e", vv, ee), ("当てはめた直線(傾き %.4f)" % slope, xs, icpt + slope * (xs - V_ITTF)),
                                            ("公表値: ITTF の切片 + Inaba らの傾き −0.0058", xs, E_ITTF + INABA_SLOPE * (xs - V_ITTF)),
                                            ("Inaba らの直線そのもの(切片 1.0002)", xs, 1.0002 + INABA_SLOPE * xs)],
                   xlabel="衝突の縦の速さ [km/h]", ylabel="反発係数 e", title="反発係数は速く当たるほど下がる",
                   kinds=["scatter", "line", "line", "line"], ylim=(0.84, 1.06),
                   caption="動画から読んだ e(22 本)と公表値。傾きは Inaba ら 2017 と %.1f %% で一致。Inaba らの直線そのものは ITTF の台の跳ね(約 23 cm)より"
                           "高く跳ねる側にずれている —— 公表値同士の食い違い(研究室の台と規格の差か、測り方の差かは未確認)。" % (100 * abs(slope / INABA_SLOPE - 1)))
    obl = [x for x in res if x["throw"].get("drop") is None]
    g = [x for x in obl if x.get("regime_meas") == "grip"]
    s_ = [x for x in obl if x.get("regime_meas") == "slip"]
    bb = [x for x in obl if "regime_meas" not in x]
    ser = []
    for lab, grp in (("転がりに移った(動画)", g), ("滑ったまま(動画)", s_), ("境目の帯(判定しない)", bb)):
        if grp:
            ser.append((lab, np.array([abs(x["v_in"][2]) for x in grp]), np.array([abs(x["slip_in"]) for x in grp])))
    vz_ax = np.linspace(2.0, 4.5, 20)
    ser.append(("閉形式の境目 |s| = (5/2) μ (1+e) |v_z|", vz_ax, 2.5 * mu_m * (1 + np.array([e_table(v) for v in vz_ax])) * vz_ax))
    figs.save_plot("regime_map", ser, kinds=["scatter"] * (len(ser) - 1) + ["line"], ylim=(0.0, 19.0), xlabel="衝突の縦の速さ |v_z| [m/s]", ylabel="接地点の滑りの速さ |s| [m/s]", title="転がりに移るか、滑ったままか",
                   caption="境目より下の跳ねは接地点が止まって転がりに移り、上の跳ねは滑ったまま離れる(Cross 2002)。境目は動画から読んだ μ = %.3f と e(v) で引いた。" % mu_m)


if __name__ == "__main__":
    sys.exit(main())
