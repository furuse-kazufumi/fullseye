# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC ㉗(自動運転 第 7 回): 終わらない地図 —— 区画を車の周りに作り足し、離れた区画は捨てて、50 km を途切れずに走る。

著者の発案: 「マップが前後左右方向にエンドレスに作られていき、一定以上離れたマップは自動に消えていく形にすれば、もっと
長距離の連続走行のテストもできるのではないか」。世界を一辺 200 m の区画に分け、車のいる区画の周り 5 × 5 だけを持つ。
区画の中身は区画の番号と世界の種だけで決まる(:mod:`driveinf`)ので、捨てた区画に戻ってきても同じものが作り直される。

門(真値の出どころ):
  1. **継ぎ目**: 区画の境目で、両側の区画が出す地面の高さの差 < 1e-12 m、道が辺を横切る位置は 1 ビットも違わない(辺の番号の
     ハッシュを両側が読む)。乱数の区画の組 300 で。
  2. **作り直し**: 50 km 走る間に捨てて作り直した区画は、最初に作ったときとメッシュの指紋(SHA-256)が一致。
  3. **作る順に依らない**: 5 × 5 の区画を乱数の順に作っても、番号順に作っても、指紋が全部同じ。
  4. **記憶の上限**: 何 km 走っても、持っている区画は 25(5 × 5、1 km 四方)を越えない(頂点のバイト数も上限つき)。
  5. **長距離の精度**: 1,000 km 先の区画から走り出し、位置を (区画, 区画の中の座標) で持つと、走り終えた位置の誤差が 1 µm 未満
     (真値 = 同じ歩みを有理数で足し直した終点)。全体の座標を float32(GPU の頂点)で持つと、同じ走りで誤差が 10 cm を越える。
  6. **道を外れない**: 50 km の間、車の中心は常に道の中心線から道幅の半分以内(継ぎ目をまたぐ所も)。

正直に書くこと: 道は区画の中の分岐点と辺を結ぶ直線(角は折れ線で、曲がりの物理は第 8 回の横の運動)。建物・交通・標識は無い。
起伏は Perlin 雑音だけ(地形らしさの門は第 4 回の fBm)。区画の中身は決定的だが、区画どうしの「景色のつながり」は道と高さだけ。

Run: py -3.11 examples/poc_driving_endless_map.py   (図は FULLSEYE_FIGURE_DIR を設定したときだけ書く。FULLSEYE_POC_BUDGET=reduced で走る距離を減らす)
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs  # noqa: E402
import driveinf as DI  # noqa: E402
import balltrack as BT  # noqa: E402
import driveworld as DW  # noqa: E402
import annotate as AN  # noqa: E402

T0 = time.time()
REDUCED = os.environ.get("FULLSEYE_POC_BUDGET", "reduced" if os.environ.get("CI") else "full") == "reduced"
KM = 10.0 if REDUCED else 50.0
STEP = 1.0                              # 1 回に進む距離 [m](20 m/s × 50 ms)
RADIUS = 2                              # 車の区画の周り (2·RADIUS + 1)² = 25 区画(1 km 四方)を持つ —— 3 × 3 だと 200 m 先で世界が切れる
OK = []


def gate(name, cond, detail=""):
    OK.append(bool(cond))
    print("  [%s] %s %s" % ("PASS" if cond else "FAIL", name, detail))


OPP = {"E": "W", "W": "E", "N": "S", "S": "N"}
MOVE = {"E": (1, 0), "W": (-1, 0), "N": (0, 1), "S": (0, -1)}


START_I = 5000                          # 出発する区画(東へ 1,000 km 先)—— 終わらない地図なので、どこからでも走り出せる


