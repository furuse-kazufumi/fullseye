# -*- coding: utf-8 -*-
# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""gallery_drive_mirrors_crowds — 鏡(カーブミラー)・坂道の譲り合い・人の群れの 1 歩を、閉形式と第 2 実装で確かめる

    py -3.11 examples/gallery_drive_mirrors_crowds.py

【平たく言うと】
見通しの悪い交差点ではカーブミラーで左右を確かめ、狭い坂道ではどちらが譲るかを決め、横断歩道の周りでは
人が互いに避けながら歩く。ここではそのための op 4 本を確かめる:
  鏡の折り返し(drivedecide)、鏡に映る物が左右どちらに見えるか(drivepass)、坂道の行き違い(drivepass)、
  social force の 1 歩(drivetraffic)。

【何を期待し、何と比べるか】
  * mirror_reflection_matrix : 対合 S·S = I、回転部の行列式 = −1、鏡面上の点は動かない、鏡からの距離 d の点は −d へ、
                               距離を保つ(等長)。法線は正規化される(長さ 2 の法線でも同じ面)。
  * mirror_image_side        : 像の位置 = 3 次元の鏡映行列(mirror_reflection_matrix)で折り返した点(op をまたいだ第 2 実装)、
                               像の角 = atan2(c × q, c · q) を自前で、左右 = heading との外積の符号、
                               仮想の眼から見た角の速さ = −(像の角の速さ)(恒等式)。法線が眼に向いていなければ拒む。
  * hill_meeting_yield       : 教則 6-2-1(6) の表 —— 原則は下りが譲る、上りの車の 30 m 以内に待避所があれば上りがそこで待つ。
  * social_force_step        : 1 人・斥力なしなら v(t) = v0(1 − e^{−t/τ})、x(t) = v0(t − τ(1 − e^{−t/τ}))に
                               **刻み幅に依らず**一致(dt = 0.1 と 0.5 の両方)。点対称な 2 人 + 壁は 10 歩後も点対称。
                               斥力があると、無いときより 2 人の間が開く。2 人が同じ位置なら拒む。

