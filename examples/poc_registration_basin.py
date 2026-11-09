# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""点群位置合わせの収束域 —— 初期姿勢がどれだけずれたら壊れるか。

EXTEND: 実物の点群に差し替えるなら ``bracket`` を捨てて ``fs.read_points`` で読む。
Stanford Bunny は同梱していないがダウンローダの入口があり、
``fullseye samples download bunny --yes``(= ``py -3.11 imgevolve.py samples
download bunny --yes``)で原典(Stanford 3D Scanning Repository)から取得して
``fs.read_points(sample_data.local_path("bunny"))``。``--yes`` を付けないと
取得するものを表示するだけで、勝手には落とさない。
実物に替えるとき **必ず一緒に変えるもの** が 3 つある。(a) しきい値は形状の直径に
対する比で書いてあるので直径さえ測れば移るが、**点間隔がしきい値より粗いと
「成功不能」になる** —— 第 1 章が測る到達可能な下限を先に見ること。(b) 真値は
自分で剛体変換を掛けて作っている。実スキャン 2 枚を突き合わせる場合は真値が無く、
**誤差ではなく残差しか測れない**(残差が小さいことは正しさの証明にならない ——
第 5-c 章の対称形状がその反例)。(c) 実物は 1 つの標本しか無いので、下の実験の
ように点群を取り直せない。取り直せないぶん、姿勢を振っただけの試行回数を
標本数と読み違えないこと(次の「測り方の罠」)。

**測り方の罠(この PoC を書いていて踏んだ)**: 点群を 1 組作って固定し、真値の姿勢
だけを振って何十回まわしても、**標本は 1 つしか無い**。剛体変換で全体が一緒に回る
ので、主軸の候補順位も ICP の到達精度も試行間で完全に同じ値になる。実際、固定した
まま 40 回まわして「象限誤り 0 %」と「100 %」の両方が形状の違いではなく **乱数の種
の違いだけ** で出た。以下の実験は **すべて試行ごとに点群を取り直している**。

この PoC が示すこと:

1. **回転と並進は別々に出す** —— 1 つの数にまとめると、回転が 180 度ずれたまま
   重心だけ合っている状態(対称形状で普通に起きる)が「中くらいの誤差」に化ける。
2. **収束域には境界がある** —— ICP は初期ずれが小さいうちは確実に決まり、ある
   角度から先で落ちる。その境界を成功率の表で出す。
3. **ゼロ点を置かないと何も言えない** —— 「何もしない」「重心だけ」「PCA だけ」を
   並べる。PCA は主軸の符号で 4 通りの解を持ち、非対称性が弱いほど間違った象限に
   落ちる。その頻度を形状を変えて数える。
4. **収束域の広さと最終精度は別の軸** —— 広いが粗い手法と、狭いが精密な手法が
   ある。同じ点群・同じしきい値で両方を表に出す。
5. **対称形状では「収束したのに間違っている」** —— 球や円柱は残差がほぼ 0 のまま
   姿勢が任意。残差を成功判定に使うとこの嘘は検出できない。

★ この PoC が出した道具の穴は末尾の「道具の穴」節に印字する(op 本体は直していない)。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

# --- 成功の定義(この PoC 全体で使う唯一の判定)-----------------------------
# 回転誤差 < 3 度 かつ 重心移動誤差 < 直径の 1 %。
# これは「精度が十分か」ではなく **正しい盆地に入ったか** の判定。第 1 章が測る
# 下限は 1 度 / 直径の 0.3 % 前後、外した場合は 20-180 度なので、しきい値はその
# 間の空白地帯に置いてある(第 1 章末尾でその空白の広さを数える)。
ROT_OK_DEG = 3.0
CEN_OK_FRAC = 0.01
# 「収束したのに間違っている」の判定はもっと粗くていい。しきい値すれすれの数度は
# 精度の話であって嘘ではないので、明らかに別の姿勢を掴んだ場合だけを数える。
LIE_DEG = 20.0

# 形状の寸法(直方体 + +x 面から突き出す角柱)。角柱の断面で非対称性の強さを変える。
# 角柱は +x 面をまたぐ位置に置き、面の中心から +y +z にずらしてある。こうすると
# x 軸・y 軸・z 軸まわりの 180 度回転がすべて壊れる。
MAIN_DIMS = (1.00, 0.62, 0.38)
PEG_DIMS = (0.24, 0.30, 0.24)      # 断面 (y, z) を bump 倍して弱める
PEG_AT = (0.50, 0.15, 0.08)

N_SRC, N_DST = 500, 700            # 密な組(局所手法用)
N_CSRC, N_CDST = 250, 325          # 粗い組(FPFH / PPF が現実的な時間で回る密度)