def plan_route(tp, n_legs, seed=7, east=0.6):
    """道の網をたどる経路: 区画に入った辺から分岐点へ、分岐点から別の辺へ(種つきの乱数で選ぶ。東へ抜ける辺があれば確率
    ``east`` でそれを選ぶ —— 遠くまで走るため。行き止まりなら引き返す)。返り値 = 区ごとの (区画, 始点, 終点) の列(区画の中の座標)。"""
    rng = np.random.default_rng(seed)
    i, j = START_I, 0
    while not DI.tile_roads(i, j, tp)["ends"]:
        i += 1
    rd = DI.tile_roads(i, j, tp)
    legs = []
    enter = None
    start = rd["hub"].copy()
    for _ in range(n_legs):
        rd = DI.tile_roads(i, j, tp)
        if enter is not None:
            p_in = dict(rd["ends"])[enter]
            legs.append(((i, j), np.asarray(p_in, float), rd["hub"].copy()))
        else:
            legs.append(((i, j), start, rd["hub"].copy()))
        exits = [s for s, _ in rd["ends"] if s != enter] or [enter]
        side = "E" if ("E" in exits and rng.random() < east) else exits[int(rng.integers(len(exits)))]
        p_out = np.asarray(dict(rd["ends"])[side], float)
        legs.append(((i, j), rd["hub"].copy(), p_out))
        di, dj = MOVE[side]
        i, j, enter = i + di, j + dj, OPP[side]
    return legs