正直に: 坂道の譲り合いは法の明文が無く教則の記述で、待避所の「近く」= 30 m は op の仮定(引数 near)。
social force の係数(A・B・τ)はここでは閉形式の門のための値で、実測の歩行者に合わせたものではない。
"""
from __future__ import annotations

import math
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import drivedecide as DD  # noqa: E402
import drivepass as DP  # noqa: E402
import drivetraffic as DTF  # noqa: E402

_ROWS = []


def check(op, what, expected, got, ok):
    """1 行 = 何を期待し、何が出て、合ったか。"""
    _ROWS.append((op, bool(ok)))
    print("  %-24s %-48s 期待 %-22s 実測 %-22s %s" % (op, what, expected, got, "ok" if ok else "NG"))


def _apply(S, P):
    P = np.atleast_2d(np.asarray(P, np.float64))
    return (np.column_stack([P, np.ones(len(P))]) @ S.T)[:, :3]


def part_reflection():
    print("== 1. 鏡の折り返し(3 次元)")
    S = DD.mirror_reflection_matrix((0.0, 0.0, 2.0, 4.0))          # 法線の長さ 2 → 正規化して z = 2 の面
    check("mirror_reflection_matrix", "長さ 2 の法線 (0,0,2)、d = 4 → 面 z = 2", "z ↦ 4 − z", "z ↦ %g − z" % S[2, 3],
          np.allclose(S, [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, -1, 4], [0, 0, 0, 1]]))
    n = np.array([1.0, 2.0, 2.0]) / 3.0
    S = DD.mirror_reflection_matrix((*n, 1.5))
    inv = float(np.abs(S @ S - np.eye(4)).max())
    check("mirror_reflection_matrix", "対合 S·S = I", "差 < 1e-15", "%.1e" % inv, inv < 1e-15)
    det = float(np.linalg.det(S[:3, :3]))
    check("mirror_reflection_matrix", "回転部の行列式(向きの反転)", "−1", "%.15f" % det, abs(det + 1.0) < 1e-14)
    on = np.array([1.5, 0.0, 0.0]) * 1.0 / 1.0                      # n·X = 0.5 ≠ 1.5 → 面上の点を作る
    on = on + (1.5 - n @ on) * n
    check("mirror_reflection_matrix", "鏡面上の点は動かない", "差 0", "%.1e" % np.abs(_apply(S, on)[0] - on).max(),
          np.allclose(_apply(S, on)[0], on, atol=1e-14))
    rng = np.random.default_rng(1)
    P = rng.normal(size=(50, 3)) * 3.0
    Q = _apply(S, P)
    dist_p, dist_q = P @ n - 1.5, Q @ n - 1.5
    check("mirror_reflection_matrix", "鏡からの符号つき距離 d → −d(50 点)", "差 < 1e-12",
          "%.1e" % np.abs(dist_q + dist_p).max(), np.abs(dist_q + dist_p).max() < 1e-12)
    dP = np.linalg.norm(P[:, None] - P[None], axis=2)
    dQ = np.linalg.norm(Q[:, None] - Q[None], axis=2)
    check("mirror_reflection_matrix", "等長(点の間の距離を保つ)", "差 < 1e-12", "%.1e" % np.abs(dP - dQ).max(),
          np.abs(dP - dQ).max() < 1e-12)


def _cross(a, b):
    return a[..., 0] * b[..., 1] - a[..., 1] * b[..., 0]


def part_mirror_side():
    print("== 2. カーブミラーに映る物の左右")
    E = np.array([0.0, 0.0])                                         # 運転者の眼、前 = +x
    M = np.array([12.0, 4.0])                                        # 交差点の向こうの角に立つ鏡
    nrm = np.array([-1.0, -0.6]) / math.hypot(1.0, 0.6)              # 鏡の法線(眼の側を向く)
    P = np.array([[8.0, 9.0], [10.0, -3.0], [3.0, 2.0]])            # 左の路地・右・手前の左
    V = np.array([[0.0, -1.5], [1.0, 0.5], [0.8, 0.0]])
    r = DP.mirror_image_side(E, M, nrm, P, heading=(1.0, 0.0), velocities=V)
    S = DD.mirror_reflection_matrix((nrm[0], nrm[1], 0.0, float(nrm @ M)))
    Pi = _apply(S, np.column_stack([P, np.zeros(len(P))]))[:, :2]
    check("mirror_image_side", "像 = 3 次元の鏡映行列で折り返した点(第 2 実装)", "差 < 1e-12",
          "%.1e" % np.abs(r["image_points"] - Pi).max(), np.abs(r["image_points"] - Pi).max() < 1e-12)
    c, q = M - E, Pi - E
    off = np.arctan2(_cross(c[None, :], q), q @ c)
    check("mirror_image_side", "像の角 atan2(c × q, c · q)(+ = 左)", str(np.round(off, 4).tolist()),
          str(np.round(r["image_offset"], 4).tolist()), np.allclose(r["image_offset"], off, atol=1e-12)
          and np.array_equal(r["image_side"], np.sign(off)))
    side = np.sign(_cross(np.array([[1.0, 0.0]]), P - E))
    check("mirror_image_side", "実物の左右 = heading × (P − E) の符号", str(side.astype(int).tolist()),
          str(np.asarray(r["real_side"]).astype(int).tolist()), np.array_equal(r["real_side"], side))
    dq = P - E
    dm = _cross(dq, V) / np.sum(dq * dq, axis=1)
    check("mirror_image_side", "直接見た角の速さ = (P−E) × V / |P−E|²", str(np.round(dm, 4).tolist()),
          str(np.round(r["direct_motion"], 4).tolist()), np.allclose(r["direct_motion"], dm, atol=1e-12))
    ident = float(np.abs(r["virtual_eye_motion"] + r["image_motion"]).max())
    check("mirror_image_side", "仮想の眼から見た角の速さ = −像の角の速さ", "差 < 1e-12", "%.1e" % ident, ident < 1e-12)
    check("mirror_image_side", "reversed = 像と直接の動きの符号が逆", str((np.sign(r["image_motion"]) != np.sign(dm)).tolist()),
          str(np.asarray(r["reversed"]).tolist()), np.array_equal(r["reversed"], np.sign(r["image_motion"]) != np.sign(dm)))
    bad = False
    try:
        DP.mirror_image_side(E, M, -nrm, P, heading=(1.0, 0.0))
    except ValueError:
        bad = True
    check("mirror_image_side", "法線が眼に向いていない鏡は拒む", "ValueError", "ValueError" if bad else "通った", bad)


def part_hill():
    print("== 3. 坂道の狭い所の行き違い(教則 6-2-1(6))")
    table = [
        (("down", None, None), ("ego", "stop"), "自車が下り・待避所なし → 自車が止まって譲る"),
        (("up", None, None), ("other", "stop"), "自車が上り・待避所なし → 下りの相手が譲る"),
        (("up", 20.0, None), ("ego", "refuge"), "自車が上り・20 m 先に待避所 → 自車がそこで待つ"),
        (("up", 50.0, None), ("other", "stop"), "自車が上り・待避所は 50 m 先(30 m 超)→ 相手が譲る"),
        (("down", None, 10.0), ("other", "refuge"), "相手が上り・相手の 10 m 先に待避所 → 相手が待つ"),
        (("down", None, 40.0), ("ego", "stop"), "相手の待避所は 40 m 先 → 下りの自車が譲る"),
    ]
    for (d, er, orr), want, what in table:
        r = DP.hill_meeting_yield(d, ego_refuge_distance=er, other_refuge_distance=orr)
        got = (r["yielder"], r["where"])
        check("hill_meeting_yield", what, "%s・%s" % want, "%s・%s" % got, got == want and "6-2-1" in r["basis"])
    r = DP.hill_meeting_yield("up", ego_refuge_distance=50.0, near=60.0)
    check("hill_meeting_yield", "near = 60 m にすると 50 m 先の待避所で待つ", "ego・refuge", "%s・%s" % (r["yielder"], r["where"]),
          (r["yielder"], r["where"]) == ("ego", "refuge"))


def part_crowd():
    print("== 4. social force の 1 歩")
    v0, tau = 1.34, 0.5
    for dt in (0.1, 0.5):
        pos, vel, goal = np.zeros((1, 2)), np.zeros((1, 2)), np.array([[100.0, 0.0]])
        n = int(round(2.0 / dt))
        for _ in range(n):
            pos, vel = DTF.social_force_step(pos, vel, goal, dt=dt, v0=v0, tau=tau, A=2.0, B=0.3, radius=0.3)
        t = n * dt
        v_ex = v0 * (1 - math.exp(-t / tau))
        x_ex = v0 * (t - tau * (1 - math.exp(-t / tau)))
        check("social_force_step", "1 人・dt = %.1f で t = 2 s の速さ・位置" % dt, "%.6f・%.6f" % (v_ex, x_ex),
              "%.6f・%.6f" % (vel[0, 0], pos[0, 0]), abs(vel[0, 0] - v_ex) < 1e-12 and abs(pos[0, 0] - x_ex) < 1e-12
              and vel[0, 1] == 0.0)

    pos = np.array([[-3.0, 0.2], [3.0, -0.2]])
    vel = np.array([[1.0, 0.0], [-1.0, 0.0]])
    goals = np.array([[10.0, 0.5], [-10.0, -0.5]])
    walls = np.array([[[-10.0, 1.5], [10.0, 1.5]], [[10.0, -1.5], [-10.0, -1.5]]])
    kw = dict(dt=0.1, v0=1.3, tau=0.5, B=0.3, radius=0.3, walls=walls)
    p1, v1 = pos.copy(), vel.copy()
    for _ in range(10):
        p1, v1 = DTF.social_force_step(p1, v1, goals, A=2.0, **kw)
    sym = float(max(np.abs(p1[0] + p1[1]).max(), np.abs(v1[0] + v1[1]).max()))
    check("social_force_step", "点対称な 2 人 + 壁: 10 歩後も点対称", "差 < 1e-12", "%.1e" % sym, sym < 1e-12)
    # 壁なしで向かい合う 2 人: すれ違う瞬間(前後の差が最小のコマ)の横の間隔は、斥力ありのほうが広い
    # (壁があると壁の斥力で内へ寄るので、ここは壁なしで比べる)
    open_kw = dict(kw, walls=None)

    def passing_gap(A):
        p, v = pos.copy(), vel.copy()
        best = (math.inf, 0.0)
        for _ in range(40):
            p, v = DTF.social_force_step(p, v, goals, A=A, **open_kw)
            best = min(best, (abs(p[0, 0] - p[1, 0]), abs(p[0, 1] - p[1, 1])))
        return best[1]
    gap1, gap0 = passing_gap(2.0), passing_gap(0.0)
    check("social_force_step", "壁なし: すれ違う瞬間の横の間隔(A = 2 vs 0)", "A=2 > A=0 + 5 cm",
          "%.3f > %.3f m" % (gap1, gap0), gap1 > gap0 + 0.05)
    bad = False
    try:
        DTF.social_force_step(np.zeros((2, 2)), np.zeros((2, 2)), np.ones((2, 2)), A=2.0, **dict(kw, walls=None))
    except ValueError:
        bad = True
    check("social_force_step", "2 人が同じ位置なら拒む", "ValueError", "ValueError" if bad else "通った", bad)


def run():
    t0 = time.perf_counter()
    part_reflection()
    part_mirror_side()
    part_hill()
    part_crowd()
    return time.perf_counter() - t0


if __name__ == "__main__":
    sec = run()
    ng = [op for op, ok in _ROWS if not ok]
    print("mirrors & crowds: %d op / %d 検査 / NG %d / %.2f s" % (len({op for op, _ in _ROWS}), len(_ROWS), len(ng), sec))
    if ng:
        print("FAILED:", sorted(set(ng)))
        raise SystemExit(1)
    print("PASS")
