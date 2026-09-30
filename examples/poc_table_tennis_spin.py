# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC ㉔: 回転で曲がる卓球の球を撮って、回転を 2 通りで読む —— 曲がり方から / 球の模様から。

同じ速さ・同じ向きで打ち出した球でも、トップスピン(前回転)なら沈んで手前に落ち、バックスピン(下回転)なら浮いて奥まで
伸び、横回転なら横に逸れる(マグヌス効果: 力は ω × v の向き)。この PoC は 4 本の打球(トップ・無回転・バック・横)を
2 台のカメラ(240 fps)で撮り、三角測量した軌跡から**曲がり方で**回転を読み(:func:`ballistics.fit_spin`、9 パラメータの
運動方程式の当てはめ)、同じ打球を近接カメラ(1000 fps)で撮って**球の模様の動きで**回転を読む(:func:`balltrack.spin_from_markers`)。
2 つの測り方は独立(片方は軌跡だけ、片方は模様だけを見る)なので、互いに一致することが第 2 実装の門になる。

門(真値の出どころ):
  1. **恒等式**: 真値の軌跡を fit_spin に入れると回転が 1e-3 rad/s で戻る。
  2. **読めない成分の定理**: マグヌスの力は ω × v なので、進行方向に平行な回転は力を生まない —— その瞬間の加速度は回転なしと
     1e-12 で同じ。飛ぶうちに重力で進行方向が曲がるので 0.25 s では少し効くが、垂直な回転の 1/5 未満(fit_spin はこの成分を
     ``omega_perp`` に分けて返す)。
  3. **着地点**: 画像から読んだ回転で先を読んだ着地点が、4 本とも真値と 2 cm 以内。着地の順はトップ < 無回転 < バック。
  4. **曲がり方から回転**: 跳ねる前の軌跡だけ(画像から)で、回転のある 3 本は垂直成分が真値と 10 % 以内、無回転は 10 rad/s 未満。
  5. **模様から回転**: 近接カメラ 20 コマで、回転のある 3 本が真値と 5 % 以内。
  6. **2 通りの一致**: 曲がり方と模様(どちらも真値を見ない)の差が 10 % 以内。
  7. **長さの効き**: 軌跡が短いと曲がりが見えず、回転は読めない。使うコマ数を増やすと誤差が減る(最長で最短の 1/3 以下)。
  8. **零点**: 無回転の球は、模様からも 10 rad/s 未満。

正直に書くこと: 球の検出は色が既知の合成映像(実写の照明・ぼけ・背景は無い)。空力係数(C_d = 0.4、C_L はスピン比の経験式)は
真値と当てはめで同じ式を使っている —— 曲がり方から回転を読む手は、空力のモデルが正しいことを前提にしている(実測の C_L は
スピン比 0.5 付近に谷がある、という報告がある: Miyazaki ら 2017)。回転は飛行中一定(減衰なし)。近接カメラは球が視野に入る
20 ms だけの都合のよい配置。