def main() -> int:
    """PoC の本体(examples の門: 実行は __main__ の守りの下で)。"""
    print("BUDGET: %s(FULLSEYE_POC_BUDGET、CI では reduced が既定。展示の数字は full)" % ("reduced" if REDUCED else "full"))
    tp = DI.tile_params()
    T = tp["tile"]

    # ─────────────────────────────── 1. 継ぎ目 ─────────────────────────────
    print("== 1. 継ぎ目: 両側の区画が出す高さと道の横切り位置")
    rng = np.random.default_rng(27)
    ys = np.linspace(0.0, T, 101)
    worst, road_mismatch, n_cross = 0.0, 0, 0
    for _ in range(300):
        i, j = (int(v) for v in rng.integers(-10 ** 6, 10 ** 6, 2))
        a = DI.tile_height(i, j, np.full_like(ys, T), ys, tp)
        b = DI.tile_height(i + 1, j, np.zeros_like(ys), ys, tp)
        c = DI.tile_height(i, j, ys, np.full_like(ys, T), tp)
        d = DI.tile_height(i, j + 1, ys, np.zeros_like(ys), tp)
        worst = max(worst, float(np.abs(a - b).max()), float(np.abs(c - d).max()))
        for s1, s2, di, dj in (("E", "W", 1, 0), ("N", "S", 0, 1)):
            e1 = DI.tile_edge_crossing(i, j, s1, tp)
            e2 = DI.tile_edge_crossing(i + di, j + dj, s2, tp)
            road_mismatch += (e1 is None) != (e2 is None) or (e1 is not None and e1 != e2)
            n_cross += e1 is not None
    print("  区画の組 300(番号は ±10⁶ = ±200,000 km まで): 高さの差 最大 %.1e m、道の横切り %d 本のうち不一致 %d" % (worst, n_cross, road_mismatch))
    gate("継ぎ目: 高さ < 1e-12 m、道の横切り位置はビット一致", worst < 1e-12 and road_mismatch == 0)

    # ─────────────────────────────── 3. 作る順 ─────────────────────────────
    print("== 2. 作る順に依らない: 5 × 5 の区画を番号順と乱数の順で作る")
    keys = [(a, b) for a in range(-2, 3) for b in range(-2, 3)]
    d_sorted = {k: DI.tile_digest(DI.tile_mesh(k[0], k[1], tp)) for k in keys}
    perm = [keys[k] for k in rng.permutation(len(keys))]
    d_perm = {k: DI.tile_digest(DI.tile_mesh(k[0], k[1], tp)) for k in perm}
    gate("作る順に依らない: 25 区画の指紋が全部同じ", d_sorted == d_perm)

    # ─────────────────────────────── 走る ─────────────────────────────
    print("== 3. %.0f km 走る(区画の周り 5 × 5 を持ち、外れた区画は捨てる)" % KM)
    legs = plan_route(tp, int(KM * 1000 / 150) + 50)
    cache, first_digest = {}, {}
    n_made, n_regen, regen_bad, max_held, max_bytes = 0, 0, 0, 0, 0
    s_total = 0.0
    i_loc = j_loc = None
    pos = None                                    # (i, j, x, y) —— 区画の中の座標
    g32 = None                                    # 全体の座標(float32)
    worst_off = 0.0
    track = []
    r = {"n": 0}
    t_d = time.time()
    k_leg = 0
    while s_total < KM * 1000 and k_leg < len(legs):
        (ti, tj), a, b = legs[k_leg]
        seg = b - a
        L = float(np.linalg.norm(seg))
        if L < 1e-9:
            k_leg += 1
            continue
        u = seg / L
        if pos is None:
            pos = (ti, tj, float(a[0]), float(a[1]))
            g32 = np.array([ti * T + a[0], tj * T + a[1]], np.float32)
        # この区の上を STEP ずつ進む(区の終わりの端数は短い 1 歩)
        s = 0.0
        while s < L - 1e-12 and s_total < KM * 1000:
            s_next = min(s + STEP, L)
            step = s_next - s
            pi_, pj_, px, py = pos
            pos = DI.pose_normalize(pi_, pj_, px + u[0] * step, py + u[1] * step, T)
            g32 = (g32 + np.array(u * step, np.float32)).astype(np.float32)
            s_total += step
            s = s_next
            if (pos[0], pos[1]) != (i_loc, j_loc):
                i_loc, j_loc = pos[0], pos[1]
                r = DI.tile_stream(cache, i_loc, j_loc, tp, radius=RADIUS)
                for kk in r["loaded"]:
                    dg = DI.tile_digest(cache[kk])
                    if kk in first_digest:
                        n_regen += 1
                        regen_bad += dg != first_digest[kk]
                    else:
                        first_digest[kk] = dg
                        n_made += 1
                max_held = max(max_held, r["n"])
                max_bytes = max(max_bytes, sum(m["V"].nbytes + m["F"].nbytes for m in cache.values()))
            off = float(DI.tile_road_distance(pos[0], pos[1], np.array([pos[2]]), np.array([pos[3]]), tp)[0])
            worst_off = max(worst_off, off)
            if len(track) == 0 or s_total - track[-1][0] >= 25.0:
                track.append((s_total, pos, g32.copy(), sorted(cache)))
        k_leg += 1
    print("  走った距離 %.2f km、作った区画 %d、捨ててから作り直した区画 %d、持っていた区画の最大 %d、頂点と面のバイト数の最大 %.2f MB(%.1f s)" % (
        s_total / 1000, n_made, n_regen, max_held, max_bytes / 1e6, time.time() - t_d))
    gate("作り直し: 捨ててから作り直した区画の指紋が最初と一致", n_regen > 0 and regen_bad == 0, "(%d 区画)" % n_regen)
    gate("記憶の上限: 持っている区画は 25 以下", max_held <= (2 * RADIUS + 1) ** 2)
    gate("道を外れない: 車の中心は道の中心線から道幅の半分以内", worst_off <= 0.5 * tp["road_width"], "(最大 %.2e m)" % worst_off)

    # ─────────────────────────────── 5. 精度 ─────────────────────────────
    print("== 4. 長距離の精度: 位置の持ち方の比較(真値 = 同じ歩みを有理数で足し直した終点)")
    # 真値: 同じ経路の同じ歩み(u·step)を有理数(Fraction、丸め無し)で足し直した終点。比べるのは足し算の丸めの溜まり方だけ
    from fractions import Fraction
    fi, fj, fx, fy = pos
    G_tile = np.array([fi * T + fx, fj * T + fy], np.float64)
    exact = _replay_exact(legs, tp, s_total)
    err_tile = float(np.hypot(float(exact[0] - (fi * Fraction(T) + Fraction(fx))), float(exact[1] - (fj * Fraction(T) + Fraction(fy)))))
    err_g32 = float(np.hypot(float(exact[0] - Fraction(float(g32[0]))), float(exact[1] - Fraction(float(g32[1])))))
    print("  %.1f km 後: 区画の中の座標(float64)の誤差 %.1e m、全体の座標(float32)の誤差 %.2f m、float32 の刻み %.1f mm(%.0f km 先)" % (
        s_total / 1000, err_tile, err_g32, 1e3 * float(np.spacing(np.float32(max(abs(G_tile)) or 1.0))), max(abs(G_tile)) / 1000))
    gate("長距離の精度: 区画の中の座標は 1 µm 未満、float32 の全体座標は 10 cm を越えてずれる", err_tile < 1e-6 and err_g32 > 0.1)

    if figs.enabled():
        print("== 5. 図と動画")
        t_f = time.time()
        _figures(tp, track, legs, first_digest)
        print("  図と動画(%.1f s)" % (time.time() - t_f))
        if figs.errors():
            print("図の書き出しで失敗:", "; ".join(figs.errors()))
            OK.append(False)
    print("所要 %.1f s" % (time.time() - T0))
    print("SUMMARY: %d / %d gates PASS" % (sum(OK), len(OK)))
    print("PASS" if all(OK) else "FAIL")
    return 0 if all(OK) else 1