# ---------------------------------------------------------------------------
# 形状(真値を自分で作れるように、すべて解析的に生成する)
# ---------------------------------------------------------------------------
def box_surface(dims, n, rng, center=(0.0, 0.0, 0.0)):
    """直方体の**表面**に n 点を面積比で撒く。中身は詰めない(スキャンは表面しか見ない)。"""
    d = np.asarray(dims, np.float64)
    areas = np.array([d[1] * d[2], d[1] * d[2], d[0] * d[2],
                      d[0] * d[2], d[0] * d[1], d[0] * d[1]])
    cnt = rng.multinomial(n, areas / areas.sum())
    out = []
    for face, c in enumerate(cnt):
        u = rng.random((c, 3)) - 0.5
        u[:, face // 2] = 0.5 if face % 2 else -0.5
        out.append(u * d)
    return np.concatenate(out) + np.asarray(center, np.float64)


def _inside(P, dims, center):
    d = np.asarray(dims, np.float64) / 2.0
    return np.all(np.abs(P - np.asarray(center, np.float64)) < d - 1e-12, axis=1)


def bracket(n, rng, bump=1.0):
    """当て金 —— 直方体の +x 面から角柱を突き出したもの。``bump`` が非対称性の強さ。

    ``bump=0`` は素の直方体で、3 軸まわりの 180 度回転で自分自身に重なる(位数 4 の
    真回転対称群)。この 4 通りの姿勢は形からは区別できない。``bump`` を上げると
    角柱の断面が太くなり、その対称がすべて壊れて正しい象限が 1 つに決まる。
    突き出し量は ``bump`` によらず一定なので、変わるのは**非対称な体積の量だけ**。
    """
    if bump <= 0.0:
        return box_surface(MAIN_DIMS, n, rng)
    pd = (PEG_DIMS[0], PEG_DIMS[1] * bump, PEG_DIMS[2] * bump)
    n_peg = max(12, int(round(n * 0.20 * bump)))
    a = box_surface(MAIN_DIMS, n - n_peg, rng)
    b = box_surface(pd, n_peg, rng, PEG_AT)
    a = a[~_inside(a, pd, PEG_AT)]                     # 角柱に隠れる面の点を捨てる
    b = b[~_inside(b, MAIN_DIMS, (0.0, 0.0, 0.0))]     # 本体に埋まる角柱の点を捨てる
    return np.concatenate([a, b])


def plain_box(n, rng):
    """素の直方体(180 度回転 3 つで自分自身に重なる)。"""
    return bracket(n, rng, bump=0.0)


def sphere(n, rng, radius=0.5):
    """球 —— SO(3) 全体で自分自身に重なる。姿勢は原理的に決まらない。"""
    v = rng.normal(size=(n, 3))
    return radius * v / np.linalg.norm(v, axis=1, keepdims=True)


def cylinder(n, rng, radius=0.28, height=1.0):
    """円柱(側面のみ、蓋なし)—— 軸まわりの回転が決まらない。軸の向きは決まる。"""
    th = rng.random(n) * 2.0 * np.pi
    z = (rng.random(n) - 0.5) * height
    return np.stack([radius * np.cos(th), radius * np.sin(th), z], axis=1)


def diameter(P):
    return float(np.linalg.norm(P.max(0) - P.min(0)))


def spacing_of(P):
    """点間隔の中央値 —— しきい値がこれより細かいと原理的に届かない。"""
    return float(np.median(cKDTree(P).query(P, k=2)[0][:, 1]))


# ---------------------------------------------------------------------------
# 点群工場 —— **試行ごとに取り直す**。冒頭の「測り方の罠」を参照。
# ---------------------------------------------------------------------------
def clouds(rng, shape=bracket, n_src=N_SRC, n_dst=N_DST, coarse=False):
    a = shape(n_src, rng)
    b = shape(n_dst, rng)
    k = 16
    if coarse:
        a = a[fs.farthest_point_sampling(a, N_CSRC)]
        b = b[fs.farthest_point_sampling(b, N_CDST)]
        k = 12
    return a, b, fs.estimate_normals(b, k=k), diameter(b)


def fine(rng):
    return clouds(rng)


def coarse(rng):
    return clouds(rng, coarse=True)


# ---------------------------------------------------------------------------
# 真値の剛体変換と、誤差の測り方
# ---------------------------------------------------------------------------
def rot_axis_angle(axis, deg):
    a = np.asarray(axis, np.float64)
    a = a / np.linalg.norm(a)
    th = np.radians(deg)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + np.sin(th) * K + (1.0 - np.cos(th)) * (K @ K)


def random_rot(deg, rng):
    return rot_axis_angle(rng.normal(size=3), deg)


def rot_error_deg(R_est, R_true):
    """2 つの回転の測地距離[度] = R_est·R_true^T の回転角。"""
    c = (np.trace(np.asarray(R_est) @ np.asarray(R_true).T) - 1.0) / 2.0
    return float(np.degrees(np.arccos(np.clip(c, -1.0, 1.0))))


def cen_error(R_est, t_est, R_true, t_true, c_src):
    """重心が行き着く先のずれ[単位]。回転誤差と足し合わせないためにこう定義する。"""
    return float(np.linalg.norm((R_est @ c_src + t_est) - (R_true @ c_src + t_true)))


def ok(rot_deg, cen, diam):
    return (rot_deg < ROT_OK_DEG) and (cen < CEN_OK_FRAC * diam)


def med(a):
    a = np.asarray(a, np.float64)
    return float(np.median(a)) if a.size else float("nan")


def pca_candidates(src, dst, R_true):
    """PCA 位置合わせの姿勢候補 4 つの回転誤差[度]を小さい順に返す。

    主軸は符号まで決まらないので符号の組合せは 8 通り。**そのうち行列式が +1 の
    ものだけが姿勢候補**で、numpy の SVD が返す ``Vt`` の行列式は +1 とは限らない
    (ここを 4 通り決め打ちにしたら、誤差がぴったり 90 度に張り付く結果が出た ——
    鏡映を姿勢として数えていた。PoC 側の誤りで、道具の誤りではない)。
    """
    _, _, VtP = np.linalg.svd(np.asarray(src) - np.asarray(src).mean(0), full_matrices=False)
    _, _, VtQ = np.linalg.svd(np.asarray(dst) - np.asarray(dst).mean(0), full_matrices=False)
    out = []
    for sx in (1.0, -1.0):
        for sy in (1.0, -1.0):
            for sz in (1.0, -1.0):
                R = VtQ.T @ np.diag([sx, sy, sz]) @ VtP
                if np.linalg.det(R) > 0:
                    out.append(rot_error_deg(R, R_true))
    return np.sort(np.array(out))


# ---------------------------------------------------------------------------
# 手法(すべて (R, t) を返す。src -> dst の向き)
# ---------------------------------------------------------------------------
def m_null(src, dst, dn):
    """ゼロ点その 1: 何もしない。"""
    return np.eye(3), np.zeros(3)


def m_centroid(src, dst, dn):
    """ゼロ点その 2: 重心だけ合わせる(回転は諦める)。"""
    return np.eye(3), dst.mean(0) - src.mean(0)


def m_pca(src, dst, dn):
    """ゼロ点その 3: PCA 位置合わせだけ。ICP を回さない。"""
    return fs.pca_align(src, dst)


def m_icp(src, dst, dn):
    return fs.icp(src, dst, max_iter=60)[:2]


def m_p2pl(src, dst, dn):
    return fs.point_to_plane_icp(src, dst, dst_normals=dn, max_iter=60)[:2]


def m_pca_icp(src, dst, dn):
    return fs.register(src, dst, init="pca")[:2]


def m_trim(src, dst, dn):
    return fs.icp(src, dst, init=fs.pca_align(src, dst), trim=0.4, max_iter=60)[:2]


def m_feature(src, dst, dn):
    return fs.feature_register(src, dst, ransac_iter=800, seed=0)[:2]


def m_ppf(src, dst, dn):
    out = fs.find_surface_pose(src, dst, angle_bins=24, ref_fraction=0.25, topk=3)
    return out["R"], out["t"]


# ---------------------------------------------------------------------------
# 一試行 = 点群を取り直し、真値を掛け、復元し、誤差を回転と並進に分けて返す
# ---------------------------------------------------------------------------
def make_pair(dst_base, dst_n_base, rot_deg, trans_frac, diam, rng):
    R_true = random_rot(rot_deg, rng) if rot_deg > 0 else np.eye(3)
    if trans_frac > 0:
        u = rng.normal(size=3)
        t_true = (u / np.linalg.norm(u)) * (trans_frac * diam)
    else:
        t_true = np.zeros(3)
    return (fs.apply_transform(dst_base, R_true, t_true),
            dst_n_base @ R_true.T, R_true, t_true)


def run_cell(method, factory, rot_deg, trans_frac, trials, seed, crop=None):
    """1 セルを trials 回。毎回 factory で点群を取り直す。成功率と誤差列を返す。"""
    rng = np.random.default_rng(seed)
    n_ok = 0
    rots, cens = [], []
    for _ in range(trials):
        src, dst_base, dn_base, diam = factory(rng)
        if crop is not None and crop < 1.0:
            u = rng.normal(size=3)
            u /= np.linalg.norm(u)
            proj = src @ u
            src = src[proj >= np.quantile(proj, 1.0 - crop)]
        dst, dn, R_true, t_true = make_pair(dst_base, dn_base, rot_deg,
                                            trans_frac, diam, rng)
        R, t = method(src, dst, dn)
        rd = rot_error_deg(R, R_true)
        cd = cen_error(R, t, R_true, t_true, src.mean(0))
        rots.append(rd)
        cens.append(cd)
        n_ok += int(ok(rd, cd, diam))
    return n_ok / trials, np.array(rots), np.array(cens)


# ---------------------------------------------------------------------------
# 動画 —— 初期ずれを振った ICP が 1 反復ずつ吸い込まれる/別の盆地に落ちる様子
# ---------------------------------------------------------------------------
VIDEO_ROTS = (30.0, 90.0, 150.0)     # 初期回転ずれ [度](同じ軸で振る)
VIDEO_AXIS = (0.35, -0.55, 0.76)
VIDEO_TRANS_FRAC = 0.10              # 初期並進ずれ(直径比、同じ向き)
VIDEO_ITERS = 60                     # 本文の m_icp と同じ反復予算(40 では 90 度がまだ這っている途中)
VIDEO_SEED = 909090                  # 動画専用の乱数(本文の乱数消費を変えない)


def _vid_txt(img, s, xy, anchor="lt", fs_=12):
    import annotate as AN
    return np.asarray(AN.text_box(img, s, xy, anchor=anchor, font_size=fs_), dtype=np.float64)


def _vid_dots(img, P2, color, r=1):
    """(N,2) の (col,row) を (2r+1) 角の点で塗る。範囲外は捨てる。"""
    h, w = img.shape[:2]
    c = np.round(P2[:, 0]).astype(int)
    rr = np.round(P2[:, 1]).astype(int)
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            cc, ry = c + dx, rr + dy
            m = (cc >= 0) & (cc < w) & (ry >= 0) & (ry < h)
            img[ry[m], cc[m]] = color


def video_icp_basin():
    """初期回転ずれ 30/90/150 度の点対点 ICP を 1 反復ずつ記録して動画にする。

    ``fs.icp(max_iter=1, init=前回)`` を連鎖して途中を取り出す(op 本体は触らない)。
    図を出さない実行では何もしない(所要時間を変えない)。動画用の点群は専用の
    乱数で取り直すので、本文の乱数消費と門の数字は変わらない。
    """
    if not figs.enabled():
        return None
    import annotate as AN

    rng_v = np.random.default_rng(VIDEO_SEED)
    src, dst_base, _dn_base, diam = fine(rng_v)
    u = np.array([0.6, 0.3, -0.74])
    u /= np.linalg.norm(u)
    t_true = u * VIDEO_TRANS_FRAC * diam
    c_src = src.mean(0)
    cases = []
    for deg in VIDEO_ROTS:
        R_true = rot_axis_angle(VIDEO_AXIS, deg)
        dst = fs.apply_transform(dst_base, R_true, t_true)
        R, t = np.eye(3), np.zeros(3)
        Rs, ts = [R], [t]
        rot, cen = [rot_error_deg(R, R_true)], [cen_error(R, t, R_true, t_true, c_src)]
        for _ in range(VIDEO_ITERS):
            R, t = fs.icp(src, dst, max_iter=1, init=(R, t))[:2]
            R, t = np.asarray(R, float), np.asarray(t, float)
            Rs.append(R)
            ts.append(t)
            rot.append(rot_error_deg(R, R_true))
            cen.append(cen_error(R, t, R_true, t_true, c_src))
        # 連鎖 = 一発か: max_iter=VIDEO_ITERS を一度に回した結果と最後の状態を比べる
        R1, t1 = fs.icp(src, dst, max_iter=VIDEO_ITERS, init=(np.eye(3), np.zeros(3)))[:2]
        cases.append(dict(deg=deg, dst=dst, Rs=Rs, ts=ts, rot=np.array(rot), cen=np.array(cen),
                          gap=rot_error_deg(np.asarray(R1), R),
                          gap_t=float(np.linalg.norm(np.asarray(t1) - t)),
                          ok=ok(rot[-1], cen[-1], diam)))
    print("\n=== 動画: 初期ずれを振った点対点 ICP の 1 反復ごとの軌跡(動画専用の点群)===")
    for c in cases:
        print(f"  初期 {c['deg']:>5.0f} 度: {VIDEO_ITERS} 反復後 回転誤差 {c['rot'][-1]:7.2f} 度 / 重心誤差 "
              f"{100 * c['cen'][-1] / diam:5.2f} % 直径 → {'成功' if c['ok'] else '失敗'}"
              f"(1 反復 x{VIDEO_ITERS} の連鎖と max_iter={VIDEO_ITERS} 一発の差: 回転 {c['gap']:.2e} 度 / "
              f"並進 {c['gap_t']:.2e})")

    # 斜めから見る正射影。尺度は dst の直径で全コマ・全パネル共通
    V = rot_axis_angle((1.0, 0.0, 0.0), -28.0) @ rot_axis_angle((0.0, 1.0, 0.0), 35.0)
    PW, PH, PLOT_H = 260, 260, 228
    W = PW * len(cases)
    scale = 0.36 * PW / (0.5 * diam)

    def proj(P, centre):
        q = (np.asarray(P) - centre) @ V.T
        return np.stack([PW / 2 + scale * q[:, 0], PH / 2 + 24 - scale * q[:, 1]], axis=1)

    cols = [(0.90, 0.62, 0.0), (0.0, 0.62, 0.45), (0.80, 0.40, 0.70)]
    ylim = (0.3, 400.0)
    ax = AN.axes_transform((58, PH + 26, W - 80, PLOT_H - 80), (0, VIDEO_ITERS), ylim, yscale="log")
    frames = []
    hold = [0] * 6 + list(range(VIDEO_ITERS + 1)) + [VIDEO_ITERS] * 12
    for k in hold:
        f = np.full((PH + PLOT_H, W, 3), 0.07)
        for j, c in enumerate(cases):
            pan = np.full((PH, PW, 3), 0.10)
            centre = c["dst"].mean(0)
            _vid_dots(pan, proj(c["dst"], centre), (0.55, 0.55, 0.55), r=1)
            cur = fs.apply_transform(src, c["Rs"][k], c["ts"][k])
            _vid_dots(pan, proj(cur, centre), cols[j], r=1)
            pan[:, -2:] = 0.35
            verdict = ""
            if k == VIDEO_ITERS:
                verdict = "\n→ 正しい盆地に入った" if c["ok"] else "\n→ 別の盆地に落ちた"
            pan = _vid_txt(pan, "初期 %.0f 度 / 反復 %d\n回転誤差 %.1f 度\n重心誤差 直径の %.1f %%%s"
                           % (c["deg"], k, c["rot"][k], 100 * c["cen"][k] / diam, verdict), (6, 6), fs_=12)
            f[:PH, j * PW:(j + 1) * PW] = pan
        f = AN.axes_frame(f, ax)
        f = AN.ticks(f, ax, xticks=[0, 10, 20, 30, 40, 50, 60], yticks=[1, 3, 10, 30, 100], font_size=11)
        f = AN.plot_series(f, ax, [0.0, float(VIDEO_ITERS)], [ROT_OK_DEG, ROT_OK_DEG],
                           color=(0.5, 0.5, 0.5), width=1)
        for j, c in enumerate(cases):
            ys = np.clip(c["rot"][:k + 1], ylim[0], ylim[1])
            xs = np.arange(k + 1, dtype=float)
            if k == 0:
                f = AN.plot_series(f, ax, xs, ys, kind="scatter", color=cols[j], marker_size=3)
            else:
                f = AN.plot_series(f, ax, xs, ys, color=cols[j], width=2)
        f = np.asarray(f, np.float64)
        f = _vid_txt(f, "回転誤差 [度](対数)/ 灰線 = 成功のしきい値 %.0f 度" % ROT_OK_DEG,
                     (W - 10, PH + 4), anchor="rt", fs_=11)
        f = _vid_txt(f, "反復の回数", (58 + (W - 80) // 2, PH + PLOT_H - 4), anchor="cb", fs_=11)
        frames.append(np.clip(f, 0.0, 1.0))
    res = "、".join("%.0f 度 → %.1f 度(%s)" % (c["deg"], c["rot"][-1], "成功" if c["ok"] else "失敗")
                   for c in cases)
    figs.save_video(
        "icp_basin_iterations", frames, fps=8, gif_every=1, gif_width=None,
        caption="点対点 ICP を 1 反復ずつ動かす(fs.icp(max_iter=1) を前回の姿勢から連鎖)。灰 = 目標の点群、"
                "色 = 動かしている点群(斜めから見た正射影)。同じ回転軸で初期回転ずれだけを 30 / 90 / 150 度と変え、"
                "並進ずれは直径の %.0f %%。反復予算は本文の点対点 ICP と同じ %d 回で、その後の回転誤差: %s。下の曲線は回転誤差の推移(対数、灰線 = 成功の"
                "しきい値 %.0f 度)。動画専用に取り直した 1 組の点群での 1 試行の軌跡で、成功率は第 2 章の表。"
                % (100 * VIDEO_TRANS_FRAC, VIDEO_ITERS, res, ROT_OK_DEG))
    return cases


# ---------------------------------------------------------------------------
# 7. 実物の走査点群 —— BOP T-LESS(CC BY 4.0)の実機 RGB-D と、走査から作った部品モデル
# ---------------------------------------------------------------------------
# データ: T-LESS(Hodaň et al., WACV 2017)の BOP19 test_primesense と models_reconst。
#   取得 ``py -3.11 tools/fetch_tless.py``。置き場は環境変数 FULLSEYE_TLESS_DATA(未設定なら
#   ``~/fullseye_data/tless`` を見る。そこにも無ければ記録値を印字する —— 手元で実データの章を回すには
#   FULLSEYE_TLESS_DATA を展開先へ向ける)。一次配布 https://bop.felk.cvut.cz/datasets/ の T-LESS 欄に
#   "license: CC BY 4.0"。
# 読むのは 場面 10 の部品 22(models_info に対称の記載が無い = 姿勢が 1 つに決まる部品)が 95 % 以上
# 見えている BOP19 の全フレーム。使う要素は下の一覧の SHA-256 で固定する。センサは市販の構造化光 RGB-D
# センサ(図と字幕には製品名を出さない)。
#
# ★比べ方(2026-11-08 の敵対的レビューで作り直し): 同じ部品 22 のモデルから作った 2 つの対照と、実測を
#   **同じ成功の基準**で並べる —— (A) 全周の点(モデル表面から一様に取る)、(B) 片面の点(実測と同じ
#   フレームの真値の姿勢で、カメラから見える面だけを残す。自己遮蔽は z バッファで近似、雑音なし)、
#   (C) 実測の深度。A→B の差が「片面しか見えない」ぶん、B→C の差が「センサ雑音・欠損・真値の誤差」の分。
#   以前の版は形の違う合成の当て金と比べていたので、差の原因が言えなかった。
REAL_ENV = "FULLSEYE_TLESS_DATA"
REAL_SCENE, REAL_OBJ, REAL_VISIB = 10, 22, 0.95
REAL_PART_JA = "3 口の電源タップ"              # 図に出す部品の呼び名(写真で確かめた一般名)
REAL_N_SRC, REAL_N_DST = 500, 3000            # 動かす点(毎試行取り直す)/ モデルの点(最遠点で固定)
REAL_ROTS = (0.0, 15.0, 30.0, 40.0, 45.0, 50.0, 55.0, 60.0, 65.0, 70.0, 80.0, 90.0, 120.0, 150.0)
REAL_CONDS = (("全周", "full"), ("片面", "side"), ("実測", "real"))
REAL_SEED = 20261108
#: 種(試行ごとの点の取り直しと回転軸)。1 本の値で語らない —— 50 % 角は種の幅で示す。
REAL_SEEDS = (20261108, 1, 2, 3, 4)
#: 使う要素(モデル 1 + models_info + 場面の JSON 3 + 深度と見えている範囲の印)の (名前, SHA-256) を
#: 並べた一覧の SHA-256。2026-11-08 に手元の取得物から計算した値。
REAL_MANIFEST_SHA256 = "36b5bd5da9a3c56adf2f98c11f4f9ac97db654f2bedad651aa943bbf07a7bb7e"
#: 手元で測った記録値(CI ではデータが無いのでこれを印字する)。データがあるときは実測と突き合わせる。
REAL_RECORDED = {
    "lines": [
        '部品 22(対称の記載なし、直径 92.25 mm = BOP)、実測 26 フレーム、毎試行 500 点、モデル 3000 点',
        '真値で置いた実測点とモデルの距離 中央値 1.99 mm / 90 % 点 4.46 mm',
        '50 % を切る角度 点対点(種 5 本の 最小〜最大): 全周 57.5〜62.5 / 片面 49.2〜52.5 / 実測 39.2〜51.0 度',
        '50 % を切る角度 点対面(種 5 本の 最小〜最大): 全周 72.9〜84.0 / 片面 58.3〜66.0 / 実測 44.2〜54.0 度',
        '床と真値のずれ(中央値、実測): 点対点 4.23 度・3.72 mm / 点対面 5.30 度・4.31 mm',
        '真値基準の成功(初期ずれ 0、実測): 点対点 0 % / 点対面 4 %',
        '50 % を最後に切る所(点対面): 全周 72.9〜84.0 / 片面 58.3〜66.0 / 実測 45.0〜65.0 度',
        '15 度での成功率(点対面): 全周 100〜100 % / 片面 100〜100 % / 実測 73〜88 %',
    ],
    'rate': {'p2p': {'full': {'0': 1.0, '15': 1.0, '30': 1.0, '40': 0.8846, '45': 0.7692, '50': 0.6923, '55': 0.7692, '60': 0.5769, '65': 0.4231, '70': 0.2692, '80': 0.0, '90': 0.0385, '120': 0.0, '150': 0.0}, 'side': {'0': 1.0, '15': 0.9231, '30': 0.9615, '40': 0.7308, '45': 0.7692, '50': 0.5385, '55': 0.4231, '60': 0.3846, '65': 0.2308, '70': 0.1538, '80': 0.0, '90': 0.0, '120': 0.0, '150': 0.0}, 'real': {'0': 1.0, '15': 0.7692, '30': 0.9231, '40': 0.4615, '45': 0.6538, '50': 0.5, '55': 0.3077, '60': 0.2308, '65': 0.1923, '70': 0.1154, '80': 0.0, '90': 0.0, '120': 0.0, '150': 0.0}}, 'p2pl': {'full': {'0': 1.0, '15': 1.0, '30': 1.0, '40': 0.9231, '45': 1.0, '50': 0.8846, '55': 0.8077, '60': 0.6538, '65': 0.7692, '70': 0.6538, '80': 0.3846, '90': 0.3462, '120': 0.0385, '150': 0.0}, 'side': {'0': 1.0, '15': 1.0, '30': 1.0, '40': 0.9615, '45': 0.8846, '50': 0.7308, '55': 0.6923, '60': 0.5, '65': 0.3462, '70': 0.4615, '80': 0.1538, '90': 0.0385, '120': 0.0, '150': 0.0}, 'real': {'0': 1.0, '15': 0.7692, '30': 0.6923, '40': 0.6923, '45': 0.4615, '50': 0.5385, '55': 0.5, '60': 0.3846, '65': 0.1538, '70': 0.2692, '80': 0.1538, '90': 0.1154, '120': 0.0385, '150': 0.0}}},
    'half': {'p2p': {'full': [57.5, 61.7, 62.5], 'side': [49.2, 51.7, 52.5], 'real': [39.2, 45.0, 51.0]}, 'p2pl': {'full': [72.9, 75.7, 84.0], 'side': [58.3, 60.0, 66.0], 'real': [44.2, 53.3, 54.0]}},
    'half_last': {'p2p': {'full': [57.5, 62.5], 'side': [49.2, 60.0], 'real': [44.0, 55.8]}, 'p2pl': {'full': [72.9, 84.0], 'side': [58.3, 66.0], 'real': [45.0, 65.0]}},
    'narrow_min': {'p2p': 10.7, 'p2pl': 19.6},
    'narrow_min_last': {'p2p': 1.7, 'p2pl': 7.9},
}


def _real_root():
    import os
    root = Path(os.environ.get(REAL_ENV, str(Path.home() / "fullseye_data" / "tless")))
    model = root / "models_reconst" / f"obj_{REAL_OBJ:06d}.ply"
    scene = root / "test_primesense" / f"{REAL_SCENE:06d}"
    if not model.is_file() or not (scene / "scene_gt.json").is_file():
        return None
    return root


def _real_load(root):
    """部品 22 のモデル(走査の再構成)と、各フレームの実測点(モデル座標へ真値で戻したもの)。

    取得物は信頼しない入力として扱う: 使う要素の一覧の SHA-256 を台帳と照合してから読む。
    直径は BOP の定義(models_info.json の diameter = モデル上の 2 点の最大距離)をそのまま使う。
    """
    import hashlib
    import json

    from PIL import Image

    scene = root / "test_primesense" / f"{REAL_SCENE:06d}"
    model_path = root / "models_reconst" / f"obj_{REAL_OBJ:06d}.ply"
    info_path = root / "models_reconst" / "models_info.json"
    js = {n: json.loads((scene / n).read_text(encoding="utf-8"))
          for n in ("scene_gt.json", "scene_gt_info.json", "scene_camera.json")}
    picks = []
    for im in sorted(js["scene_gt.json"], key=int):
        for k, (g, inf) in enumerate(zip(js["scene_gt.json"][im], js["scene_gt_info.json"][im])):
            if g["obj_id"] == REAL_OBJ and inf["visib_fract"] > REAL_VISIB:
                picks.append((int(im), k, g))
    used = [model_path, info_path] + [scene / n for n in sorted(js)]
    for im, k, _g in picks:
        used += [scene / "depth" / f"{im:06d}.png", scene / "mask_visib" / f"{im:06d}_{k:06d}.png"]

    def sha(p):
        h = hashlib.sha256()
        with p.open("rb") as fh:
            for blk in iter(lambda: fh.read(1 << 20), b""):
                h.update(blk)
        return h.hexdigest()

    listing = "\n".join("%s %s" % (p.relative_to(root).as_posix(), sha(p)) for p in used).encode("ascii")
    digest = hashlib.sha256(listing).hexdigest()
    if REAL_MANIFEST_SHA256 is not None and digest != REAL_MANIFEST_SHA256:
        raise ValueError("T-LESS の要素の一覧の SHA-256 %s が台帳 %s と違う" % (digest, REAL_MANIFEST_SHA256))
    info = json.loads(info_path.read_text(encoding="utf-8"))[str(REAL_OBJ)]
    bop_diam = float(info["diameter"])
    if "symmetries_discrete" in info or "symmetries_continuous" in info:
        raise ValueError("部品 %d に対称の記載がある —— 姿勢が 1 つに決まらないので選び直す" % REAL_OBJ)

    # 頂点と法線(T-LESS の ASCII PLY。先頭 6 列が xyz / nxyz であることを確かめてから読む)
    with model_path.open("r", encoding="ascii") as fh:
        head = []
        while True:
            line = fh.readline()
            if not line:
                raise ValueError("PLY に end_header が無い")
            head.append(line.strip())
            if line.strip() == "end_header":
                break
        nv = int(next(h for h in head if h.startswith("element vertex ")).split()[2])
        props = [h.split()[-1] for h in head if h.startswith("property ")]
        if props[:6] != ["x", "y", "z", "nx", "ny", "nz"]:
            raise ValueError("PLY の先頭 property が xyz / nxyz でない: %s" % props[:6])
        v = np.loadtxt(fh, dtype=np.float64, max_rows=nv)
    mp, mn = v[:, :3], v[:, 3:6] / np.linalg.norm(v[:, 3:6], axis=1, keepdims=True)
    idx = fs.farthest_point_sampling(mp, REAL_N_DST)
    model, normals = mp[idx], mn[idx]

    frames = []
    for im, k, g in picks:
        cam = js["scene_camera.json"][str(im)]
        K = np.asarray(cam["cam_K"], np.float64).reshape(3, 3)
        depth = np.asarray(Image.open(scene / "depth" / f"{im:06d}.png"), np.float64) * float(cam["depth_scale"])
        mask = np.asarray(Image.open(scene / "mask_visib" / f"{im:06d}_{k:06d}.png")) > 0
        P = fs.depth_to_points(np.where(mask, depth, 0.0), K)
        P = P[np.isfinite(P).all(axis=1) & (P[:, 2] > 0)]
        R = np.asarray(g["cam_R_m2c"], np.float64).reshape(3, 3)
        t = np.asarray(g["cam_t_m2c"], np.float64)
        frames.append(dict(image=im, inst=k, pts=(P - t) @ R, R=R, t=t, K=K,       # 真値でモデル座標へ戻す
                           side=_visible_side(mp, mn, R, t, K)))
    return model, normals, mp, frames, digest, len(used), bop_diam


def _visible_side(mp, mn, R, t, K, cell=2.0):
    """真値の姿勢でカメラから見えるモデルの面(対照 B)。裏向きの面を捨て、z バッファ(画素 ``cell`` 角)で
    手前の点だけを残す。返りはモデル座標の点。"""
    pc = mp @ R.T + t
    nc = mn @ R.T
    front = np.einsum("ij,ij->i", nc, -pc / np.linalg.norm(pc, axis=1, keepdims=True)) > 0.05
    pc, keep = pc[front], np.flatnonzero(front)
    uv = (pc @ K.T)[:, :2] / pc[:, 2:3]
    key = np.floor(uv / cell).astype(np.int64)
    order = np.lexsort((pc[:, 2], key[:, 1], key[:, 0]))
    k2 = key[order]
    first = np.ones(len(order), bool)
    first[1:] = np.any(k2[1:] != k2[:-1], axis=1)
    near = order[first]
    zmin = dict(zip(map(tuple, key[near]), pc[near, 2]))
    zref = np.array([zmin[tuple(kk)] for kk in key])
    vis = pc[:, 2] <= zref + 3.0                                  # 同じ画素で最も手前から 3 mm 以内
    return mp[keep[vis]]


def _real_trial(method, src, dst, dn, deg, rng, diam):
    """1 試行: 真値から始めた到達点(床)と、ずらして始めた到達点を比べる。

    実測の点はセンサの系統誤差と真値の誤差を含むので、真値そのものには届かない。そこで
    「真値から始めた ICP の行き先」を床とし、**同じ床に戻れたか** を盆地の判定にする(3 条件とも同じ判定)。
    床と真値のずれは別に返す(精度の軸。盆地とは混ぜない)。
    """
    dstT, dnT, R_true, t_true = make_pair(dst, dn, deg, 0.0, diam, rng)
    if method == "p2p":
        Rf, tf = fs.icp(src, dstT, max_iter=60, init=(R_true, t_true))[:2]
        R, t = m_icp(src, dstT, dnT)
    else:
        Rf, tf = fs.point_to_plane_icp(src, dstT, dst_normals=dnT, max_iter=60, init=(R_true, t_true))[:2]
        R, t = m_p2pl(src, dstT, dnT)
    c = src.mean(0)
    Rf, tf, R, t = (np.asarray(a, np.float64) for a in (Rf, tf, R, t))
    to_floor = (rot_error_deg(R, Rf), float(np.linalg.norm((R @ c + t) - (Rf @ c + tf))))
    floor_gt = (rot_error_deg(Rf, R_true), cen_error(Rf, tf, R_true, t_true, c))
    return ok(to_floor[0], to_floor[1], diam), to_floor, floor_gt


def _half_angle(rates, last=False):
    """成功率が 50 % を切る角度を、隣の格子点の間で線形補間して返す(切らなければ 180)。

    ★成功率は 1 フレーム = 3.8 % の粒度で上下するので、50 % を下向きに横切る所が 2 か所以上ある行がある。
    既定(``last=False``)は**最初に**切る所、``last=True`` は**最後に**切る所。両方を出し、幅として読む。
    """
    xs = list(REAL_ROTS)
    hits = []
    for i in range(1, len(xs)):
        r0, r1 = rates["%.0f" % xs[i - 1]], rates["%.0f" % xs[i]]
        if r0 >= 0.5 > r1:
            hits.append(float(xs[i - 1] + (r0 - 0.5) / (r0 - r1) * (xs[i] - xs[i - 1])))
    if not hits:
        return 180.0
    return hits[-1] if last else hits[0]


def real_scan_chapter(syn_half):
    """第 7 章。``syn_half`` は合成の当て金の 50 % 角(参考に印字するだけ。形が違うので比べない)。"""
    print("\n=== 7. 実物の走査点群 —— T-LESS の実機 RGB-D(構造化光センサ)と走査から作った部品モデル ===")
    root = _real_root()
    if root is None:
        print(f"  T-LESS が手元に無い(CI の既定)。取得: py -3.11 tools/fetch_tless.py(置き場は {REAL_ENV})")
        if REAL_RECORDED is None:
            raise AssertionError("記録値 REAL_RECORDED が空 —— 手元でデータありの実行をして転記する")
        for line in REAL_RECORDED["lines"]:
            print("  [記録値] " + line)
        # ★ここは記録値どうしの門で、記録の形と結論の向きしか見ない(記録が古いかはデータありの実行が見る)。
        assert min(REAL_RECORDED["narrow_min"].values()) > 0, "記録値: 実測の盆地が全周より狭くない種がある"
        assert min(REAL_RECORDED["narrow_min_last"].values()) > 0, "記録値: 最後に切る所で実測が全周より狭くない種がある"
        return REAL_RECORDED
    model, normals, mp, frames, digest, n_used, diam = _real_load(root)
    import realdata
    realdata.mark_read("bop_tless:test_primesense/%06d:obj%02d" % (REAL_SCENE, REAL_OBJ))
    print(f"  部品 {REAL_OBJ}({REAL_PART_JA}、対称の記載なし)。直径 {diam:.2f} mm(BOP の models_info = 2 点の最大距離)。"
          f"モデル = 走査の再構成 {REAL_N_DST} 点(最遠点抽出、点間隔 {spacing_of(model):.2f} mm)")
    print(f"  実測 = 場面 {REAL_SCENE} の BOP19 フレームのうち 95 % 以上見えている {len(frames)} 枚の深度。"
          f"1 枚あたり {min(len(f['pts']) for f in frames)}〜{max(len(f['pts']) for f in frames)} 点 → 毎試行 "
          f"{REAL_N_SRC} 点を取り直す")
    print(f"  使った要素 {n_used} 個の一覧の SHA-256 {digest}")
    tree = cKDTree(model)
    fit = np.concatenate([tree.query(f["pts"])[0] for f in frames])
    print(f"  真値の姿勢で置いた実測点からモデルまでの距離: 中央値 {np.median(fit):.2f} mm、90 % 点 {np.percentile(fit, 90):.2f} mm"
          "(センサの雑音 + 真値の誤差 + 走査モデルの誤差の和)")
    print("  同じ部品で 3 条件: 全周 = モデル表面から一様に / 片面 = 実測と同じ視点で見える面だけ(雑音なし)/ 実測 = 深度")
    print("  1 試行 = フレームを 1 枚(順に巡回)+ 回転軸を乱数で選び、初期回転ずれだけを与えて ICP(並進ずれ 0)。")
    print("  判定 = 真値から始めた ICP の行き先(床)に、回転 3 度 / 重心 直径の 1 % 以内で戻れたか(3 条件とも同じ)。")
    def basin(seed, show):
        rng = np.random.default_rng(seed)
        rate = {m: {c: {} for _, c in REAL_CONDS} for m in ("p2p", "p2pl")}
        floor = {m: {c: [] for _, c in REAL_CONDS} for m in ("p2p", "p2pl")}
        if show:
            print(f"  {'初期回転 [度]':<16}" + "".join(f"{d:>6.0f}" for d in REAL_ROTS) + f"   (種 {seed})")
        for meth in ("p2p", "p2pl"):
            for label, cond in REAL_CONDS:
                row = []
                for deg in REAL_ROTS:
                    oks = []
                    for fr in frames:
                        pool = {"full": mp, "side": fr["side"], "real": fr["pts"]}[cond]
                        src = pool[rng.choice(len(pool), REAL_N_SRC, replace=False)]
                        good, _tf, fg = _real_trial(meth, src, model, normals, deg, rng, diam)
                        oks.append(good)
                        if deg == 0.0:
                            floor[meth][cond].append(fg)
                    rate[meth][cond]["%.0f" % deg] = round(float(np.mean(oks)), 4)
                    row.append(np.mean(oks))
                if show:
                    print(f"  {('点対点 ' if meth == 'p2p' else '点対面 ') + label:<14}"
                          + "".join(f"{100 * v:>5.0f}%" for v in row))
        return rate, floor

    runs = [basin(sd, k == 0) for k, sd in enumerate(REAL_SEEDS)]
    rate, floor = runs[0]
    halves = {m: {c: [round(_half_angle(r[m][c]), 1) for r, _f in runs] for _, c in REAL_CONDS} for m in rate}
    halves_last = {m: {c: [round(_half_angle(r[m][c], last=True), 1) for r, _f in runs] for _, c in REAL_CONDS}
                   for m in rate}
    half = {m: {c: [min(v), float(np.median(v)), max(v)] for c, v in halves[m].items()} for m in halves}
    fl = {m: {c: np.median(np.asarray(floor[m][c]), axis=0) for _, c in REAL_CONDS} for m in floor}
    gt_ok = {m: float(np.mean([(a < ROT_OK_DEG) and (b < CEN_OK_FRAC * diam) for a, b in floor[m]["real"]])) for m in floor}
    print(f"  成功率が 50 % を切る角度(格子の間を線形補間)、種 {len(REAL_SEEDS)} 本の 最小 / 中央 / 最大:")
    for m in ("p2p", "p2pl"):
        print(f"    {'点対点' if m == 'p2p' else '点対面'}: "
              + " / ".join(f"{lab} {half[m][c][0]:.1f}〜{half[m][c][2]:.1f}(中央 {half[m][c][1]:.1f})度" for lab, c in REAL_CONDS))
    hl = {m: {c: [min(v), max(v)] for c, v in halves_last[m].items()} for m in halves_last}
    print("  同じ角を『最後に』50 % を切る所で取ると(上下する行で値が変わる):")
    for m in ("p2p", "p2pl"):
        print(f"    {'点対点' if m == 'p2p' else '点対面'}: "
              + " / ".join(f"{lab} {hl[m][c][0]:.1f}〜{hl[m][c][1]:.1f} 度" for lab, c in REAL_CONDS))
    k_narrow = int(np.argmin(halves["p2pl"]["real"]))
    print(f"  動画と上の表の種 {REAL_SEEDS[0]} は、実測の 50 % 角(点対面、最初に切る所)が 5 本の中で"
          f"{'最も狭く出る種' if k_narrow == 0 else '最も狭い種ではない(最も狭いのは種 %d)' % REAL_SEEDS[k_narrow]}。")
    small = {c: [r["p2pl"][c]["15"] for r, _f in runs] for _, c in REAL_CONDS}
    print("  初期ずれの小さい側(15 度、点対面、種 5 本の最小〜最大): "
          + " / ".join(f"{lab} {100 * min(small[c]):.0f}〜{100 * max(small[c]):.0f} %" for lab, c in REAL_CONDS)
          + f" —— 実測では 15 度でも {100 - 100 * max(small['real']):.0f}〜{100 - 100 * min(small['real']):.0f} % が床に戻れない。")
    dd = {m: {"side": [halves[m]["full"][k] - halves[m]["side"][k] for k in range(len(REAL_SEEDS))],
              "real": [halves[m]["side"][k] - halves[m]["real"][k] for k in range(len(REAL_SEEDS))],
              "all": [halves[m]["full"][k] - halves[m]["real"][k] for k in range(len(REAL_SEEDS))]} for m in halves}
    print(f"  床と真値のずれ(中央値、実測、種 {REAL_SEEDS[0]}): 点対点 {fl['p2p']['real'][0]:.2f} 度・{fl['p2p']['real'][1]:.2f} mm / "
          f"点対面 {fl['p2pl']['real'][0]:.2f} 度・{fl['p2pl']['real'][1]:.2f} mm(全周では {fl['p2pl']['full'][0]:.2f} 度)")
    print(f"  ★真値を基準にすると、実測では初期ずれ 0 でも 3 度 / 直径の 1 % に入るのは 点対点 {100 * gt_ok['p2p']:.0f} %・"
          f"点対面 {100 * gt_ok['p2pl']:.0f} % —— この章の『成功』は精度ではなく『同じ床に戻れたか』(盆地の広さ)。")
    print(f"  (参考: 形の違う合成の当て金の 50 % 角は 点対点 {syn_half['p2p']:.0f} 度・点対面 {syn_half['p2pl']:.0f} 度。"
          "部品が違うので比べない)")
    for m in ("p2p", "p2pl"):
        print(f"  → {'点対点' if m == 'p2p' else '点対面'}: 全周 → 実測で {min(dd[m]['all']):.1f}〜{max(dd[m]['all']):.1f} 度狭まる"
              f"(うち全周 → 片面 {min(dd[m]['side']):.1f}〜{max(dd[m]['side']):.1f}、片面 → 実測 "
              f"{min(dd[m]['real']):.1f}〜{max(dd[m]['real']):.1f} 度)。")
    dd_last = {m: [halves_last[m]["full"][k] - halves_last[m]["real"][k] for k in range(len(REAL_SEEDS))] for m in halves_last}
    for m in ("p2p", "p2pl"):
        print(f"  → {'点対点' if m == 'p2p' else '点対面'}: 『最後に切る所』で取ると、全周 → 実測の狭まりは種ごとに "
              + " / ".join("%.1f" % v for v in dd_last[m]) + f" 度(最小 {min(dd_last[m]):.1f} 度)。")
    print("    全周より実測が狭いことは種にも取り方にもよらない(ただし差の大きさは取り方で 2 倍以上変わる)。")
    print("    片面と実測の分け方は種で大きく揺れるので、内訳は言わない。")
    print(f"    1 フレーム = {100 / len(frames):.1f} % の粒度で、隣の角度どうしの成功率は数フレームぶん前後する(単調でない行がある)。")
    # 門(種によらない主張だけ)
    for r_, _f in runs:
        for m in ("p2p", "p2pl"):
            assert r_[m]["real"]["0"] == 1.0 and r_[m]["full"]["0"] == 1.0, "真値から始めて床に戻れない(判定の作りが壊れた)"
    for m in ("p2p", "p2pl"):
        assert min(dd[m]["all"]) > 0, "種によって実測の盆地が全周より狭くない —— 結論を書き直せ"
        assert min(dd_last[m]) > 0, "『最後に切る所』で取ると実測の盆地が全周より狭くない種がある —— 結論を書き直せ"
    lines = [
        "部品 %d(対称の記載なし、直径 %.2f mm = BOP)、実測 %d フレーム、毎試行 %d 点、モデル %d 点"
        % (REAL_OBJ, diam, len(frames), REAL_N_SRC, REAL_N_DST),
        "真値で置いた実測点とモデルの距離 中央値 %.2f mm / 90 %% 点 %.2f mm" % (np.median(fit), np.percentile(fit, 90)),
    ] + ["50 %% を切る角度 %s(種 %d 本の 最小〜最大): 全周 %.1f〜%.1f / 片面 %.1f〜%.1f / 実測 %.1f〜%.1f 度"
         % (lab, len(REAL_SEEDS), half[m]["full"][0], half[m]["full"][2], half[m]["side"][0], half[m]["side"][2],
            half[m]["real"][0], half[m]["real"][2])
         for m, lab in (("p2p", "点対点"), ("p2pl", "点対面"))] + [
        "床と真値のずれ(中央値、実測): 点対点 %.2f 度・%.2f mm / 点対面 %.2f 度・%.2f mm"
        % (fl["p2p"]["real"][0], fl["p2p"]["real"][1], fl["p2pl"]["real"][0], fl["p2pl"]["real"][1]),
        "真値基準の成功(初期ずれ 0、実測): 点対点 %.0f %% / 点対面 %.0f %%" % (100 * gt_ok["p2p"], 100 * gt_ok["p2pl"]),
    ]
    lines += ["50 %% を最後に切る所(点対面): 全周 %.1f〜%.1f / 片面 %.1f〜%.1f / 実測 %.1f〜%.1f 度"
              % (hl["p2pl"]["full"][0], hl["p2pl"]["full"][1], hl["p2pl"]["side"][0], hl["p2pl"]["side"][1],
                 hl["p2pl"]["real"][0], hl["p2pl"]["real"][1]),
              "15 度での成功率(点対面): " + " / ".join("%s %.0f〜%.0f %%" % (lab, 100 * min(small[c]), 100 * max(small[c]))
                                                for lab, c in REAL_CONDS)]
    rec = {"lines": lines, "rate": rate, "half": half, "half_last": hl,
           "narrow_min": {m: round(min(dd[m]["all"]), 1) for m in dd},
           "narrow_min_last": {m: round(min(dd_last[m]), 1) for m in dd_last}}
    print("  REAL_RECORDED = %r" % (rec,))
    # ★データがあるときは、測った値と埋め込みの記録値を突き合わせる(決定的な計算。CI の門は記録どうしなので)。
    if REAL_RECORDED is not None:
        assert rec == REAL_RECORDED, "REAL_RECORDED が実測と違う(記録を転記し直す)"
    seed_note = ("本文の表に出す代表の種は、実測の 50 % 角が 5 本の中で最も狭く出る種。" if k_narrow == 0 else
                 "本文の表に出す代表の種は、実測の 50 %% 角が 5 本の中で最も狭い種ではない(最も狭いのは種 %d)。" % REAL_SEEDS[k_narrow])
    video_real_scan(root, model, normals, frames, diam, rate, half, float(fl["p2pl"]["real"][0]), hl, small, seed_note)
    return rec


REAL_VIDEO_ROTS = (30.0, 60.0, 120.0)


def video_real_scan(root, model, normals, frames, diam, rate, half, floor_med, hl, small, seed_note):
    """代表の動画: 実機の写真の上に、ICP が今そう推定している姿勢の部品モデルを重ねる(点対面、30 / 60 / 120 度)。"""
    if not figs.enabled():
        return None
    from PIL import Image, ImageDraw, ImageFont

    fr = frames[0]
    rgb = np.asarray(Image.open(root / "test_primesense" / f"{REAL_SCENE:06d}" / "rgb" / f"{fr['image']:06d}.png")
                     .convert("RGB"))
    rng = np.random.default_rng(REAL_SEED + 1)
    src = fr["pts"][rng.choice(len(fr["pts"]), REAL_N_SRC, replace=False)]
    c_src = src.mean(0)
    cases = []
    for deg in REAL_VIDEO_ROTS:
        R_true = rot_axis_angle(VIDEO_AXIS, deg)
        t_true = np.zeros(3)
        dst = fs.apply_transform(model, R_true, t_true)
        dn = normals @ R_true.T
        Rf, tf = fs.point_to_plane_icp(src, dst, dst_normals=dn, max_iter=60, init=(R_true, t_true))[:2]
        Rf, tf = np.asarray(Rf, float), np.asarray(tf, float)
        R, t = np.eye(3), np.zeros(3)
        Rs, ts, rot = [R], [t], [rot_error_deg(R, Rf)]
        for _ in range(VIDEO_ITERS):
            R, t = fs.point_to_plane_icp(src, dst, dst_normals=dn, max_iter=1, init=(R, t))[:2]
            R, t = np.asarray(R, float), np.asarray(t, float)
            Rs.append(R)
            ts.append(t)
            rot.append(rot_error_deg(R, Rf))
        cen = float(np.linalg.norm((R @ c_src + t) - (Rf @ c_src + tf)))
        cases.append(dict(deg=deg, R_true=R_true, Rs=Rs, ts=ts, rot=np.array(rot), ok=ok(rot[-1], cen, diam)))
    print("  [動画] 点対面 ICP、フレーム %d(実測): " % fr["image"]
          + "、".join("%.0f 度 → 床との差 %.1f 度(%s)" % (c["deg"], c["rot"][-1], "成功" if c["ok"] else "失敗")
                     for c in cases))

    font = lambda n, b=False: ImageFont.truetype(str(figs._japanese_font_path(bold=b)), n)
    W, H = 960, 600
    # 写真の切り抜き(部品の周り)。推定の姿勢のモデルをこの写真へ投影して重ねる。
    uv0 = (fr["pts"] @ fr["R"].T + fr["t"]) @ fr["K"].T
    uv0 = uv0[:, :2] / uv0[:, 2:3]
    cx, cy = np.median(uv0, axis=0)
    hw = 120
    x0 = int(np.clip(cx - hw, 0, rgb.shape[1] - 2 * hw))
    y0 = int(np.clip(cy - hw, 0, rgb.shape[0] - 2 * hw))
    crop = Image.fromarray(rgb[y0:y0 + 2 * hw, x0:x0 + 2 * hw])
    PS = 300                                                     # 1 枠の表示の大きさ
    sc = PS / (2.0 * hw)
    cols = [(255, 170, 0), (0, 200, 140), (230, 110, 200)]

    def overlay(c, k):
        """推定 (R, t) のときに部品モデルがカメラのどこに来るか: src ≈ R^T (R_true x − t) を真値でカメラへ。"""
        R, t = c["Rs"][k], c["ts"][k]
        xm = (model @ c["R_true"].T - t) @ R                      # モデル座標(推定の姿勢)
        pc = xm @ fr["R"].T + fr["t"]
        uv = pc @ fr["K"].T
        uv = uv[:, :2] / uv[:, 2:3]
        im = crop.resize((PS, PS), Image.Resampling.LANCZOS)
        d = ImageDraw.Draw(im)
        q = (uv - np.array([x0, y0])) * sc
        for (u, v) in q[::2]:
            if 0 <= u < PS and 0 <= v < PS:
                d.point((u, v), fill=cols[REAL_VIDEO_ROTS.index(c["deg"])])
        return im

    def card(lines, pic=None):
        im = Image.new("RGB", (W, H), (12, 16, 22))
        d = ImageDraw.Draw(im)
        y = 36
        for i, s_ in enumerate(lines):
            d.text((36, y), s_, font=font(28 if i == 0 else 21, i == 0), fill=(240, 240, 240) if i == 0 else (205, 210, 220))
            y += 52 if i == 0 else 34
        if pic is not None:
            im.paste(pic, (W - pic.width - 30, H - pic.height - 24))   # 文字の下に置く(重ねない)
        return np.asarray(im)

    frames_v = []
    big = crop.resize((300, 300), Image.Resampling.LANCZOS)
    frames_v += [card(["入れるもの: 実物の部品の走査点群(T-LESS の部品 %d)" % REAL_OBJ,
                       "%s(対称の記載なし、直径 %.0f mm)" % (REAL_PART_JA, diam),
                       "・実測: 構造化光 RGB-D センサの深度から、部品の見えている面 %d 点" % REAL_N_SRC,
                       "・モデル: 走査から再構成した 3-D モデル %d 点" % REAL_N_DST,
                       "初期姿勢を 30 / 60 / 120 度ずらして点対面 ICP を回し、",
                       "真値から始めたときと同じ姿勢(床)に戻れるかを見る。"], big)] * 32
    hold = [0] * 8 + [i for i in range(VIDEO_ITERS + 1) for _ in range(2)] + [VIDEO_ITERS] * 16
    for k in hold:
        im = Image.new("RGB", (W, H), (12, 16, 22))
        d = ImageDraw.Draw(im)
        d.text((16, 10), "実機の写真に、ICP がいま推定している姿勢の部品モデル(色の点)を重ねる", font=font(20), fill=(235, 235, 235))
        for j, c in enumerate(cases):
            xo = 15 + j * (PS + 15)
            im.paste(overlay(c, k), (xo, 44))
            verdict = ""
            if k == VIDEO_ITERS:
                verdict = " → 戻れた" if c["ok"] else " → 戻れない"
            d.rectangle((xo, 44, xo + PS, 96), fill=(0, 0, 0))
            d.text((xo + 6, 48), "初期 %.0f 度 / 反復 %d" % (c["deg"], k), font=font(18, True), fill=(240, 240, 240))
            d.text((xo + 6, 72), "床との回転差 %.1f 度%s" % (c["rot"][k], verdict), font=font(18),
                   fill=(255, 140, 120) if (k == VIDEO_ITERS and not c["ok"]) else (220, 220, 220))
        gx0, gy0, gw, gh = 70, 390, 860, 150
        d.rectangle((gx0, gy0, gx0 + gw, gy0 + gh), outline=(150, 150, 150))
        lo, hi = np.log10(0.3), np.log10(400.0)
        yv = lambda v: gy0 + gh - (np.log10(np.clip(v, 0.3, 400.0)) - lo) / (hi - lo) * gh
        xv = lambda i: gx0 + i / VIDEO_ITERS * gw
        for tk in (1, 3, 10, 30, 100):
            d.text((gx0 - 40, yv(tk) - 10), "%g" % tk, font=font(15), fill=(180, 180, 180))
        d.line((gx0, yv(ROT_OK_DEG), gx0 + gw, yv(ROT_OK_DEG)), fill=(110, 110, 110), width=1)
        for j, c in enumerate(cases):
            pts_ = [(xv(i), yv(c["rot"][i])) for i in range(k + 1)]
            if len(pts_) >= 2:
                d.line(pts_, fill=cols[j], width=3)
        d.text((gx0, gy0 - 26), "床との回転差 [度](対数、灰線 = 判定のしきい値 %.0f 度)" % ROT_OK_DEG, font=font(17), fill=(210, 210, 210))
        d.text((gx0 + gw // 2 - 40, gy0 + gh + 6), "反復の回数", font=font(17), fill=(210, 210, 210))
        frames_v.append(np.asarray(im))
    fin = Image.new("RGB", (W, H), (12, 16, 22))
    d = ImageDraw.Draw(fin)
    d.text((36, 30), "何が分かったか(同じ部品・同じ判定、%d フレーム × 乱数の回転軸)" % len(frames), font=font(26, True), fill=(240, 240, 240))
    d.text((36, 82), "成功率が 50 %% を切る初期回転(点対面 ICP、種 %d 本の幅)" % len(REAL_SEEDS), font=font(22),
           fill=(205, 210, 220))
    for i, (lab, cnd, note) in enumerate((("全周の点", "full", "モデルの表面から一様に"),
                                         ("片面の点", "side", "実測と同じ視点で見える面だけ、雑音なし"),
                                         ("実測の深度", "real", "構造化光センサ"))):
        d.text((56, 126 + 44 * i), "%s  %.0f〜%.0f 度" % (lab, half["p2pl"][cnd][0], half["p2pl"][cnd][2]),
               font=font(26, True), fill=(240, 240, 240))
        d.text((400, 130 + 44 * i), note, font=font(19), fill=(190, 195, 205))
    d.text((36, 262), "最初に 50 %% を切る所で取った値。最後に切る所で取ると 実測 %.0f〜%.0f 度(成功率が上下する行がある)。"
           % (hl["p2pl"]["real"][0], hl["p2pl"]["real"][1]), font=font(17), fill=(200, 205, 215))
    d.text((36, 286), "15 度での成功率: 全周 %.0f〜%.0f %% / 実測 %.0f〜%.0f %%。実測は全周より狭い(どの種でも)。"
           % (100 * min(small["full"]), 100 * max(small["full"]), 100 * min(small["real"]), 100 * max(small["real"])),
           font=font(17), fill=(225, 225, 225))
    d.text((36, 312), "★判定は『真値から始めた ICP の行き先(床)に戻れたか』。実測の床は真値から", font=font(19), fill=(255, 190, 120))
    d.text((36, 338), "  中央値 %.1f 度ずれる —— 盆地の広さを測っており、精度は測っていない。" % floor_med,
           font=font(19), fill=(255, 190, 120))
    fin.paste(crop.resize((220, 220), Image.Resampling.LANCZOS), (W - 250, H - 260))
    d.text((36, H - 40), "データ: T-LESS(Hodaň et al., WACV 2017)、CC BY 4.0", font=font(16), fill=(170, 170, 170))
    frames_v += [np.asarray(fin)] * 48
    cap = ("実物の部品(T-LESS の部品 %d = %s、CC BY 4.0)で ICP の収束域を測った動画。構造化光 RGB-D センサの深度から切り出した"
           "見えている面 %d 点を、走査から再構成したモデル %d 点へ点対面 ICP で合わせ、推定中の姿勢のモデルを実機の写真に重ねる。"
           "同じ部品・同じ判定(真値から始めた ICP の行き先に戻れたか)で、成功率が 50 %% を切る初期回転は "
           "全周の点 %.0f〜%.0f 度・片面の点 %.0f〜%.0f 度・実測の深度 %.0f〜%.0f 度(点対面、%d フレーム、乱数の種 %d 本の幅)。"
           "実測が全周より狭いことはどの種でも成り立つが、片面と実測の内訳は種で揺れる。50 %% 角は最初に 50 %% を切る所で取った値で、"
           "最後に切る所で取ると実測は %.0f〜%.0f 度。"
           % (REAL_OBJ, REAL_PART_JA, REAL_N_SRC, REAL_N_DST, half["p2pl"]["full"][0], half["p2pl"]["full"][2],
              half["p2pl"]["side"][0], half["p2pl"]["side"][2], half["p2pl"]["real"][0], half["p2pl"]["real"][2],
              len(frames), len(REAL_SEEDS), hl["p2pl"]["real"][0], hl["p2pl"]["real"][1]) + seed_note)
    return figs.save_video("real_scan_icp", [f.astype(np.float64) / 255.0 for f in frames_v], fps=8, gif_every=4,
                           gif_width=720, caption=cap)


# ---------------------------------------------------------------------------
def main():
    t_start = time.perf_counter()

    rng0 = np.random.default_rng(20260906)
    src0, dst0, dn0, diam0 = fine(rng0)

    print("=== 0. 舞台 ===")
    print(f"  形状 = 非対称な当て金(直方体 {MAIN_DIMS} + +x 面から突き出す角柱 {PEG_DIMS})")
    print(f"  点数 src {src0.shape[0]} / dst {dst0.shape[0]}"
          "(同じ面からの**独立な**標本。対応点は存在しない)")
    print(f"  直径 {diam0:.4f} 単位 / dst の点間隔 中央値 {spacing_of(dst0):.4f} 単位"
          f"(直径の {100 * spacing_of(dst0) / diam0:.2f} %)")
    print(f"  成功の定義: 回転誤差 < {ROT_OK_DEG:.0f} 度 かつ 重心誤差 < 直径の "
          f"{100 * CEN_OK_FRAC:.0f} %")
    print("  これは精度の判定ではなく **正しい盆地に入ったか** の判定。精度は別列で出す。")
    print("  誤差は回転[度]と並進[単位]に分ける。並進誤差 = src の重心が行き着く先のずれ。")
    print("  **すべての試行で点群を取り直す**(固定すると姿勢を振っても標本が増えない)。")

    # ---- 1. 真値の復元と、到達できる下限 ---------------------------------
    print("\n=== 1. 真値を自分で作って復元する —— 下限はどこか ===")
    R_true = rot_axis_angle((0.3, -0.7, 0.65), 37.0)
    t_true = np.array([0.21, -0.13, 0.07])
    dst_exact = fs.apply_transform(src0, R_true, t_true)
    Rk, tk = fs.kabsch(src0, dst_exact)
    print(f"  対応点が既知なら閉形式: kabsch の回転誤差 {rot_error_deg(Rk, R_true):.2e} 度 / "
          f"並進誤差 {cen_error(Rk, tk, R_true, t_true, src0.mean(0)):.2e} 単位")
    print("  対応点が無く標本も別の場合の下限(真値から開始、16 試行、毎回取り直し):")
    print(f"  {'点群':<20}{'手法':<14}{'回転 中央値[度]':>16}{'回転 90 %tile':>15}"
          f"{'並進 中央値[直径比]':>22}")
    floors = {}
    all_floor_rot = []
    for cname, fac in (("密 500/700", fine), ("粗 250/325", coarse)):
        rngf = np.random.default_rng(4004)
        rows = {"点対点 ICP": ([], []), "点対面 ICP": ([], [])}
        for _ in range(16):
            a, b, bn, dm = fac(rngf)
            dq, dqn, Rt, tt = make_pair(b, bn, 60.0, 0.15, dm, rngf)
            for name, out in (("点対点 ICP", fs.icp(a, dq, init=(Rt, tt), max_iter=60)),
                              ("点対面 ICP", fs.point_to_plane_icp(
                                  a, dq, dst_normals=dqn, init=(Rt, tt), max_iter=60))):
                rows[name][0].append(rot_error_deg(out[0], Rt))
                rows[name][1].append(cen_error(out[0], out[1], Rt, tt, a.mean(0)) / dm)
        for name, (rr, cc) in rows.items():
            floors[(cname, name)] = (med(rr), np.percentile(rr, 90))
            all_floor_rot += rr
            print(f"  {cname:<18}{name:<12}{med(rr):>16.2f}{np.percentile(rr, 90):>15.2f}"
                  f"{100 * med(cc):>21.3f}%")
    print(f"  → 下限は 1 度 / 直径の 0.3 % 前後。しきい値 {ROT_OK_DEG:.0f} 度 はその外側。")

    # ---- 2. 収束域 ---------------------------------------------------------
    ROTS = (0, 30, 60, 90, 120, 150, 165, 180)
    TRANS = (0.0, 0.10, 0.25, 0.50)
    TRIALS = 15
    print(f"\n=== 2. 収束域 —— 成功率の等高線({TRIALS} 試行/セル、"
          "回転軸と並進方向は毎回ランダム)===")
    basin, edges, all_rot = {}, {}, []
    for label, method in (("点対点 ICP", m_icp), ("点対面 ICP", m_p2pl)):
        print(f"\n  [{label}] 行 = 初期並進ずれ(直径比)、列 = 初期回転ずれ[度]")
        corner = "並進 / 回転"
        print("  " + f"{corner:>12}" + "".join(f"{r:>7}" for r in ROTS))
        grid = np.zeros((len(TRANS), len(ROTS)))
        for i, tf in enumerate(TRANS):
            for j, rd in enumerate(ROTS):
                rate, rr, _cc = run_cell(method, fine, rd, tf, TRIALS,
                                         seed=1000 + 17 * j + 3 * i)
                grid[i, j] = rate
                all_rot.append(rr)
            print("  " + f"{tf * 100:>10.0f} %"
                  + "".join(f"{v * 100:>6.0f}%" for v in grid[i]))
        basin[label] = grid
        row0 = grid[0]
        e = next((ROTS[j] for j in range(len(ROTS)) if row0[j] < 0.5), None)
        edges[label] = e
        print(f"  → 並進ずれ 0 の行で成功率が 50 % を切るのは "
              f"{str(e) + ' 度' if e is not None else '180 度までで切らない'}")
    all_rot = np.concatenate(all_rot)
    band = float(np.mean((all_rot >= ROT_OK_DEG) & (all_rot < 20.0)))
    print(f"\n  境界の読み方: 1 セル {TRIALS} 試行なので成功率の標準誤差は最大 "
          f"{100 * (0.5 / np.sqrt(TRIALS)):.0f} 点。")
    print(f"  {TRIALS} 分の 1 刻みの差は読まない —— 読むのは 100 % から 0 % へ落ちる位置だけ。")
    print(f"  しきい値の妥当性: 上の全 {all_rot.size} 試行のうち回転誤差が 3〜20 度の")
    print(f"  「どちらとも言えない帯」に入るのは {100 * band:.1f} %。当たれば 1 度前後、")
    print("  外せば 20 度以上に割れるので、しきい値をこの帯のどこに置いても表は変わらない。")
    # 等高線は 4x8 の表で、画像にすると小さすぎて読めない。行ごとの折れ線にする。
    _rx = np.array(ROTS, float)
    figs.save_plot("basin",
                   [("初期並進ずれ %.0f %%" % (100 * tf), _rx,
                     100.0 * basin["点対点 ICP"][i])
                    for i, tf in enumerate(TRANS)],
                   xlabel="初期回転ずれ [度]", ylabel="成功率 [%]",
                   title="点対点 ICP の収束域 —— 境界はどこか",
                   caption="100 %% から 0 %% へ落ちる位置が収束域の縁。"
                           "並進ずれを足すと縁が左へ動く(%d 試行/点)。" % TRIALS)

    # ---- 3. ゼロ点 ---------------------------------------------------------
    print("\n=== 3. ゼロ点 —— 何もしない / 重心だけ / PCA だけ ===")
    print("  (初期回転ずれ 0/30/60/90/150 度、並進ずれ 直径の 15 %、各 10 試行の合算)")
    print(f"  {'手法':<20}{'成功率':>8}{'回転誤差 中央値[度]':>24}{'並進誤差 中央値[単位]':>26}")
    zero_rate = {}
    for label, method in (("何もしない", m_null), ("重心合わせのみ", m_centroid),
                          ("PCA 位置合わせのみ", m_pca), ("PCA + ICP", m_pca_icp),
                          ("点対点 ICP", m_icp)):
        rates, rr, cc = [], [], []
        for j, rd in enumerate((0, 30, 60, 90, 150)):
            r, a, b = run_cell(method, fine, rd, 0.15, 10, seed=4242 + j)
            rates.append(r)
            rr.append(a)
            cc.append(b)
        zero_rate[label] = float(np.mean(rates))
        print(f"  {label:<18}{100 * np.mean(rates):>7.0f}%"
              f"{med(np.concatenate(rr)):>22.3f}{med(np.concatenate(cc)):>26.5f}")
    print("  → 「何もしない」は初期ずれそのもの。これを上回らない手法に価値は無い。")
    print("     PCA だけは初期値に依存しないので初期ずれ 150 度でも回転誤差が数度まで")
    print("     落ちる。それでも**しきい値は越えない** —— 初期値としては有用、")
    print("     姿勢推定器としては不合格。理由を次で 2 つに分解する。")

    # ---- 3-b. PCA の象限と軸のぶれ -----------------------------------------
    print("\n=== 3-b. PCA が外す 2 つの理由 —— 象限の取り違え と 主軸のぶれ ===")
    print("  主軸は符号まで決まらないので候補は 8 通り、うち行列式 +1 の 4 通りが姿勢候補。")
    print("  道具は最小 RMSE で 1 つ選ぶ。4 候補すべての誤差と選択結果を数える。")
    print(f"  {'形状':<24}{'第1候補[度]':>13}{'第2〜4候補[度]':>16}"
          f"{'象限誤り':>10}{'選ばれた解[度]':>16}")
    N_Q = 60
    quad_wrong, quad_best, quad_tbl = {}, {}, {}
    for label, bump in (("非対称 強(角柱 1.0)", 1.0),
                        ("非対称 弱(角柱 0.25)", 0.25),
                        ("対称(素の直方体)", 0.0)):
        rq = np.random.default_rng(777)
        best, rest, chosen_all, wrong = [], [], [], 0
        for _ in range(N_Q):
            a = bracket(N_SRC, rq, bump=bump)
            b = bracket(N_DST, rq, bump=bump)
            dq = diameter(b)
            Rt = random_rot(60.0, rq)
            u = rq.normal(size=3)
            dstq = fs.apply_transform(b, Rt, (u / np.linalg.norm(u)) * (0.15 * dq))
            cands = pca_candidates(a, dstq, Rt)
            chosen = rot_error_deg(fs.pca_align(a, dstq)[0], Rt)
            best.append(cands[0])
            rest.append(cands[1])
            chosen_all.append(chosen)
            wrong += int(chosen > cands[0] + 30.0)
        quad_wrong[label] = wrong / N_Q
        quad_best[label] = med(best)
        quad_tbl[label] = (med(best), med(rest), 100 * wrong / N_Q, med(chosen_all))
        print(f"  {label:<22}{med(best):>13.2f}{med(rest):>16.1f}"
              f"{100 * wrong / N_Q:>9.0f}%{med(chosen_all):>16.2f}")
    print("  (象限誤り = 選ばれた解が最良候補より 30 度以上悪い = 反転した象限を掴んだ)")
    figs.save_table("pca_quadrant",
                    ["形状", "第1候補 度", "第2候補 度", "象限誤り %", "選ばれた解 度"],
                    [[k, "%.2f" % v[0], "%.1f" % v[1], "%.0f" % v[2], "%.2f" % v[3]]
                     for k, v in quad_tbl.items()],
                    title="PCA の正しさは形状の非対称性に賭けている",
                    caption="非対称性が消えると 4 候補が形として区別できず、"
                            "選択が崩れる(選ばれた解が第 1 候補から離れる)。",
                    col_w=125)
    print("  → 理由その 1・象限: 角柱があるうちは最小 RMSE が正しい象限を選ぶ。素の")
    print("     直方体では 4 候補が形として区別できず、選択が崩れる。**PCA の正しさは")
    print("     形状の非対称性に賭けている**。")
    print("  → 理由その 2・軸のぶれ: **正しい象限を選んでも第 1 候補が数度ずれている**。")
    print("     主軸は有限標本からの推定なので揺れる。点数を変えて確かめる:")
    print(f"  {'点数':>8}{'第1候補の回転誤差 中央値[度]':>30}{'1/sqrt(N) からの予測':>24}")
    ref, scale = None, {}
    for npts in (200, 800, 3200):
        rq = np.random.default_rng(555)
        errs = []
        for _ in range(24):
            a = bracket(npts, rq)
            b = bracket(int(npts * 1.4), rq)
            Rt = random_rot(60.0, rq)
            errs.append(pca_candidates(a, fs.apply_transform(b, Rt, np.zeros(3)), Rt)[0])
        m = med(errs)
        ref = ref if ref is not None else (m, npts)
        scale[npts] = m
        print(f"  {npts:>8}{m:>30.2f}{ref[0] * np.sqrt(ref[1] / npts):>24.2f}")
    print("     → 点数を 16 倍にすると誤差はおよそ 4 分の 1。主軸推定の統計的ゆらぎで")
    print("        あって実装の誤りではない。この床は ICP では消えるが PCA には残る。")
    print("        **PCA は初期値専用。単体では姿勢推定器にならない**。")

    # ---- 4. 収束域の広さ と 最終精度 --------------------------------------
    TR4 = 12
    print("\n=== 4. 収束域の広さ と 最終精度 は別の軸(同じ点群・同じしきい値で 5 手法)===")
    print(f"  点数を落とした共通の組 src {N_CSRC} / dst {N_CDST}"
          f"(FPFH と PPF が現実的な時間で回る密度。下限は第 1 章の「粗」の行)")
    WIDE = (0, 45, 90, 135, 180)
    print("  行 = 手法、列 = 初期回転ずれ[度]。並進ずれ 直径の 15 % 固定、"
          f"{TR4} 試行/セル")
    print("  " + f"{'手法':<20}" + "".join(f"{r:>7}" for r in WIDE)
          + f"{'成功時の回転誤差[度]':>24}{'成功時の並進[直径比]':>24}")
    width = {}
    for label, method in (("点対点 ICP", m_icp), ("点対面 ICP", m_p2pl),
                          ("PCA + ICP", m_pca_icp), ("FPFH + RANSAC", m_feature),
                          ("PPF surface_match", m_ppf)):
        rates, fr, fc = [], [], []
        for j, rd in enumerate(WIDE):
            r, a, b = run_cell(method, coarse, rd, 0.15, TR4, seed=5000 + 31 * j)
            rates.append(r)
            keep = a < ROT_OK_DEG
            fr.append(a[keep])
            fc.append(b[keep])
        width[label] = np.array(rates)
        print("  " + f"{label:<18}" + "".join(f"{v * 100:>6.0f}%" for v in rates)
              + f"{med(np.concatenate(fr)):>24.3f}"
              + f"{100 * med(np.concatenate(fc)) / diam0:>23.3f}%")
    print("  → 左から右へ落ちる手法は「狭い」、平らな手法は「広い」。広さと右 2 列の")
    print("     精度は連動していない。**「良い手法」は 1 つの数では決まらない**。")
    figs.save_plot("width",
                   [(k, np.array(WIDE, float), 100.0 * v) for k, v in width.items()],
                   xlabel="初期回転ずれ [度]", ylabel="成功率 [%]",
                   title="収束域の広さ —— 落ちる手法と、平らな手法",
                   caption="平らな線ほど「広い」。広さと最終精度は別の軸で、"
                           "この図だけでは手法を選べない(%d 試行/点)。" % TR4)
    _pr = width["PPF surface_match"]
    _fr = width["FPFH + RANSAC"]
    print("  → FPFH と PPF は回転不変な記述子に基づくので、行は**平らでなければならない**")
    print(f"     (初期回転ずれで成績が変わってはいけない)。PPF の行は {100 * _pr.min():.0f}〜"
          f"{100 * _pr.max():.0f} %。")
    print("     ★2026-11-09 まで find_surface_pose の既定は**場面側だけ**符号任意の")
    print("     estimate_normals を使い、モデル側(向き付き法線)と鍵が半分ずれていた")
    print("     (135 度のセルが 67 %)。場面側も estimate_oriented_normals にそろえて直した。")
    print("     さらに向き付けの符号は「場面の重心から外向き」に決まり、床や他物体を含む場面では")
    print("     物体ごと裏返ることがあるので、既定の法線では両方の符号で投票して当てはまりの")
    print("     良い方を取る(独立レビューの指摘で追加。この表では 0 度と 90 度のセルが上がった)。")
    print(f"     FPFH の行は {100 * _fr.min():.0f}〜{100 * _fr.max():.0f} % で、回転ではなく"
          "対応の質で決まっている")
    print("     (RANSAC の試行回数不足でもない: 800/4000/12000 回で同じ誤答に収束した)。")
    print("     記述子が本当に回転不変かは 5-d で切り分ける。")

    # ---- 5-a. 重なり率 -----------------------------------------------------
    TR5 = 10
    print(f"\n=== 5-a. 重なり率を下げる(部分ビュー。初期ずれ 30 度 / 直径の 10 %、"
          f"{TR5} 試行/セル)===")
    print(f"  {'重なり':>8}{'点対点 ICP':>12}{'PCA + ICP':>12}{'ICP trim=0.4':>16}"
          f"{'FPFH+RANSAC':>14}{'PPF':>8}")
    OVER = (1.0, 0.9, 0.75, 0.6, 0.5)
    over = {}
    for frac in OVER:
        row = []
        for method in (m_icp, m_pca_icp, m_trim, m_feature, m_ppf):
            r, _a, _b = run_cell(method, coarse, 30.0, 0.10, TR5, seed=9001,
                                 crop=frac)
            row.append(r)
        over[frac] = row
        print(f"  {100 * frac:>7.0f}%{row[0] * 100:>11.0f}%{row[1] * 100:>11.0f}%"
              f"{row[2] * 100:>15.0f}%{row[3] * 100:>13.0f}%{row[4] * 100:>7.0f}%")
    print("  → 重なりが下がると部分ビューの主軸が全体の主軸とずれるので、PCA 初期値は")
    print("     先に壊れる。切り捨て(trim)は残差の外れ値を捨てるが、初期値が別の象限")
    print("     なら救えない —— **頑健化は初期値の間違いを直さない**。")

    # ---- 5-b. 雑音 ---------------------------------------------------------
    print("\n=== 5-b. 雑音を乗せる(精度の軸。成功率でなく誤差の中央値で見る)===")
    print(f"  {'雑音 σ(直径比)':>16}{'点対点 回転[度]':>18}{'点対点 並進[直径比]':>22}"
          f"{'点対面 回転[度]':>18}{'点対面 並進[直径比]':>22}")
    noise_tbl = {}
    for sig in (0.0, 0.002, 0.01, 0.03):
        res = {}
        for name, method in (("p2p", m_icp), ("p2pl", m_p2pl)):
            rng_n = np.random.default_rng(3131)
            rr, cc = [], []
            for _ in range(10):
                a, b, bn, dm = fine(rng_n)
                dstc, dnc, Rt, tt = make_pair(b, bn, 15.0, 0.05, dm, rng_n)
                if sig > 0:
                    dstc = dstc + rng_n.normal(scale=sig * dm, size=dstc.shape)
                    dnc = fs.estimate_normals(dstc, k=16)
                R, t = method(a, dstc, dnc)
                rr.append(rot_error_deg(R, Rt))
                cc.append(cen_error(R, t, Rt, tt, a.mean(0)) / dm)
            res[name] = (med(rr), med(cc))
        noise_tbl[sig] = res
        print(f"  {sig * 100:>15.1f}%{res['p2p'][0]:>18.3f}{100 * res['p2p'][1]:>21.3f}%"
              f"{res['p2pl'][0]:>18.3f}{100 * res['p2pl'][1]:>21.3f}%")
    print("  → 点対面は無雑音では 3 倍精密だが、雑音が乗ると法線推定そのものが崩れて")
    print("     優位が消える。**手法の優劣は測定条件つきでしか言えない**。")

    # ---- 5-c. 対称形状 -----------------------------------------------------
    print("\n=== 5-c. 対称形状 —— 「収束したのに間違っている」 ===")
    print("  見かけ上収束 = 最終残差 rmse が dst の点間隔の 2 倍未満(実務ではここで OK を出す)")
    print(f"  姿勢が誤り = 回転誤差 > {LIE_DEG:.0f} 度(しきい値すれすれの数度は精度の話であって")
    print("  嘘ではないので、明らかに別の姿勢を掴んだ場合だけを数える)")
    SHAPES = (("非対称当て金", bracket), ("素の直方体", plain_box),
              ("球", sphere), ("円柱", cylinder))
    N_S = 16
    sym, sym_stat = {}, {}
    for mode, init_deg, use_global in (("局所: ICP を恒等から", 25.0, False),
                                       ("大域: PCA + ICP", 120.0, True)):
        print(f"\n  [{mode}、初期ずれ {init_deg:.0f} 度 / 直径の 5 %、{N_S} 試行]")
        print(f"  {'形状':<14}{'残差 rmse/直径':>16}{'回転誤差 中央値[度]':>22}"
              f"{'見かけ上収束':>14}{'うち姿勢が誤り':>18}")
        for label, gen in SHAPES:
            rng_s = np.random.default_rng(24680)
            rr, res, conv, bad = [], [], 0, 0
            for _ in range(N_S):
                a, b, bn, dm = clouds(rng_s, shape=gen)
                dstc, _dnc, Rt, tt = make_pair(b, bn, init_deg, 0.05, dm, rng_s)
                init = fs.pca_align(a, dstc) if use_global else None
                R, _t, _aln, rmse = fs.icp(a, dstc, init=init, max_iter=60)
                rd = rot_error_deg(R, Rt)
                rr.append(rd)
                res.append(rmse / dm)
                if rmse < 2.0 * spacing_of(dstc):
                    conv += 1
                    bad += int(rd > LIE_DEG)
            sym[(mode, label)] = (conv, bad)
            sym_stat[(mode, label)] = (med(res), med(rr))       # 図用
            print(f"  {label:<12}{med(res):>16.5f}{med(rr):>22.2f}"
                  f"{conv:>13}/{N_S}{bad:>17}")
    figs.save_table("symmetry_lies",
                    ["初期化", "形状", "残差/直径", "回転誤差 度", "見かけ収束",
                     "姿勢が誤り"],
                    [[mode.split(":")[0], label,
                      "%.5f" % sym_stat[(mode, label)][0],
                      "%.2f" % sym_stat[(mode, label)][1],
                      "%d/%d" % (v[0], N_S), "%d" % v[1]]
                     for (mode, label), v in sym.items()],
                    title="収束したのに間違っている(残差では検出できない)",
                    caption="球・円柱は残差が小さいまま姿勢が任意。素の直方体は"
                            "局所なら嘘をつかず、大域に替えた瞬間に嘘をつく。",
                    col_w=118)
    print("\n  → 局所 ICP は初期ずれが小さければ対称形状でも**近い**解に落ちるので嘘が")
    print("     出にくい(素の直方体の他の 3 姿勢は 180 度先にあり、盆地の外)。大域手法に")
    print("     替えたとたん、残差が同じまま別の姿勢を返す。**残差を成功判定に使うと")
    print("     この嘘は原理的に検出できない** —— 真値か、形状の対称群を知る必要がある。")
    rng_c = np.random.default_rng(1357)
    axis_err, full_err = [], []
    for _ in range(16):
        a, b, bn, dm = clouds(rng_c, shape=cylinder)
        dstc, _dn, Rt, tt = make_pair(b, bn, 25.0, 0.05, dm, rng_c)
        R = fs.icp(a, dstc, max_iter=60)[0]
        z = np.array([0.0, 0.0, 1.0])
        axis_err.append(np.degrees(np.arccos(np.clip(abs((R @ z) @ (Rt @ z)), -1.0, 1.0))))
        full_err.append(rot_error_deg(R, Rt))
    print(f"  円柱の内訳: 軸の向きの誤差 中央値 {med(axis_err):.2f} 度 に対し、"
          f"回転全体の誤差 中央値 {med(full_err):.2f} 度")
    print("     = 決まる自由度と決まらない自由度が同居している。1 つの数にまとめると消える。")

    # ---- 5-d. 回転不変のはずの記述子が回転で変わる --------------------------
    print("\n=== 5-d. ★ 回転不変のはずの記述子が回転で変わる(第 4 章の行が平らであるべき理由)===")
    rngd = np.random.default_rng(7)
    a_d = bracket(N_CSRC, rngd)
    R_d = rot_axis_angle((0.3, -0.7, 0.65), 90.0)
    b_d = fs.apply_transform(a_d, R_d, np.array([0.3, -0.2, 0.1]))   # 同じ点を剛体移動しただけ

    def outward(P, k=12):
        """重心から外向きに符号を揃えた法線 —— 星形の物体なら回転に対して同変。"""
        n = fs.estimate_normals(P, k=k)
        n[np.einsum("ni,ni->n", n, P - P.mean(0)) < 0] *= -1.0
        return n

    def inv_step(P):
        """回転不変な距離刻み(重心からの最大半径から作る)。"""
        return 2.0 * float(np.max(np.linalg.norm(P - P.mean(0), axis=1))) / 20.0

    n_a, n_b = fs.estimate_normals(a_d, k=12), fs.estimate_normals(b_d, k=12)
    flip_signed = float(np.mean(np.linalg.norm(n_b - n_a @ R_d.T, axis=1) > 1e-6))
    flip_unsigned = float(np.mean(np.minimum(
        np.linalg.norm(n_b - n_a @ R_d.T, axis=1),
        np.linalg.norm(n_b + n_a @ R_d.T, axis=1)) > 1e-6))
    print("  同一の点群を 90 度回しただけの 2 つを比べる(答えは完全に一致すべき)。")
    print(f"  estimate_normals: 向きまで一致しない点 {100 * flip_signed:.0f} % / "
          f"符号を無視すれば {100 * flip_unsigned:.0f} %")
    print("    → 法線そのものは正しい。**符号が任意で、しかも回転すると別の符号を選ぶ**。")
    d_default = float(np.max(np.abs(fs.fpfh(b_d, k=12) - fs.fpfh(a_d, k=12))))
    d_fixed = float(np.max(np.abs(fs.fpfh(b_d, normals=outward(a_d) @ R_d.T, k=12)
                                  - fs.fpfh(a_d, normals=outward(a_d), k=12))))
    # ★利用者が「法線なら在るじゃないか」と `estimate_normals` を明示的に渡した場合。
    #   ここが穴の**残り**で、既定より 14 桁悪い。
    d_user = float(np.max(np.abs(fs.fpfh(b_d, normals=n_b, k=12)
                                 - fs.fpfh(a_d, normals=n_a, k=12))))
    print(f"  fpfh の記述子の差 max|Δ|: 既定(道具任せ){d_default:.3e} / "
          f"向きを揃えて渡す {d_fixed:.3e} / "
          f"estimate_normals を渡す {d_user:.3e}")
    print("    → ★2026-09-06 に**塞がった**。以前はここが 1e+03 台で、この PoC は")
    print("       『docstring は rotation-invariant と書いてあるが不変でない』と記録した。")
    print("       いまは fpfh が自前の estimate_point_normals を使い、**重心から外向きに**")
    print("       符号を揃えてから角を作るので、既定のまま厳密に不変になっている。")
    print("    → 残っている穴は 2 つ。(i) ファサードの estimate_normals は**いまも**")
    print(f"       符号が回転で変わる({100 * flip_signed:.0f} % の点)。(ii) それを")
    print(f"       fpfh に**明示的に渡すと不変性が丸ごと壊れる**(max|Δ| {d_user:.3e})。")
    print("       つまり「引数を使わないほうが正しい」という、道具として危ない形が残る。")
    ka = set(fs.ppf_model(a_d, normals=outward(a_d), angle_bins=24)["table"])
    kb = set(fs.ppf_model(b_d, normals=outward(a_d) @ R_d.T, angle_bins=24)["table"])
    st = inv_step(a_d)
    ka2 = set(fs.ppf_model(a_d, normals=outward(a_d), angle_bins=24, dist_step=st)["table"])
    kb2 = set(fs.ppf_model(b_d, normals=outward(a_d) @ R_d.T, angle_bins=24,
                           dist_step=st)["table"])
    print(f"  ppf_model のハッシュ鍵の一致率: 既定の dist_step {100 * len(ka & kb) / len(ka):.0f} % / "
          f"回転不変な dist_step を渡すと {100 * len(ka2 & kb2) / len(ka2):.0f} %")
    print("    → ★2026-09-06 に**塞がった**。以前の既定は**軸平行境界箱の対角/20** で、")
    print(f"       同じ物体でも向きで対角が {diameter(a_d):.3f} → {diameter(b_d):.3f} と変わり、")
    print("       距離の量子化がずれて鍵の一致率が 58 % まで落ちていた。いまは既定が")
    print("       **凸包の頂点どうしの最大距離**(真の直径 = 回転不変)なので、")
    print("       軸平行の対角が上のように動いても鍵は完全一致する。")
    print("       ※ 軸平行の対角そのものは今も向きで変わる —— 直ったのは「何を")
    print("          直径と呼ぶか」であって、境界箱の性質ではない。")
    TR_D = 14
    print(f"  端から端まで(find_surface_pose、{TR_D} 試行/セル):")
    print(f"  {'初期回転ずれ':>12}{'既定':>10}{'向き揃え + 不変 step':>24}")
    ppf_fix = {}
    for deg in (0.0, 180.0):
        row = []
        for fixed in (False, True):
            rr = np.random.default_rng(4321)
            n_ok = 0
            for _ in range(TR_D):
                a, b, bn, dm = coarse(rr)
                dq, _dn, Rt, tt = make_pair(b, bn, deg, 0.15, dm, rr)
                if fixed:
                    o = fs.find_surface_pose(a, dq, model_normals=outward(a),
                                             scene_normals=outward(dq), dist_step=inv_step(a),
                                             angle_bins=24, ref_fraction=0.25, topk=3)
                else:
                    o = fs.find_surface_pose(a, dq, angle_bins=24, ref_fraction=0.25, topk=3)
                n_ok += int(ok(rot_error_deg(o["R"], Rt),
                               cen_error(o["R"], o["t"], Rt, tt, a.mean(0)), dm))
            row.append(n_ok / TR_D)
        ppf_fix[deg] = row
        print(f"  {deg:>11.0f}度{row[0] * 100:>9.0f}%{row[1] * 100:>23.0f}%")
    print(f"  → 記述子の一致は厳密な数値で言えるが、端から端までの成功率は {TR_D} 試行では")
    print("     ばらつきが大きい。**結論の根拠は上の max|Δ| と鍵一致率の方**に置く。")

    # ---- 6. 速度 -----------------------------------------------------------
    print("\n=== 6. 速度(この機械での実測)===")
    rngv = np.random.default_rng(31415)
    sv, bv, nv, _dv = fine(rngv)
    sc, bc, nc, _dc = coarse(rngv)
    dst_v = fs.apply_transform(bv, rot_axis_angle((1, 1, 0), 25.0), np.array([0.1, 0.0, 0.05]))
    dn_v = fs.estimate_normals(dst_v, k=16)
    dst_ct = fs.apply_transform(bc, rot_axis_angle((1, 1, 0), 25.0), np.array([0.1, 0.0, 0.05]))
    fine_n = f"{sv.shape[0]} -> {bv.shape[0]}"
    coarse_n = f"{sc.shape[0]} -> {dst_ct.shape[0]}"
    print(f"  {'手法':<28}{'時間 [ms]':>11}   点数")
    for label, fn, note in (
            ("kabsch(対応点既知)", lambda: fs.kabsch(sv, fs.apply_transform(sv, R_true, t_true)),
             f"{sv.shape[0]}"),
            ("pca_align", lambda: fs.pca_align(sv, dst_v), fine_n),
            ("icp", lambda: fs.icp(sv, dst_v, max_iter=60), fine_n),
            ("point_to_plane_icp", lambda: fs.point_to_plane_icp(
                sv, dst_v, dst_normals=dn_v, max_iter=60), fine_n),
            ("estimate_normals(k=16)", lambda: fs.estimate_normals(dst_v, k=16), f"{bv.shape[0]}"),
            ("register(init='pca')", lambda: fs.register(sv, dst_v, init="pca"), fine_n),
            ("register(init='auto')", lambda: fs.register(sv, dst_v, init="auto"), fine_n),
            ("feature_register(800 回)", lambda: fs.feature_register(sc, dst_ct, ransac_iter=800),
             coarse_n),
            ("ppf_model", lambda: fs.ppf_model(sc, angle_bins=24), f"{sc.shape[0]}"),
            ("find_surface_pose", lambda: fs.find_surface_pose(
                sc, dst_ct, angle_bins=24, ref_fraction=0.25, topk=3), coarse_n),
            ("voxel_downsample(0.05)", lambda: fs.voxel_downsample(dst_v, 0.05), f"{bv.shape[0]}"),
            ("farthest_point_sampling(250)", lambda: fs.farthest_point_sampling(sv, 250),
             f"{sv.shape[0]}"),
    ):
        t0 = time.perf_counter()
        fn()
        print(f"  {label:<28}{1e3 * (time.perf_counter() - t0):>11.2f}   {note}")
    print("  → 大域手法は局所手法の 20-100 倍。**収束域は時間で買っている**。")
    print("     点対面が点対点より速いのは反復回数が少なくて済むため(1 反復は重い)。")

    # ---- 道具の穴 ----------------------------------------------------------
    print("\n=== ★ この PoC が出した道具の穴(op 本体は直していない)===")
    print("  1. **(塞がった / 2026-09-06)fpfh の既定経路は回転不変になった**(5-d)。")
    print(f"     いまは max|Δ| {d_default:.2e}。以前はここが 1e+03 台で、原因は数式ではなく")
    print("     法線の符号だった。直り方は「fpfh が自前の estimate_point_normals を使い、")
    print("     **重心から外向きに**符号を揃えてから角を作る」—— この PoC が書いた回避策")
    print("     そのものが実装に入った形。")
    print(f"     ★ただし残りがある: ファサードの estimate_normals はいまも {100 * flip_signed:.0f} % の点で")
    print(f"     符号が回転で変わり、それを fpfh に**明示的に渡すと max|Δ| {d_user:.2e} に")
    print("     壊れる**。「引数を使わないほうが正しい」形が残っているのが現在の穴。")
    print("  2. **(塞がった / 2026-09-06)ppf_model の既定 dist_step は回転不変になった**")
    print(f"     (5-d)。ハッシュ鍵の一致率は {100 * len(ka & kb) / len(ka):.0f} %。以前の既定は軸平行境界箱の")
    print("     対角/20 で、同じ物体でも向きで変わるため一致率が 58 % まで落ちていた。")
    print("     いまは凸包の頂点どうしの最大距離(= 真の直径)を使う。モデルは 1 度作って")
    print("     多数の場面に使い回す設計なので、ここが向き依存だと「別の向きで撮った")
    print("     場面だけ当たらない」という再現しにくい壊れ方になっていた。")
    print("  3. 向きの揃った法線を作る op は repo にある(normals_orient.orient_normals /")
    print("     estimate_oriented_normals、実測で回転同変)。fpfh と ppf_model は内部で")
    print("     それを使い、2026-11-09 からは surface_match の場面側(scene_normals=None)も")
    print("     同じ関数を使う(以前は場面側だけ符号任意で、当て金 48 試行の PPF 成功率が 54 %。いまの既定")
    print("     = 両符号の投票で 79 %(同じ種 7。種 1〜7 では 75〜94 %、片符号で向きを渡すと平均 0.84 対 0.83、")
    print("     時間は約 2 倍)。片側だけ見えた物体 + 床では、既定でも視点で向けた法線でも成功はほぼ 0)。")
    print("     既定の法線のときは両方の符号で投票する(場面全体の符号が裏返っても外れない)。")
    print("     だが **fullseye ファサードには出ていない** —— 利用者が自分で法線を渡すと")
    print("     素の estimate_normals になりやすい(渡した法線は渡した符号だけで投票する)。")
    print("  4. feature_register は失敗を沈黙する。返り値に対応の質を示す指標が無い")
    print("     (inlier 数も 2 位との差も返らない)ので、呼び出し側は「試行回数が足りない」")
    print("     のか「原理的に無理」なのかを区別できない。実際 800/4000/12000 回で同じ")
    print("     誤答に収束したが、それは呼び出し側から見えない。")
    print("  5. point_to_plane_icp の rmse は**点対面残差**で、icp の点対点 rmse と単位も")
    print("     意味も違う。同じしきい値で比べると点対面が常に良く見える(接平面内の滑りが")
    print("     残差に出ない)。返り値の位置も型も同じなので取り違えても例外にならない。")
    print("  6. pca_align は最小 RMSE で象限を選ぶが、その RMSE は対称形状ではどの象限でも")
    print("     ほぼ同じになる。選択が実質くじ引きでも、道具はそれを呼び出し側に伝えない")
    print(f"     (信頼度も候補どうしの差も返らない)。3-b の素の直方体 "
          f"{100 * quad_wrong['対称(素の直方体)']:.0f} % はここで生まれる。")
    print("  7. surface_match(refine=False) は rmse に nan を返す。型は float のままなので")
    print("     数値比較すると常に False になり、静かに「最良候補なし」に落ちる。")
    print("  8. icp / point_to_plane_icp は収束したかを返さない。tol で止まったのか")
    print("     max_iter で打ち切られたのかが外から分からず、反復予算の設計ができない。")
    print("  9. register(init='auto') は毎回 FPFH 初期値を計算するので PCA 経路の 20-50 倍")
    print("     遅い。掃引のような繰り返し用途では init を明示しないと予算が読めない。")

    # ---- 自己検査(速さは assert しない)-----------------------------------
    # (a) 対応点が既知なら閉形式は厳密(arccos は 0 度付近で平方根ぶん精度を失う)
    assert rot_error_deg(Rk, R_true) < 1e-4, "kabsch が対応点既知で厳密でない"
    assert cen_error(Rk, tk, R_true, t_true, src0.mean(0)) < 1e-12
    assert np.allclose(fs.apply_transform(src0, np.eye(3), np.zeros(3)), src0)
    # (b) 下限がしきい値の内側 = 以下の「失敗」が精度不足でないことの保証
    for key, (m50, m90) in floors.items():
        assert m90 < ROT_OK_DEG, f"{key}: 下限の 90 %tile がしきい値を超えた ({m90:.2f} 度)"
    # (c) しきい値は空白地帯に置かれている(判定が恣意的でない)
    assert band < 0.05, f"3〜20 度の帯に {100 * band:.1f} % もある = しきい値が結論を左右する"
    # (d) 収束域が存在する = 小さい初期ずれで当たり、180 度で落ちる
    for label in ("点対点 ICP", "点対面 ICP"):
        g = basin[label]
        assert g[0, 0] >= 0.99, f"{label}: 初期ずれ 0 で失敗している ({g[0, 0]})"
        assert g[0, ROTS.index(30)] > g[0, ROTS.index(180)], f"{label}: 境界が出ていない"
        assert g.min() < 0.5, f"{label}: どのセルでも落ちない(判定が緩すぎる)"
        assert edges[label] is not None, f"{label}: 境界が 180 度までに現れない"
    # (e) ゼロ点を上回っていること
    assert zero_rate["何もしない"] == 0.0, "『何もしない』が成功した(判定が緩すぎる)"
    assert zero_rate["PCA 位置合わせのみ"] < 0.2, "PCA 単体が姿勢推定器として通ってしまった"
    assert zero_rate["PCA + ICP"] > zero_rate["点対点 ICP"], \
        "PCA 初期値が素の ICP を上回らない(大域初期値の意味が無い)"
    # (f) PCA の象限: 非対称が強ければ当たり、対称なら外れる
    assert quad_wrong["非対称 強(角柱 1.0)"] <= 0.05, "強い非対称で象限を外した"
    assert quad_wrong["対称(素の直方体)"] >= 0.25, "対称形状で象限誤りが出ていない"
    assert quad_best["非対称 強(角柱 1.0)"] > 1.0, "PCA の軸ぶれが出ていない"
    # 軸のぶれは点数で減る(統計的ゆらぎ。実装の誤りなら点数を増やしても残る)
    assert scale[3200] < 0.6 * scale[800] < 0.6 * scale[200], \
        f"PCA の軸ぶれが点数で減らない {scale}"
    # (g) 重なり低下で PCA 初期値は劣化する
    assert over[1.0][1] > over[0.5][1], "重なり低下で PCA+ICP が劣化しない"
    # (h) 大域手法は狭い局所手法より広い(第 4 章の右端)
    assert width["PCA + ICP"][-1] > width["点対点 ICP"][-1], \
        "180 度で大域手法が局所手法を上回らない"
    # (i) 対称形状で「収束したのに間違っている」が実際に出る
    for mode in ("局所: ICP を恒等から", "大域: PCA + ICP"):
        conv_s, bad_s = sym[(mode, "球")]
        assert conv_s >= N_S // 2, f"{mode}: 球で収束すらしていない (conv={conv_s})"
        assert bad_s >= conv_s // 2, f"{mode}: 球で偽の成功が出ていない ({bad_s}/{conv_s})"
        assert sym[(mode, "非対称当て金")][1] == 0, f"{mode}: 非対称形状で偽の成功が出た"
    # 素の直方体は局所なら嘘をつかず、大域に替えると嘘をつく(嘘の原因は形だけではない)
    assert sym[("局所: ICP を恒等から", "素の直方体")][1] == 0, "局所 ICP が直方体で嘘をついた"
    assert sym[("大域: PCA + ICP", "素の直方体")][1] > 0, "大域手法が直方体で嘘をつかない"
    # (j) 円柱は軸だけ決まる = 自由度ごとに結論が違う
    assert med(axis_err) < 5.0 < med(full_err), "円柱の軸と全体の分離が出ていない"
    # (k) 雑音が増えれば精度は落ちる
    assert noise_tbl[0.03]["p2p"][0] > noise_tbl[0.0]["p2p"][0], "雑音で誤差が増えない"
    assert noise_tbl[0.0]["p2pl"][0] < noise_tbl[0.0]["p2p"][0], "無雑音で点対面が優位でない"
    # (l) 5-d の 2 つの穴が実在する(ここが直れば assert が落ちる = 直った合図になる)
    assert flip_unsigned < 1e-9, "法線が符号を無視しても一致しない(別の問題がある)"
    assert flip_signed > 0.1, "法線の符号が回転で変わらない(穴が塞がった?)"
    # ★2026-09-06 に穴 1 が塞がった。この assert は**塞がった状態を固定する**
    #   側へ書き換えてある(以前は `d_fixed < 1e-6 < d_default` = 壊れている
    #   ことを固定していた)。壊れ方が戻ってきたらここが落ちる。
    assert d_default < 1e-9, \
        f"fpfh が既定の法線で回転不変でなくなった(max|Δ| {d_default:.2e})"
    assert d_fixed < 1e-9, f"向きを揃えても不変でない({d_fixed:.2e})"
    # 残った穴: 利用者が estimate_normals を明示的に渡すと丸ごと壊れる。
    # これが直ったら(= 1e-9 を下回ったら)ここが落ちるので、所見を書き換えること。
    assert d_user > 1.0, \
        f"estimate_normals を渡しても不変になった(穴が塞がった? {d_user:.2e})"
    assert len(ka2 & kb2) == len(ka2) == len(kb2), "dist_step を固定しても鍵が一致しない"
    # ★2026-09-06 に穴 2 が塞がった。以前は `< 0.9 * len(ka)`(壊れていることを
    #   固定)だった。いまは**既定のままで完全一致する**ことを固定する。
    assert len(ka & kb) == len(ka) == len(kb),         "既定 dist_step が回転不変でなくなった(鍵の一致率 %.0f %%)" % (
            100 * len(ka & kb) / len(ka))
    # (m) surface_match(refine=False) の rmse は nan(型は float のまま静かに比較を裏切る)
    nan_out = fs.surface_match(fs.ppf_model(a_d[:120], angle_bins=24), a_d[:150],
                               refine=False, ref_fraction=0.25, topk=3)
    assert isinstance(nan_out["rmse"], float) and np.isnan(nan_out["rmse"]), \
        "surface_match(refine=False) の rmse が nan でない(穴が塞がった?)"
    assert (nan_out["rmse"] < 1.0) is False, "nan の比較が False にならない"

    video_icp_basin()
    real_scan_chapter({"p2p": float(edges["点対点 ICP"] or 180.0), "p2pl": float(edges["点対面 ICP"] or 180.0)})

    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print(f"\n  (所要 {time.perf_counter() - t_start:.1f} 秒)")
    print("\nPASS")


if __name__ == "__main__":
    main()