Run: py -3.11 examples/poc_table_tennis_spin.py   (図は FULLSEYE_FIGURE_DIR を設定したときだけ書く。FULLSEYE_POC_BUDGET=reduced で
長さの掃引を粗くする。MP4 は extras [video](imageio-ffmpeg)があるときだけ)
"""
from __future__ import annotations

import os
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
import annotate as AN  # noqa: E402

T0 = time.time()
REDUCED = os.environ.get("FULLSEYE_POC_BUDGET", "reduced" if os.environ.get("CI") else "full") == "reduced"
#: ★追跡カメラは予算に関係なく 240 fps。120 fps に落とすと標本が半分になり、回転の誤差が √2 倍(バック 0.9 → 10.9 %)、
#:   コマ間で球が 1.6 cm 動くので跳ねの谷も浅く見えた(2026-09-30)。予算は長さの掃引の刻みだけで削る。
FPS = 240
ROI = 160                              # 追跡カメラの読み出し窓 [px]
POST_BOUNCE = 0.03                     # 跳ねた後に撮る長さ [s](跳ねの谷を見つけるのに足りるだけ)
FPS_SPIN = 1000                        # 近接カメラ
N_SPIN = 20
LAG = 4                                # 模様の 2 段目: 4 コマ離れた組(回転 ≈ 0.6 rad)
TRACK_W, TRACK_H = 1024, 800
V0 = np.array([6.0, 0.0, 1.3])
SPIN = 150.0                           # rad/s(≈ 1430 rpm)
SERVES = [("トップスピン", "top", (0.0, SPIN, 0.0), (1.0, 0.55, 0.05)),
          ("無回転", "none", (0.0, 0.0, 0.0), (1.0, 0.85, 0.10)),
          ("バックスピン", "back", (0.0, -SPIN, 0.0), (0.15, 0.65, 1.0)),
          ("横回転", "side", (0.0, 0.0, SPIN), (0.85, 0.25, 0.85))]
BALL_COLOR = (1.0, 0.55, 0.05)
E_TRUE, MU_TRUE = 0.9, 0.25
MARKERS = [((1, 0, 0), 11.0), ((-1, 0, 0), 11.0), ((0, 1, 0), 11.0), ((0, -1, 0), 11.0), ((0, 0, 1), 11.0), ((0, 0, -1), 11.0)]
MARKERS += [((sx, sy, sz), 11.0) for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]
OK = []


def gate(name, cond, detail=""):
    OK.append(bool(cond))
    print("  [%s] %s %s" % ("PASS" if cond else "FAIL", name, detail))


def _interp(sim, key, t):
    return np.column_stack([np.interp(np.atleast_1d(t), sim["t"], sim[key][:, k]) for k in range(3)])


def _poses(sim, t_frames):
    """姿勢の積分(コマの間は角速度一定とみなす)。"""
    W = _interp(sim, "omega", t_frames)
    R, out = np.eye(3), []
    for k in range(len(t_frames)):
        if k:
            R = BW.rotation_from_omega(W[k - 1], t_frames[k] - t_frames[k - 1]) @ R
        out.append(R.copy())
    return out


def _disc(img, c, r, color):
    h, w = img.shape[:2]
    if not np.all(np.isfinite(c)):
        return
    x0, x1 = int(max(0, c[0] - r - 1)), int(min(w, c[0] + r + 2))
    y0, y1 = int(max(0, c[1] - r - 1)), int(min(h, c[1] + r + 2))
    if x0 >= x1 or y0 >= y1:
        return
    yy, xx = np.mgrid[y0:y1, x0:x1]
    m = (xx - c[0]) ** 2 + (yy - c[1]) ** 2 <= r * r
    img[y0:y1, x0:x1][m] = color


def _spin_from_closeup(world, ball, sim, t_mid, R0):
    """近接カメラ(1000 fps、N_SPIN コマ、ストロボ照明)で模様を検出し、コマ間の回転を Kabsch で当てる。

    返り値 (ω の中央値(世界系), コマ, 使えたコマ組の数)。真値は描画(世界の姿勢)にだけ使い、推定は画像だけから。"""
    t_sp = t_mid + (np.arange(N_SPIN) - N_SPIN // 2) / FPS_SPIN
    pm = _interp(sim, "p", t_mid)[0]
    eye = pm + np.array([0.0, -0.6, 0.15])
    K = DW.camera_intrinsics(20.0, 256, 256)
    pose = DW.camera_pose(eye, pm)
    Rc = np.asarray(pose)[:3, :3]
    P = _interp(sim, "p", t_sp)
    W = _interp(sim, "omega", t_sp)
    R = R0.copy()
    dirs, frames = [], []
    rr, cc = np.mgrid[0:256, 0:256]
    for k in range(N_SPIN):
        if k:
            R = BW.rotation_from_omega(W[k - 1], 1.0 / FPS_SPIN) @ R
        BW.ball_set_pose(world, ball, P[k], R)
        view = DW.world_camera(world, pose, K, 256, 256, ambient=0.7)
        frames.append(view["color"])
        d = BT.ball_detect(view["color"], mode="chroma", color=BALL_COLOR, color_tol=0.2, radius_range=(10, 120))
        if not d:
            dirs.append(None)
            continue
        cb, rb = (d[0]["col"], d[0]["row"]), d[0]["radius"] + 0.5
        gray = view["color"].mean(-1)
        inside = np.hypot(cc - cb[0], rr - cb[1]) < rb * 0.85          # 縁は模様が潰れるので内側だけ
        marks = BT.ball_detect(np.where(inside, gray, 1.0), mode="dark", thresh=0.2, radius_range=(1.5, 12))
        dirs.append(np.asarray([BT.marker_direction((m["col"], m["row"]), cb, rb, K) for m in marks]) if len(marks) >= 2 else None)
    # 1 段目: 隣のコマと対応づける(1 コマの回転 ≈ 0.15 rad なので、向きが 0.5 rad 以内で最も近い組)。
    est1 = [e for e in (_kabsch_pair(dirs[k], dirs[k + 1], 1, None) for k in range(N_SPIN - 1)) if e is not None]
    if not est1:
        return np.full(3, np.nan), frames, 0
    w1 = np.median(np.asarray(est1), axis=0)
    # 2 段目: LAG コマ離れた組で当て直す。回転角が LAG 倍になるので、模様の位置の誤差が効く割合は 1/LAG。
    #   対応づけは 1 段目の ω で前のコマを回して予測し、予測に最も近い模様と組む(0.25 rad 以内)。
    est = [e for e in (_kabsch_pair(dirs[k], dirs[k + LAG], LAG, w1) for k in range(N_SPIN - LAG)) if e is not None]
    w_cam = np.median(np.asarray(est), axis=0) if est else w1
    return Rc.T @ w_cam, frames, len(est)                               # カメラ系 → 世界系


def _kabsch_pair(d0, d1, lag, w_pred):
    """模様の向きの組 (d0, d1)(lag コマ離れている)を対応づけて回転を当てる(カメラ系の ω)。対応が 2 組未満なら None。"""
    if d0 is None or d1 is None:
        return None
    dt = lag / FPS_SPIN
    pred = d0 if w_pred is None else d0 @ BW.rotation_from_omega(w_pred, dt).T
    cosang = pred @ d1.T
    lim = np.cos(0.5 if w_pred is None else 0.25)
    pairs, used_i, used_j = [], set(), set()
    for i, j in sorted(((i, j) for i in range(len(d0)) for j in range(len(d1))), key=lambda ij: -cosang[ij]):
        if i in used_i or j in used_j or cosang[i, j] < lim:
            continue
        pairs.append((i, j))
        used_i.add(i)
        used_j.add(j)
    if len(pairs) < 2:
        return None
    return BT.spin_from_markers(d0[[i for i, _ in pairs]], d1[[j for _, j in pairs]], dt)["omega"]


def _roi_detections(world, ball, P, Rs, cam):
    """1 台のカメラで全コマの球を検出する。★高速カメラの ROI 読み出しと同じく、前 2 コマの検出から等速で予測した位置の
    周り ROI × ROI px だけを描いて(= 読み出して)探す。最初の 2 コマと、ROI の中で見失ったコマは全画面で読み直す
    (その候補には ``"full": True`` を付ける)。座標は全画面の (col, row) で返す。予測に真値は使わない。"""
    W, Hh = cam["width"], cam["height"]
    dets, hist = [], []
    for k in range(len(P)):
        BW.ball_set_pose(world, ball, P[k], Rs[k])
        found = []
        if len(hist) >= 2:
            (c1, r1), (c2, r2) = hist[-2], hist[-1]
            pc, pr = 2 * c2 - c1, 2 * r2 - r1
            x0 = int(np.clip(round(pc) - ROI // 2, 0, W - ROI))
            y0 = int(np.clip(round(pr) - ROI // 2, 0, Hh - ROI))
            Kr = np.array(cam["K"], dtype=np.float64)
            Kr[0, 2] -= x0
            Kr[1, 2] -= y0
            img = DW.world_camera(world, cam["pose"], Kr, ROI, ROI)["color"]
            cand = BT.ball_detect(img, mode="chroma", color=BALL_COLOR, color_tol=0.12, radius_range=(1.5, 30))
            found = [dict(c, col=c["col"] + x0, row=c["row"] + y0) for c in cand]
        if not found:
            img = DW.world_camera(world, cam["pose"], cam["K"], W, Hh)["color"]
            found = [dict(c, full=True) for c in BT.ball_detect(img, mode="chroma", color=BALL_COLOR, color_tol=0.12, radius_range=(1.5, 30))]
        dets.append(found)
        if found:
            hist.append((found[0]["col"], found[0]["row"]))
    return dets


def _drop_partial(tr, ratio=0.8, half=4):
    """欠けた検出を捨てる: 像の半径が前後 ``half`` コマの中央値の ``ratio`` 倍未満のコマ(ネットなどに一部が隠れると、
    色の重心が見えている側へ寄り、半径が小さく出る)。返り値 (軌跡, 捨てた数)。"""
    rad = np.asarray(tr["radius"], float)
    keep = np.ones(len(rad), bool)
    for i in range(len(rad)):
        nb = np.r_[rad[max(0, i - half):i], rad[i + 1:i + 1 + half]]
        if nb.size and rad[i] < ratio * np.median(nb):
            keep[i] = False
    out = {k: (np.asarray(v)[keep] if k != "found" else np.asarray(v).copy()) for k, v in tr.items()}
    out["found"][np.asarray(tr["frame"])[~keep]] = False
    return out, int((~keep).sum())


def _rel(a, b):
    return float(np.linalg.norm(a - b) / max(1e-12, np.linalg.norm(b)))


def main() -> int:
    """PoC の本体(examples の門: 実行は __main__ の守りの下で)。"""
    print("BUDGET: %s(FULLSEYE_POC_BUDGET、CI では reduced が既定。展示の数字は full)" % ("reduced" if REDUCED else "full"))
    bp = B.ball_params()
    ip = B.impact_params(E_TRUE, MU_TRUE)
    tp = BW.table_params()
    H = tp["height"]
    p0 = np.array([-1.30, 0.0, H + 0.25])

    # ─────────────────────────────── 1. 定理 ─────────────────────────────
    print("== 1. 定理: 真値の軌跡で回転が戻る / 進行方向に平行な回転は軌跡を動かさない")
    tt = np.arange(0.0, 0.3, 1.0 / 240)
    f = B.flight_ode(p0, V0, [0, SPIN, 0], bp, 0.31, 1e-4)
    r_id = B.fit_spin(tt, _interp(f, "p", tt), bp)
    id_err = float(np.linalg.norm(r_id["omega"] - np.array([0, SPIN, 0])))
    gate("恒等式: 真値の軌跡から回転が 1e-3 rad/s で戻る", id_err < 1e-3, "差 %.1e rad/s(%d 反復)" % (id_err, r_id["iters"]))
    vhat = V0 / np.linalg.norm(V0)
    perp = np.cross(vhat, [0, 0, 1.0])
    perp /= np.linalg.norm(perp)
    t25 = tt[:60]
    base = _interp(B.flight_ode(p0, V0, [0, 0, 0], bp, 0.26, 1e-4), "p", t25)
    d_ax = np.abs(_interp(B.flight_ode(p0, V0, 100 * vhat, bp, 0.26, 1e-4), "p", t25) - base).max()
    d_pp = np.abs(_interp(B.flight_ode(p0, V0, 100 * perp, bp, 0.26, 1e-4), "p", t25) - base).max()
    a_ax = float(np.abs(B._accel(V0, 100 * vhat, bp) - B._accel(V0, [0, 0, 0], bp)).max())
    print("  打ち出しの瞬間: 平行な回転 100 rad/s の加速度の差 %.1e m/s²。0.25 s の飛行で: 平行 → 軌跡のずれ %.1f mm、垂直 100 rad/s → %.1f cm"
          "(平行な回転も、重力で進行方向が曲がった分だけ効く)" % (a_ax, 1e3 * d_ax, 100 * d_pp))
    gate("読めない成分: 平行な回転の力は 1e-12 で 0、0.25 s でも垂直な回転の 1/5 未満", a_ax < 1e-12 and d_ax < d_pp / 5)

    # ─────────────────────────────── 2. 4 本の打球を撮る ─────────────────────────────
    print("== 2. 同じ打ち出し(v₀ = %s m/s)で回転だけ違う 4 本を、カメラ 2 台(%d fps、%d × %d)で撮る" % (V0.tolist(), FPS, TRACK_W, TRACK_H))
    rig = BW.camera_rig(tp, n=2, width=TRACK_W, height_px=TRACK_H, fov_deg=55.0)
    poses = [c["pose"] for c in rig]
    Ks = [c["K"] for c in rig]
    mesh = BW.ball_mesh(bp["radius"], 3, BALL_COLOR, markers=MARKERS)
    res = {}
    t_r = time.time()
    full_frames = 0
    for label, key, w0, _ in SERVES:
        world = BW.table_world(tp)
        sim = B.flight_simulate(p0, V0, w0, bp, ip, 0.7, 1e-4, table_z=H, table_xy=world["bounds"])
        c0 = sim["contacts"][0]
        t_frames = np.arange(0.0, c0["t"] + POST_BOUNCE, 1.0 / FPS)
        P = _interp(sim, "p", t_frames)
        Rs = _poses(sim, t_frames)
        ball = BW.add_ball(world, mesh, P[0], Rs[0])
        tracks, dropped = [], 0
        for cam in rig:
            dets = _roi_detections(world, ball, P, Rs, cam)
            n_full = sum(1 for d in dets if d and d[0].get("full"))
            full_frames += n_full
            tr, n_drop = _drop_partial(BT.ball_track(dets, max_jump=60.0))
            dropped += n_drop
            tracks.append(tr)
        tri = BT.track_triangulate(tracks, poses, Ks, len(t_frames))
        tri_t = t_frames[tri["frame"]]
        bd = BT.bounce_detect(tri_t, tri["p"][:, 2], min_gap=2)
        # 画像から見つけた跳ね(真値は使わない)。★z の局所最小のうち**最も低いもの** —— 欠けた検出が残ると空中に偽の
        #   「跳ね」ができ、最初の谷を採るとその手前で軌跡を切ってしまう(バックスピンで 36 コマしか使えなかった)。
        #   高さの閾値(台 + r + 1.5 cm)で選ぶ手は、コマ間で球が 1.6 cm 動く 120 fps で本物の谷を落とした
        zb = np.interp(bd["t"], tri_t, tri["p"][:, 2]) if len(bd["t"]) else np.zeros(0)
        t_b = float(bd["t"][int(np.argmin(zb))]) if len(zb) else np.inf
        pre = tri_t < t_b - 1.0 / FPS
        res[key] = {"label": label, "w0": np.asarray(w0, float), "sim": sim, "contact": c0, "t_frames": t_frames, "P": P, "R": Rs,
                    "tri": tri, "tri_t": tri_t, "pre": pre, "bounce_t": t_b, "world": world, "ball": ball, "dropped": dropped}
    print("  ROI(%d × %d px、前 2 コマの等速予測の周り)で読み、全画面で読み直したコマ %d。" % (ROI, ROI, full_frames))
    print("  4 本 × 2 台 を描画・検出・三角測量(%.1f s)。ネットの白帯に上半分が隠れて欠けた検出(半径が前後の 0.8 倍未満)を捨てた数: %s" % (
        time.time() - t_r, ", ".join("%s %d" % (r["label"], r["dropped"]) for r in res.values())))
    tri_err = {k: np.linalg.norm(r["tri"]["p"] - r["P"][r["tri"]["frame"]], axis=1) for k, r in res.items()}
    print("  三角測量の誤差(真値と): %s" % ", ".join("%s 中央値 %.1f mm・最大 %.1f mm" % (res[k]["label"], 1e3 * np.median(e), 1e3 * e.max())
                                                  for k, e in tri_err.items()))

    # ─────────────────────────────── 3. 曲がり方から回転 ─────────────────────────────
    print("== 3. 跳ねる前の軌跡(画像から)に運動方程式を当てて回転を読む(fit_spin、9 パラメータ)")
    land_ok, spin_ok = True, True
    for key, r in res.items():
        tri, pre = r["tri"], r["pre"]
        fs_ = B.fit_spin(r["tri_t"][pre], tri["p"][pre], bp)
        r["fit"] = fs_
        st = B.flight_simulate(fs_["p0"], fs_["v0"], fs_["omega"], bp, ip, 0.7 - fs_["t0"], 1e-4, table_z=H, table_xy=r["world"]["bounds"])
        land = st["contacts"][0]["p"][:2] if st["contacts"] else np.full(2, np.nan)
        r["land_est"] = land
        r["land_err"] = float(np.linalg.norm(land - r["contact"]["p"][:2]))
        land_ok &= r["land_err"] < 0.02
        vh = fs_["v0"] / np.linalg.norm(fs_["v0"])
        w_true_perp = r["w0"] - (r["w0"] @ vh) * vh
        if np.linalg.norm(r["w0"]) > 0:
            e = _rel(fs_["omega_perp"], w_true_perp)
            spin_ok &= e < 0.10
            txt = "垂直成分の誤差 %.1f %%" % (100 * e)
        else:
            e = float(np.linalg.norm(fs_["omega_perp"]))
            spin_ok &= e < 10.0
            txt = "|ω⊥| %.1f rad/s" % e
        r["curve_err"] = e
        spin_ok &= not fs_["at_bound"]
        print("  %s: %d コマ、ω = %s rad/s(真値 %s)、%s、当てはめ rms %.2f mm。先読みした着地点 (%.3f, %.3f) m、真値と %.1f cm" % (
            r["label"], int(pre.sum()), np.round(fs_["omega"], 1), np.round(r["w0"], 1), txt, 1e3 * fs_["rms"], land[0], land[1],
            100 * r["land_err"]))
    order = [float(res[k]["land_est"][0]) for k in ("top", "none", "back")]
    gate("着地点: 4 本とも真値と 2 cm 以内、順はトップ < 無回転 < バック", land_ok and order[0] < order[1] < order[2],
         "(x = %s m)" % np.round(order, 3).tolist())
    gate("曲がり方から回転: 回転のある 3 本は 10 % 以内、無回転は 10 rad/s 未満", spin_ok)

    # ─────────────────────────────── 4. 模様から回転 ─────────────────────────────
    print("== 4. 同じ打球を近接カメラ(%d fps、%d コマ)で撮り、模様の動きから回転を読む(spin_from_markers)" % (FPS_SPIN, N_SPIN))
    mk_ok, agree_ok, zero_ok = True, True, True
    closeups = {}
    for key, r in res.items():
        t_mid = 0.5 * r["contact"]["t"]
        k0 = int(np.searchsorted(r["t_frames"], t_mid - (N_SPIN // 2) / FPS_SPIN)) - 1
        t_start = t_mid - (N_SPIN // 2) / FPS_SPIN
        R0 = BW.rotation_from_omega(r["w0"], t_start - r["t_frames"][k0]) @ r["R"][k0]
        w_mk, fr, n_pairs = _spin_from_closeup(r["world"], r["ball"], r["sim"], t_mid, R0)
        closeups[key] = fr
        r["marker"] = w_mk
        if np.linalg.norm(r["w0"]) > 0:
            e_mk = _rel(w_mk, r["w0"])
            vh = r["fit"]["v0"] / np.linalg.norm(r["fit"]["v0"])
            mk_perp = w_mk - (w_mk @ vh) * vh
            e_ag = _rel(r["fit"]["omega_perp"], mk_perp)
            mk_ok &= e_mk < 0.05
            agree_ok &= e_ag < 0.10
            r["agree"] = e_ag
            print("  %s: 模様 ω = %s rad/s(%d 組)、真値と %.1f %%。曲がり方の ω⊥ %s と %.1f %%" % (
                r["label"], np.round(w_mk, 1), n_pairs, 100 * e_mk, np.round(r["fit"]["omega_perp"], 1), 100 * e_ag))
        else:
            zero_ok &= bool(np.linalg.norm(w_mk) < 10.0)
            r["agree"] = float("nan")
            print("  %s: 模様 ω = %s rad/s(%d 組)、|ω| %.2f rad/s" % (r["label"], np.round(w_mk, 1), n_pairs, np.linalg.norm(w_mk)))
    gate("模様から回転: 回転のある 3 本は真値と 5 % 以内", mk_ok)
    gate("2 通りの一致: 曲がり方と模様(どちらも真値を見ない)の差 10 % 以内", agree_ok)

    # ─────────────────────────────── 5. 長さの効き ─────────────────────────────
    print("== 5. 使う軌跡の長さを変える(トップスピン、跳ねる前の先頭 n コマ)")
    r = res["top"]
    idx = np.flatnonzero(r["pre"])
    grid = (10, 20, 45) if REDUCED else (10, 15, 20, 30, 45, 60)
    lengths = sorted({n for n in grid if n < len(idx)} | {len(idx)})
    len_err, bound = [], []
    for n in lengths:
        sel = idx[:n]
        fs_ = B.fit_spin(r["tri_t"][sel], r["tri"]["p"][sel], bp)
        len_err.append(_rel(fs_["omega_perp"], r["w0"]))
        bound.append(fs_["at_bound"])
    print("  コマ数 → 誤差: %s(* = 回転の上限 1000 rad/s に張り付いた = 大きさが読めていない)" % ", ".join(
        "%d(%.0f ms)→ %.0f %%%s" % (n, 1e3 * n / FPS, 100 * e, "*" if b else "") for n, e, b in zip(lengths, len_err, bound)))
    gate("長さの効き: 最長の誤差は最短の 1/3 以下", len_err[-1] <= len_err[0] / 3, "(%.1f %% → %.1f %%)" % (100 * len_err[0], 100 * len_err[-1]))
    gate("零点: 無回転の球は模様からも 10 rad/s 未満", zero_ok)

    # ─────────────────────────────── 6. 図と動画 ─────────────────────────────
    if figs.enabled():
        print("== 6. 図と動画")
        t_f = time.time()
        _figures(res, closeups, tp, bp, lengths, len_err)
        print("  図と動画(%.1f s)" % (time.time() - t_f))
        if figs.errors():
            print("図の書き出しで失敗:", "; ".join(figs.errors()))
            OK.append(False)
    print("所要 %.1f s" % (time.time() - T0))
    print("SUMMARY: %d / %d gates PASS" % (sum(OK), len(OK)))
    print("PASS" if all(OK) else "FAIL")
    return 0 if all(OK) else 1


def _figures(res, closeups, tp, bp, lengths, len_err):
    """動画 3 本(横から 3 本 / 近接の模様 / 上から横回転)+ 表 + グラフ。"""
    H = tp["height"]
    color = {k: c for _, k, _, c in SERVES}
    # (1) 横から見た 3 本(同じ世界に 3 つの球を置く)。軌跡の跡を残す
    world = BW.table_world(tp)
    balls = {}
    for _, key, _, col in SERVES:
        if key != "side":
            m = BW.ball_mesh(bp["radius"] * 1.6, 3, col, markers=MARKERS)       # 見やすさのため 1.6 倍(描画だけ)
            balls[key] = BW.add_ball(world, m, res[key]["P"][0], np.eye(3))
    W_, H_ = 960, 540
    pose = DW.camera_pose(np.array([0.05, -2.2, H + 0.30]), np.array([0.05, 0.0, H + 0.14]))
    K = DW.camera_intrinsics(40.0, W_, H_)
    trails = {k: [] for k in balls}
    frames = []
    for t in np.arange(0.0, 0.62, 1.0 / 240):
        for key, i in balls.items():
            p = _interp(res[key]["sim"], "p", t)[0]
            BW.ball_set_pose(world, i, p, np.eye(3))
            trails[key].append(BT.reproject(p[None], pose, K)[0])
        img = np.array(DW.world_camera(world, pose, K, W_, H_)["color"], dtype=np.float64)
        for key in balls:
            for q in trails[key][:-1:2]:
                _disc(img, q, 1.6, color[key])
        img = np.asarray(AN.text_box(img, "t = %3.0f ms   1/8 スロー(240 fps を 30 fps で再生)" % (1e3 * t), (10, 10), font_size=16), dtype=np.float64)
        y = 46
        for label, key, _, _ in SERVES:
            if key in balls:
                img = np.asarray(AN.text_box(img, "● %s  ω = %.0f rad/s" % (label, np.linalg.norm(res[key]["w0"])), (10, y), font_size=14,
                                             text_color=color[key]), dtype=np.float64)
                y += 34
        frames.append(np.clip(img, 0, 1))
    figs.save_video("side_three_serves", frames, fps=30.0, gif_every=2, gif_width=640,
                    caption="同じ速さ・同じ向き(v₀ = (6.0, 0, 1.3) m/s)で打ち出した 3 本を横から: トップスピン(橙)は沈んで x = %.2f m、無回転(黄)は %.2f m、"
                            "バックスピン(青)は浮いて %.2f m に落ちる(台の中心から)。球は見やすさのため 1.6 倍で描いた。MP4 = 240 fps の全コマ(1/8 スロー)。" % (
                                res["top"]["contact"]["p"][0], res["none"]["contact"]["p"][0], res["back"]["contact"]["p"][0]))
    # (2) 近接カメラ(トップスピン)
    cl = [np.kron(np.asarray(f, dtype=np.float64), np.ones((2, 2, 1))) for f in closeups["top"]]
    cl = [np.asarray(AN.text_box(f, "近接 1000 fps  t₀ + %2d ms  模様 14 個" % k, (8, 8), font_size=14), dtype=np.float64) for k, f in enumerate(cl)]
    figs.save_video("spin_closeup", cl * 3, fps=10.0, gif_every=1, gif_width=None,
                    caption="近接カメラ(1000 fps、20 コマ = 20 ms)のトップスピン。黒い模様(14 個、見えるのは 4〜6 個)を前のコマと向きで対応づけ、"
                            "Kabsch で回転を当てる: ω = %s rad/s(真値 (0, 150, 0))。1/100 スロー、3 回繰り返し。" % np.round(res["top"]["marker"], 1).tolist())
    # (3) 上から見た横回転と無回転
    world2 = BW.table_world(tp)
    b_side = BW.add_ball(world2, BW.ball_mesh(bp["radius"] * 1.6, 3, color["side"], markers=MARKERS), res["side"]["P"][0], np.eye(3))
    b_none = BW.add_ball(world2, BW.ball_mesh(bp["radius"] * 1.6, 3, color["none"], markers=MARKERS), res["none"]["P"][0], np.eye(3))
    pose2 = DW.camera_pose(np.array([0.0, -0.001, H + 3.2]), np.array([0.0, 0.0, H]), up=(1.0, 0.0, 0.0))
    K2 = DW.camera_intrinsics(50.0, 640, 360)
    fr2, tr_s, tr_n = [], [], []
    for t in np.arange(0.0, 0.5, 1.0 / 240):
        ps = _interp(res["side"]["sim"], "p", t)[0]
        pn = _interp(res["none"]["sim"], "p", t)[0]
        BW.ball_set_pose(world2, b_side, ps, np.eye(3))
        BW.ball_set_pose(world2, b_none, pn, np.eye(3))
        tr_s.append(BT.reproject(ps[None], pose2, K2)[0])
        tr_n.append(BT.reproject(pn[None], pose2, K2)[0])
        img = np.array(DW.world_camera(world2, pose2, K2, 640, 360)["color"], dtype=np.float64)
        for q in tr_s[:-1:2]:
            _disc(img, q, 1.4, color["side"])
        for q in tr_n[:-1:2]:
            _disc(img, q, 1.4, color["none"])
        img = np.asarray(AN.text_box(img, "上から  t = %3.0f ms  横回転(紫)は ω × v の向きへ逸れる" % (1e3 * t), (8, 8), font_size=14), dtype=np.float64)
        fr2.append(np.clip(img, 0, 1))
    figs.save_video("top_view_sidespin", fr2, fps=30.0, gif_every=2, gif_width=None,
                    caption="上から: 横回転(紫、ω = (0, 0, 150) rad/s)は無回転(黄)と同じ打ち出しから %.1f cm 横に逸れて落ちる。曲がり方から読んだ回転 %s rad/s。" % (
                        100 * (res["side"]["contact"]["p"][1] - res["none"]["contact"]["p"][1]), np.round(res["side"]["fit"]["omega"], 1).tolist()))
    # (4) 2 通りの比較と長さの効き
    rows = []
    for label, key, _, _ in SERVES:
        r = res[key]
        rows.append([label, "%s" % np.round(r["w0"], 0).tolist(), "%s" % np.round(r["fit"]["omega_perp"], 1).tolist(),
                     "%s" % np.round(r["marker"], 1).tolist(), "%.1f cm" % (100 * r["land_err"])])
    figs.save_table("two_readings", ["打球", "真値 ω [rad/s]", "曲がり方から(ω⊥)", "模様から", "先読みした着地点の誤差"], rows,
                    title="回転を 2 通りで読む(どちらも真値を見ない)",
                    caption="曲がり方(軌跡に運動方程式を当てる)と模様(近接カメラの Kabsch)は独立。進行方向に平行な成分は曲がり方からは読めない(定理)ので、垂直成分で比べる。")
    figs.save_plot("error_vs_length", [("トップスピン、fit_spin の誤差", 1e3 * np.asarray(lengths) / FPS, 100 * np.asarray(len_err))],
                   xlabel="使った軌跡の長さ [ms]", ylabel="回転の誤差 [%]", title="曲がりが見えるまで回転は読めない",
                   caption="跳ねる前の先頭 n コマだけで回転を読む。短いと曲がり(マグヌスの分)が検出の誤差に埋もれて読めない。")


if __name__ == "__main__":
    sys.exit(main())