def _replay_exact(legs, tp, s_total):
    """同じ経路・同じ歩みを Fraction(有理数、丸め無し)で足し直した終点の全体の座標。"""
    from fractions import Fraction
    T = Fraction(tp["tile"])
    walked = 0.0
    X = Y = None
    for (ti, tj), a, b in legs:
        seg = b - a
        L = float(np.linalg.norm(seg))
        if L < 1e-9:
            continue
        u = seg / L
        if X is None:
            X, Y = ti * T + Fraction(float(a[0])), tj * T + Fraction(float(a[1]))
        s = 0.0
        while s < L - 1e-12 and walked < s_total:
            s_next = min(s + STEP, L)
            step = s_next - s
            X += Fraction(float(u[0] * step))
            Y += Fraction(float(u[1] * step))
            walked += step
            s = s_next
        if walked >= s_total:
            break
    return X, Y


def _heat(h, lo=-6.0, hi=6.0, levels=8):
    """高さの塗り分け(等高の 8 段 —— 地図として読め、GIF の減色で粒にならない)。"""
    t = np.clip((h - lo) / (hi - lo), 0, 1)
    t = (np.minimum(np.floor(t * levels), levels - 1) / (levels - 1))[..., None]
    return (1 - t) * np.array([0.20, 0.40, 0.18]) + t * np.array([0.62, 0.66, 0.40])


def _tile_image(i, j, tp, px):
    """区画 (i, j) を真上から px × px の絵に(起伏の濃淡 + 道)。"""
    T = tp["tile"]
    g = (np.arange(px) + 0.5) * T / px
    X, Y = np.meshgrid(g, g[::-1])
    img = _heat(DI.tile_height(i, j, X, Y, tp))
    d = DI.tile_road_distance(i, j, X, Y, tp)
    img[d <= 0.5 * tp["road_width"]] = (0.22, 0.22, 0.24)
    img[:, 0] = img[-1, :] = (0.9, 0.9, 0.9)                       # 区画の境目(左と下)
    return img


def _box(L=4.4, W=1.8, H=1.5):
    """車の代わりの箱(原点 = 底面の中心、+x が前)。"""
    V = np.array([[x, y, z] for z in (0.0, H) for y in (-W / 2, W / 2) for x in (-L / 2, L / 2)])
    F = np.array([[0, 1, 3], [0, 3, 2], [4, 6, 7], [4, 7, 5], [0, 4, 5], [0, 5, 1], [2, 3, 7], [2, 7, 6], [0, 2, 6], [0, 6, 4],
                  [1, 5, 7], [1, 7, 3]])
    return V, F


def _world_from_cache(cache, ci, cj, tp):
    """持っている区画を、車のいる区画の原点に合わせて 1 つの世界に(浮動原点: 区画の番号の差 × T だけずらす)。"""
    T = tp["tile"]
    w = DW._empty_world()
    for (ti, tj), m in cache.items():
        off = np.array([(ti - ci) * T, (tj - cj) * T, 0.0])
        for lab in (0, 1):
            sel = m["label"] == lab
            if not sel.any():
                continue
            F = m["F"][sel]
            used = np.unique(F)
            remap = np.full(len(m["V"]), -1)
            remap[used] = np.arange(len(used))
            DW.world_add(w, m["V"][used] + off, remap[F], lab, m["color"][sel], name="tile")
    return w


def _figures(tp, track, legs, first_digest):
    T = tp["tile"]
    # (1) 真上から: 車の周り 5 × 5 の区画が車について作られ、離れた区画は消える(最初の 5 km、25 m ごと)
    PX = 72
    NT = 2 * RADIUS + 1
    img_cache = {}
    frames = []
    made = set()
    for s_, (ti, tj, x, y), g32, held in [t for t in track if t[0] <= 5000.0]:
        canvas = np.full((NT * PX, NT * PX, 3), 0.08)
        for (ki, kj) in held:
            if (ki, kj) not in img_cache:
                img_cache[(ki, kj)] = _tile_image(ki, kj, tp, PX)
            a, b = ki - ti + RADIUS, RADIUS - (kj - tj)
            if 0 <= a < NT and 0 <= b < NT:
                canvas[b * PX:(b + 1) * PX, a * PX:(a + 1) * PX] = img_cache[(ki, kj)]
            made.add((ki, kj))
        cx, cy = RADIUS * PX + x / T * PX, RADIUS * PX + (T - y) / T * PX
        yy, xx = np.mgrid[0:NT * PX, 0:NT * PX]
        canvas[(xx - cx) ** 2 + (yy - cy) ** 2 <= 16] = (1.0, 0.3, 0.2)
        big = np.kron(canvas, np.ones((2, 2, 1)))
        f = np.asarray(AN.text_box(big, "%.2f km  区画 (%d, %d)  持っている区画 %d  作った区画 %d" % (
            s_ / 1000, ti, tj, len(held), len(made)), (6, 6), font_size=13), dtype=np.float64)
        frames.append(np.clip(f, 0, 1))
    figs.save_video("minimap_stream", frames, fps=12.0, gif_every=2, gif_width=360,
                    caption="真上から: 赤 = 車、周り 5 × 5 の区画(一辺 200 m、1 km 四方)だけを持ち、車が区画をまたぐと進む側に 5 区画を作り、反対側の 5 区画を捨てる。"
                            "色の濃淡は起伏、灰の帯は道(区画の境目で必ずつながる)。1,000 km 先の区画から東寄りに走る最初の 5 km。")
    # (2) 車載カメラ: 浮動原点で持っている区画を描く(25 m ごと、最初の 3 km)
    frames2 = []
    cur = None
    world = None
    for k in range(1, len(track)):
        s_, (ti, tj, x, y), g32, held = track[k]
        if s_ > 3000.0:
            break
        _, (pi_, pj_, px_, py_), _, _ = track[k - 1]
        d = np.array([(ti - pi_) * T + x - px_, (tj - pj_) * T + y - py_])
        if np.linalg.norm(d) < 1e-6:
            continue
        u = d / np.linalg.norm(d)
        if cur != (ti, tj, tuple(held)):
            cache = {kk: DI.tile_mesh(kk[0], kk[1], tp, step=5.0) for kk in held}     # カメラ用は 5 m の格子(近くの三角形を小さく)
            world = _world_from_cache(cache, ti, tj, tp)
            car = DW.world_add(world, *_box(), 5, (0.85, 0.15, 0.12), name="car")
            cur = (ti, tj, tuple(held))
        z0 = float(DI.tile_height(ti, tj, np.array([x]), np.array([y]), tp)[0])
        yaw = float(np.arctan2(u[1], u[0]))
        V0, _ = _box()
        R = np.array([[np.cos(yaw), -np.sin(yaw), 0], [np.sin(yaw), np.cos(yaw), 0], [0, 0, 1]])
        o = world["objects"][car]
        world["V"][o["verts"][0]:o["verts"][1]] = V0 @ R.T + np.array([x, y, z0])
        # 追従カメラ: 車の 7 m 後ろ・3 m 上から、車の 25 m 先を見る(★頂点がカメラの後ろにある三角形は描かれないので、
        #   カメラを車の真上に置くと足元の地面に穴が開く)
        eye = np.array([x - 7 * u[0], y - 7 * u[1], z0 + 3.0])
        tgt = np.array([x + 25 * u[0], y + 25 * u[1], z0 + 0.5])
        pose = DW.camera_pose(eye, tgt)
        K = DW.camera_intrinsics(70.0, 480, 270)
        v = DW.world_camera(world, pose, K, 480, 270)
        img = np.array(v["color"], dtype=np.float64)
        # ★描画器は頂点が 1 つでもカメラの後ろにある三角形を捨てるので、足元に穴(空の色)が開く。地平線より下なのに何も
        #   当たらなかった画素だけを地面の色で埋める(第 6 回の env_render と同じ扱い。見た目だけで、門には使わない)
        M = BT._projection_matrix(pose, K)
        A = M[:, :3]
        rr, cc = np.mgrid[0:270, 0:480]
        dirs = np.linalg.solve(A, np.stack([cc.ravel() + 0.5, rr.ravel() + 0.5, np.ones(rr.size)])).T
        hole = (np.asarray(v["label"]).ravel() < 0) & (dirs[:, 2] < 0)
        img.reshape(-1, 3)[hole] = (0.20, 0.36, 0.16)
        f = np.asarray(AN.text_box(img, "%.2f km  区画 (%d, %d)  区画の中 (%.1f, %.1f) m" % (
            s_ / 1000, ti, tj, x, y), (6, 6), font_size=13), dtype=np.float64)
        frames2.append(np.clip(f, 0, 1))
    figs.save_video("dashcam", frames2, fps=12.0, gif_every=2, gif_width=None,
                    caption="追従カメラ(赤 = 車、25 m ごと、最初の 3 km)。持っている 25 区画だけを、車のいる区画の原点に合わせて描く(浮動原点)—— "
                            "1,000 km 先でも頂点の座標は ±600 m に収まる。区画の継ぎ目で道と地面は途切れない。描画器はカメラの後ろに頂点がある"
                            "三角形を捨てるので、足元の穴は地面の色で埋めている(見た目だけ)。")
    # (3) 走った経路の全体図
    P = np.array([[(t[1][0] - START_I) * T + t[1][2], t[1][1] * T + t[1][3]] for t in track])
    figs.save_plot("route", [("走った経路(%d 区画、%.0f km)" % (len(first_digest), track[-1][0] / 1000), P[:, 0] / 1000, P[:, 1] / 1000)],
                   xlabel="出発点から東へ [km](出発点 = 1,000 km 先の区画)", ylabel="北へ [km]", title="終わらない地図を走った経路",
                   caption="東寄りに道の網をたどった経路。区画は車の周り 5 × 5 だけを持ち、通った区画は %d(作り直したものを含まない)。" % len(first_digest))


if __name__ == "__main__":
    sys.exit(main())
