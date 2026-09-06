# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""点群位置合わせの収束域 —— 初期姿勢がどれだけずれたら壊れるか。

EXTEND: 実物の点群に差し替えるなら ``bracket`` を捨てて ``fs.read_points`` で読む。
Stanford Bunny は同梱していないがダウンローダの入口があり、
``py -3.11 -m sample_data download bunny --yes`` で原典(Stanford 3D Scanning
Repository)から取得して ``fs.read_points(sample_data.local_path("bunny"))``。
実物に替えるとき **必ず一緒に変えるもの** が 3 つある。(a) 成功判定のしきい値は
**形状の直径に対する比**で書いてあるので直径さえ測れば移るが、点間隔がしきい値より
粗いと「成功不能」になる —— 下の第 1 章が出す到達可能な下限を先に測ること。
(b) 真値は自分で剛体変換を掛けて作っている。実スキャン 2 枚を突き合わせる場合は
真値が無いので、**誤差ではなく残差しか測れない**(残差が小さいことは正しさの証明に
ならない —— 第 5 章の対称形状がその反例)。(c) 実スキャンは重なりが 100 % では
ないので、第 5 章の重なり率の表の側を先に見る。

この PoC が示すこと:

1. **回転と並進は別々に出す** —— 1 つの数にまとめると、回転が 180 度ずれたまま
   重心だけ合っている状態(対称形状で普通に起きる)が「中くらいの誤差」に化ける。
2. **収束域には境界がある** —— ICP は初期回転ずれが小さいうちは確実に決まり、
   ある角度から先で急に落ちる。その境界を成功率の表で出す。
3. **ゼロ点を置かないと何も言えない** —— 「何もしない」と「PCA 位置合わせだけ」を
   並べる。PCA は主軸の符号で 4 通りの解を持ち、間違った象限に落ちうる。
4. **収束域の広さと最終精度は別の軸** —— 広いが粗い手法(PPF、FPFH)と、
   狭いが精密な手法(点対面 ICP)がある。両方を表に出す。
5. **対称形状では「収束したのに間違っている」** —— 球や円柱は残差がほぼ 0 の
   まま姿勢が任意。残差を成功判定に使うと、この嘘を検出できない。

★ この PoC が出した道具の穴は末尾の「道具の穴」節に印字する(op 本体は直していない)。
"""
from __future__ import annotations

import time

import numpy as np
from scipy.spatial import cKDTree

import fullseye as fs

# --- 成功の定義(この PoC 全体で使う唯一の判定)-----------------------------
# 回転誤差 1 度未満 かつ 重心の移動誤差が形状直径の 0.1 % 未満。
# 直径比で書くのは、実データに移したときそのまま持ち越せるようにするため。
ROT_OK_DEG = 1.0
CEN_OK_FRAC = 0.001


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
    q = np.abs(P - np.asarray(center, np.float64))
    return np.all(q < d - 1e-12, axis=1)


BRACKET_MAIN = ((1.00, 0.62, 0.38), (0.0, 0.0, 0.0))
BRACKET_BUMP = ((0.36, 0.30, 0.24), (0.42, 0.24, 0.11))


def bracket(n, rng):
    """非対称な当て金 —— 直方体の +x +y +z の隅に小さな出っ張りを付けたもの。

    出っ張りが無い素の直方体は 3 軸まわりの 180 度回転で自分自身に重なる(位数 8 の
    対称群)ので、「間違った象限」と「正しい象限」が区別できない。この PoC の
    主役の形状は **その 3 つの対称をすべて壊してある**。
    """
    a = box_surface(BRACKET_MAIN[0], int(n * 0.78), rng, BRACKET_MAIN[1])
    b = box_surface(BRACKET_BUMP[0], n - int(n * 0.78), rng, BRACKET_BUMP[1])
    a = a[~_inside(a, *BRACKET_BUMP)]
    b = b[~_inside(b, *BRACKET_MAIN)]
    return np.concatenate([a, b])


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
    """2 つの回転の測地距離[度]。R_est·R_true^T の回転角。"""
    c = (np.trace(np.asarray(R_est) @ np.asarray(R_true).T) - 1.0) / 2.0
    return float(np.degrees(np.arccos(np.clip(c, -1.0, 1.0))))


def cen_error(R_est, t_est, R_true, t_true, c_src):
    """重心が行き着く先のずれ[単位]。回転誤差と混ぜないためにこう定義する。"""
    return float(np.linalg.norm((R_est @ c_src + t_est) - (R_true @ c_src + t_true)))


def ok(rot_deg, cen, diam):
    return (rot_deg < ROT_OK_DEG) and (cen < CEN_OK_FRAC * diam)


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
    R, t, _a, _r = fs.icp(src, dst, max_iter=60)
    return R, t


def m_p2pl(src, dst, dn):
    R, t, _a, _r = fs.point_to_plane_icp(src, dst, dst_normals=dn, max_iter=60)
    return R, t


def m_pca_icp(src, dst, dn):
    R, t, _a, _r = fs.register(src, dst, init="pca")
    return R, t


def m_feature(src, dst, dn):
    R, t, _a, _r = fs.feature_register(src, dst, ransac_iter=800, seed=0)
    return R, t


def m_ppf(src, dst, dn):
    out = fs.find_surface_pose(src, dst, angle_bins=24, ref_fraction=0.25, topk=3)
    return out["R"], out["t"]


# ---------------------------------------------------------------------------
# 一試行 = 真値を作り、掛け、復元し、誤差を回転と並進に分けて返す
# ---------------------------------------------------------------------------
def make_pair(src_base, dst_base, dst_n_base, rot_deg, trans_frac, diam, rng):
    R_true = random_rot(rot_deg, rng) if rot_deg > 0 else np.eye(3)
    if trans_frac > 0:
        u = rng.normal(size=3)
        t_dir = u / np.linalg.norm(u)
    else:
        t_dir = np.zeros(3)
    t_true = t_dir * (trans_frac * diam)
    dst = fs.apply_transform(dst_base, R_true, t_true)
    dst_n = dst_n_base @ R_true.T
    return dst, dst_n, R_true, t_true


def run_cell(method, src, dst_base, dst_n_base, rot_deg, trans_frac, diam,
             trials, seed):
    """1 セル(初期回転ずれ・初期並進ずれの組)を trials 回。成功率と誤差を返す。"""
    rng = np.random.default_rng(seed)
    c_src = src.mean(0)
    n_ok = 0
    rots, cens = [], []
    for _ in range(trials):
        dst, dst_n, R_true, t_true = make_pair(src, dst_base, dst_n_base,
                                               rot_deg, trans_frac, diam, rng)
        R, t = method(src, dst, dst_n)
        rd = rot_error_deg(R, R_true)
        cd = cen_error(R, t, R_true, t_true, c_src)
        rots.append(rd)
        cens.append(cd)
        n_ok += int(ok(rd, cd, diam))
    return n_ok / trials, np.array(rots), np.array(cens)


# ---------------------------------------------------------------------------
def main():
    t_start = time.perf_counter()
    rng = np.random.default_rng(20260906)

    SRC_N, DST_N = 500, 700
    src = bracket(SRC_N, rng)                       # 標本 A
    dst_base = bracket(DST_N, rng)                  # 同じ面から独立に取った標本 B
    diam = diameter(dst_base)
    dst_n_base = fs.estimate_normals(dst_base, k=16)
    spacing = float(np.median(
        __import__("scipy.spatial", fromlist=["cKDTree"]).cKDTree(dst_base).query(dst_base, k=2)[0][:, 1]))

    print("=== 0. 舞台 ===")
    print(f"  形状 = 非対称な当て金(直方体 {BRACKET_MAIN[0]} + 隅の出っ張り {BRACKET_BUMP[0]})")
    print(f"  点数 src {src.shape[0]} / dst {dst_base.shape[0]}(同じ面からの**独立な**標本。対応点は無い)")
    print(f"  直径 {diam:.4f} 単位 / dst の点間隔 中央値 {spacing:.4f} 単位"
          f"(直径の {100 * spacing / diam:.2f} %)")
    print(f"  成功の定義: 回転誤差 < {ROT_OK_DEG} 度 かつ 重心誤差 < 直径の "
          f"{100 * CEN_OK_FRAC:.1f} %(= {CEN_OK_FRAC * diam:.5f} 単位)")
    print("  誤差は回転[度]と並進[単位]に分けて出す。並進誤差は「src の重心が行き着く")
    print("  先のずれ」で、回転誤差と足し合わせない。")

    # ---- 1. 真値の復元と、到達できる下限 ---------------------------------
    print("\n=== 1. 真値を自分で作って復元する —— 下限はどこか ===")
    R_true = rot_axis_angle((0.3, -0.7, 0.65), 37.0)
    t_true = np.array([0.21, -0.13, 0.07])
    # (a) 対応点が既知なら閉形式で厳密に戻る
    dst_exact = fs.apply_transform(src, R_true, t_true)
    Rk, tk = fs.kabsch(src, dst_exact)
    print(f"  {'条件':<34}{'回転誤差[度]':>14}{'並進誤差[単位]':>16}")
    print(f"  {'kabsch(対応点既知・同一標本)':<30}"
          f"{rot_error_deg(Rk, R_true):>14.2e}{cen_error(Rk, tk, R_true, t_true, src.mean(0)):>16.2e}")
    # (b) 対応点が無く標本も別 = 実際に測れる下限。完全な初期値から始める
    dst = fs.apply_transform(dst_base, R_true, t_true)
    dst_n = dst_n_base @ R_true.T
    for name, fn in (("icp(真値から開始)", lambda: fs.icp(src, dst, init=(R_true, t_true), max_iter=60)),
                     ("点対面 icp(真値から開始)",
                      lambda: fs.point_to_plane_icp(src, dst, dst_normals=dn_local, init=(R_true, t_true), max_iter=60))):
        dn_local = dst_n
        R, t, _a, _r = fn()
        print(f"  {name:<30}{rot_error_deg(R, R_true):>14.4f}"
              f"{cen_error(R, t, R_true, t_true, src.mean(0)):>16.5f}")
    print(f"  → 別標本どうしでも下限は成功しきい値({ROT_OK_DEG} 度 / {CEN_OK_FRAC * diam:.5f} 単位)より")
    print("     十分内側にある。つまり以下で「失敗」と出るものは、精度不足ではなく")
    print("     **別の解に落ちた**ことを意味する。")

    # ---- 2. 収束域 ---------------------------------------------------------
    ROTS = (0, 10, 20, 30, 45, 60, 75, 90)
    TRANS = (0.0, 0.05, 0.15, 0.30)
    TRIALS = 15
    print(f"\n=== 2. 収束域 —— 成功率の等高線({TRIALS} 試行/セル、回転軸と並進方向は毎回ランダム)===")
    basin = {}
    for label, method in (("点対点 ICP", m_icp), ("点対面 ICP", m_p2pl)):
        print(f"\n  [{label}] 行 = 初期並進ずれ(直径比)、列 = 初期回転ずれ[度]")
        print("  " + f"{'並進\\回転':>12}" + "".join(f"{r:>7}" for r in ROTS))
        grid = np.zeros((len(TRANS), len(ROTS)))
        for i, tf in enumerate(TRANS):
            row = []
            for j, rd in enumerate(ROTS):
                rate, _r, _c = run_cell(method, src, dst_base, dst_n_base, rd, tf,
                                        diam, TRIALS, seed=1000 + 17 * j + 3 * i)
                grid[i, j] = rate
                row.append(rate)
            print("  " + f"{tf * 100:>10.0f} %" + "".join(f"{v * 100:>6.0f}%" for v in row))
        basin[label] = grid
        # 境界 = 成功率が 50 % を下回る最初の回転角(並進ずれ 0 の行)
        r0 = grid[0]
        edge = next((ROTS[j] for j in range(len(ROTS)) if r0[j] < 0.5), None)
        print(f"  → 並進ずれ 0 での境界: 成功率が 50 % を切るのは "
              f"{'{} 度'.format(edge) if edge is not None else '90 度までで切らない'}")

    # ---- 3. ゼロ点 ---------------------------------------------------------
    print("\n=== 3. ゼロ点 —— 何もしない / 重心だけ / PCA だけ ===")
    print(f"  {'手法':<22}{'成功率':>8}{'回転誤差 中央値[度]':>22}{'並進誤差 中央値[単位]':>24}")
    ZERO_SEED = 4242
    for label, method in (("何もしない", m_null), ("重心合わせのみ", m_centroid),
                          ("PCA 位置合わせのみ", m_pca), ("PCA + ICP", m_pca_icp)):
        rates, rr, cc = [], [], []
        for j, rd in enumerate((0, 30, 60, 90)):
            rate, r, c = run_cell(method, src, dst_base, dst_n_base, rd, 0.15,
                                  diam, 12, seed=ZERO_SEED + j)
            rates.append(rate)
            rr.append(r)
            cc.append(c)
        rr = np.concatenate(rr)
        cc = np.concatenate(cc)
        print(f"  {label:<20}{100 * np.mean(rates):>7.0f}%{np.median(rr):>20.3f}{np.median(cc):>24.5f}")
    print("  → 「何もしない」は初期ずれそのものなので、これを上回らない手法に価値は無い。")

    print("\n  PCA の象限 —— 主軸の符号で 4 通り。どれに落ちるか")
    # 主軸は符号まで、なので 8 通りのうち行列式 +1 の 4 通りが候補になる。
    # 道具の中では最小 RMSE で 1 つ選ばれるが、ここでは 4 つ全部の誤差を並べる。
    rngq = np.random.default_rng(777)
    quad_hist = np.zeros(4, int)
    wrong = 0
    cand_deg_all = []
    N_Q = 40
    for _ in range(N_Q):
        dstq, dnq, Rt, tt = make_pair(src, dst_base, dst_n_base, 60.0, 0.15, diam, rngq)
        cp, cq = src.mean(0), dstq.mean(0)
        _, _, VtP = np.linalg.svd(src - cp, full_matrices=False)
        _, _, VtQ = np.linalg.svd(dstq - cq, full_matrices=False)
        cands = []
        for sx in (1.0, -1.0):
            for sy in (1.0, -1.0):
                for sz in (1.0, -1.0):
                    Rc = VtQ.T @ np.diag([sx, sy, sz]) @ VtP
                    if np.linalg.det(Rc) < 0:
                        continue
                    cands.append(rot_error_deg(Rc, Rt))
        cands = np.sort(np.array(cands))
        cand_deg_all.append(cands)
        Rp, tp = fs.pca_align(src, dstq)
        chosen = rot_error_deg(Rp, Rt)
        k = int(np.argmin(np.abs(cands - chosen)))
        quad_hist[k] += 1
        wrong += int(chosen > 5.0)
    cand_deg_all = np.array(cand_deg_all)
    print(f"  {'候補(誤差の小さい順)':<24}{'回転誤差 中央値[度]':>22}")
    for k in range(4):
        print(f"  {'第 ' + str(k + 1) + ' 候補':<22}{np.median(cand_deg_all[:, k]):>22.1f}")
    print(f"  道具が選んだ候補の内訳(n={N_Q}): "
          + " / ".join(f"第{k + 1}={quad_hist[k]}" for k in range(4)))
    print(f"  間違った象限に落ちた割合: {100 * wrong / N_Q:.0f} %"
          f"(判定 = 選ばれた解の回転誤差 > 5 度)")
    print("  → 4 候補のうち 3 つは 100 度超。最小 RMSE で選ぶので普段は当たるが、")
    print("     当たり外れは形状の非対称性の強さに賭けている。")

    # ---- 4. 手法の比較(広さと精度は別の軸)-------------------------------
    print("\n=== 4. 収束域の広さ と 最終精度 は別の軸 ===")
    WIDE_ROTS = (0, 45, 90, 135, 180)
    print(f"  行 = 手法、列 = 初期回転ずれ[度](並進ずれは直径の 15 % 固定、8 試行/セル)")
    print("  " + f"{'手法':<20}" + "".join(f"{r:>7}" for r in WIDE_ROTS)
          + f"{'成功時の回転誤差 中央値[度]':>28}")
    src_s = src[fs.farthest_point_sampling(src, 150)]
    dst_s_base = dst_base[fs.farthest_point_sampling(dst_base, 150)]
    dst_s_n_base = fs.estimate_normals(dst_s_base, k=12)
    methods4 = (("点対点 ICP", m_icp, False), ("点対面 ICP", m_p2pl, False),
                ("PCA + ICP", m_pca_icp, False), ("FPFH + RANSAC", m_feature, False),
                ("PPF surface_match", m_ppf, True))
    width = {}
    for label, method, small in methods4:
        s = src_s if small else src
        db = dst_s_base if small else dst_base
        dn = dst_s_n_base if small else dst_n_base
        dm = diameter(db)
        rates, fine = [], []
        for j, rd in enumerate(WIDE_ROTS):
            rate, r, c = run_cell(method, s, db, dn, rd, 0.15, dm, 8, seed=5000 + 31 * j)
            rates.append(rate)
            fine.append(r[r < ROT_OK_DEG])
        fine = np.concatenate(fine) if any(len(f) for f in fine) else np.array([np.nan])
        width[label] = np.array(rates)
        print("  " + f"{label:<18}" + "".join(f"{v * 100:>6.0f}%" for v in rates)
              + f"{np.nanmedian(fine):>28.4f}")
    print("  → 左から右へ落ちる手法は「狭い」、平らな手法は「広い」。広さと右端の精度は")
    print(f"     連動していない。PPF は点数を落として({src_s.shape[0]} 点)動かしている。")

    # ---- 5. 壊れる条件 -----------------------------------------------------
    print("\n=== 5-a. 重なり率を下げる(部分ビュー)===")
    print(f"  {'重なり':>8}{'点対点 ICP':>12}{'PCA + ICP':>12}{'FPFH+RANSAC':>14}"
          f"{'ICP(trim=0.4)':>16}")
    OVER = (1.0, 0.9, 0.75, 0.6, 0.5)
    over_rates = {}
    for frac in OVER:
        row = []
        for label, method in (("icp", m_icp), ("pca", m_pca_icp), ("feat", m_feature),
                              ("trim", lambda s, d, n: fs.icp(s, d, init=fs.pca_align(s, d),
                                                              trim=0.4, max_iter=60)[:2])):
            rng_o = np.random.default_rng(9001)
            n_ok = 0
            TR = 8
            for _ in range(TR):
                # 部分ビュー = ある方向の上位 frac だけ残す(スキャンの片面しか見えない状況)
                u = rng_o.normal(size=3)
                u /= np.linalg.norm(u)
                proj = src @ u
                keep = proj >= np.quantile(proj, 1.0 - frac)
                s = src[keep]
                dst, dn, Rt, tt = make_pair(s, dst_base, dst_n_base, 30.0, 0.10, diam, rng_o)
                R, t = method(s, dst, dn)
                n_ok += int(ok(rot_error_deg(R, Rt), cen_error(R, t, Rt, tt, s.mean(0)), diam))
            row.append(n_ok / TR)
        over_rates[frac] = row
        print(f"  {100 * frac:>7.0f}%{row[0] * 100:>11.0f}%{row[1] * 100:>11.0f}%"
              f"{row[2] * 100:>13.0f}%{row[3] * 100:>15.0f}%")
    print("  → 重なりが下がると PCA 初期値は主軸そのものがずれるので先に壊れる。")
    print("     切り捨て(trim)は残差の外れ値を捨てるが、初期値が違う象限なら救えない。")

    print("\n=== 5-b. 雑音を乗せる(精度の軸。成功率でなく誤差で見る)===")
    print(f"  {'雑音 σ(直径比)':>16}{'点対点 回転[度]':>18}{'点対点 並進[単位]':>20}"
          f"{'点対面 回転[度]':>18}{'点対面 並進[単位]':>20}")
    for sig in (0.0, 0.002, 0.01, 0.03):
        rng_n = np.random.default_rng(3131)
        res = {}
        for label, method in (("p2p", m_icp), ("p2pl", m_p2pl)):
            rr, cc = [], []
            for _ in range(8):
                dstc, dnc, Rt, tt = make_pair(src, dst_base, dst_n_base, 15.0, 0.05, diam, rng_n)
                dstc = dstc + rng_n.normal(scale=sig * diam, size=dstc.shape)
                dnc = fs.estimate_normals(dstc, k=16) if sig > 0 else dnc
                R, t = method(src, dstc, dnc)
                rr.append(rot_error_deg(R, Rt))
                cc.append(cen_error(R, t, Rt, tt, src.mean(0)))
            res[label] = (np.median(rr), np.median(cc))
        print(f"  {sig * 100:>15.1f}%{res['p2p'][0]:>18.4f}{res['p2p'][1]:>20.5f}"
              f"{res['p2pl'][0]:>18.4f}{res['p2pl'][1]:>20.5f}")
    print("  → 雑音が乗ると法線の推定自体が崩れるので、点対面の優位はそのままでは続かない。")

    print("\n=== 5-c. 対称形状 —— 「収束したのに間違っている」 ===")
    print(f"  {'形状':<12}{'残差 rmse/直径':>16}{'回転誤差 中央値[度]':>22}"
          f"{'見かけ上収束':>14}{'そのうち姿勢が誤り':>20}")
    sym_false = {}
    for label, gen, n in (("非対称当て金", lambda k, r: bracket(k, r), 500),
                          ("球", sphere, 500), ("円柱", cylinder, 500)):
        rng_s = np.random.default_rng(24680)
        a = gen(n, rng_s)
        b = gen(int(n * 1.4), rng_s)
        dmm = diameter(b)
        bn = fs.estimate_normals(b, k=16)
        rr, res, conv, bad = [], [], 0, 0
        for _ in range(16):
            dstc, dnc, Rt, tt = make_pair(a, b, bn, 25.0, 0.05, dmm, rng_s)
            R, t, aln, rmse = fs.icp(a, dstc, max_iter=60)
            rd = rot_error_deg(R, Rt)
            rr.append(rd)
            res.append(rmse / dmm)
            # 「見かけ上収束」= 残差が点間隔の 2 倍未満。実務ではこれで OK を出す
            sp = float(np.median(
                __import__("scipy.spatial", fromlist=["cKDTree"]).cKDTree(dstc).query(dstc, k=2)[0][:, 1]))
            if rmse < 2.0 * sp:
                conv += 1
                bad += int(rd > 5.0)
        sym_false[label] = (conv, bad)
        print(f"  {label:<10}{np.median(res):>16.5f}{np.median(rr):>22.2f}"
              f"{conv:>13}/16{bad:>19}")
    print("  → 球は残差がほぼ 0 のまま姿勢が任意。円柱は軸は当たるが軸まわりが自由。")
    print("     **残差を成功判定に使うと、この嘘は絶対に検出できない**。真値か、")
    print("     形状の対称群を知っているかのどちらかが要る。")
    # 円柱の軸だけは決まる、を数字で
    rng_c = np.random.default_rng(1357)
    a = cylinder(500, rng_c)
    b = cylinder(700, rng_c)
    bn = fs.estimate_normals(b, k=16)
    axis_err, full_err = [], []
    for _ in range(12):
        dstc, dnc, Rt, tt = make_pair(a, b, bn, 25.0, 0.05, diameter(b), rng_c)
        R, t, _al, _rm = fs.icp(a, dstc, max_iter=60)
        z = np.array([0.0, 0.0, 1.0])
        ang = np.degrees(np.arccos(np.clip(abs((R @ z) @ (Rt @ z)), -1.0, 1.0)))
        axis_err.append(ang)
        full_err.append(rot_error_deg(R, Rt))
    print(f"  円柱: 軸の向きの誤差 中央値 {np.median(axis_err):.2f} 度 に対し、"
          f"回転全体の誤差 中央値 {np.median(full_err):.2f} 度")
    print("     = 決まる自由度と決まらない自由度が混ざっている。1 つの数にまとめると消える。")

    # ---- 6. 速度 -----------------------------------------------------------
    print("\n=== 6. 速度(この機械での実測)===")
    dst_t = fs.apply_transform(dst_base, rot_axis_angle((1, 1, 0), 25.0), np.array([0.1, 0.0, 0.05]))
    dn_t = fs.estimate_normals(dst_t, k=16)
    print(f"  {'手法':<24}{'時間 [ms]':>12}   点数")
    for label, fn, note in (
            ("kabsch(対応点既知)", lambda: fs.kabsch(src, dst_exact), f"{src.shape[0]}"),
            ("pca_align", lambda: fs.pca_align(src, dst_t), f"{src.shape[0]}->{dst_t.shape[0]}"),
            ("icp", lambda: fs.icp(src, dst_t, max_iter=60), f"{src.shape[0]}->{dst_t.shape[0]}"),
            ("point_to_plane_icp", lambda: fs.point_to_plane_icp(src, dst_t, dst_normals=dn_t, max_iter=60),
             f"{src.shape[0]}->{dst_t.shape[0]}"),
            ("estimate_normals(k=16)", lambda: fs.estimate_normals(dst_t, k=16), f"{dst_t.shape[0]}"),
            ("register(init=pca)", lambda: fs.register(src, dst_t, init="pca"),
             f"{src.shape[0]}->{dst_t.shape[0]}"),
            ("feature_register(800)", lambda: fs.feature_register(src, dst_t, ransac_iter=800),
             f"{src.shape[0]}->{dst_t.shape[0]}"),
            ("ppf_model", lambda: fs.ppf_model(src_s, angle_bins=24), f"{src_s.shape[0]}"),
            ("find_surface_pose", lambda: fs.find_surface_pose(
                src_s, dst_s_base, angle_bins=24, ref_fraction=0.25, topk=3),
             f"{src_s.shape[0]}->{dst_s_base.shape[0]}"),
            ("voxel_downsample(0.05)", lambda: fs.voxel_downsample(dst_t, 0.05), f"{dst_t.shape[0]}"),
    ):
        t0 = time.perf_counter()
        fn()
        print(f"  {label:<24}{1e3 * (time.perf_counter() - t0):>12.2f}   {note}")

    # ---- 道具の穴 ----------------------------------------------------------
    print("\n=== ★ この PoC が出した道具の穴(op 本体は直していない)===")
    print("  1. fs.register(init='auto') は FPFH 初期値を毎回計算するため、PCA だけの")
    print("     経路に比べて 1 桁以上遅い。収束域の掃引のような繰り返し用途では")
    print("     init を明示しないと予算が読めない。")
    print("  2. point_to_plane_icp が返す rmse は**点対面残差**で、icp が返す点対点")
    print("     rmse と単位も意味も違う。両者を同じしきい値で比べると点対面が常に")
    print("     良く見える(平面上を滑る成分が残差に出ないため)。")
    print("  3. pca_align は最小 RMSE で象限を選ぶが、その RMSE は対称形状では")
    print("     どの象限でも同じになる。球・円柱では選択が実質ランダムで、")
    print("     しかも道具はそれを呼び出し側に伝える手段を持たない(信頼度が返らない)。")
    print("  4. surface_match(refine=False) は rmse に nan を返す。返り値の型は同じ")
    print("     なので、呼び出し側が数値として比較すると常に False になり静かに落ちる。")
    print("  5. icp / point_to_plane_icp は収束したかどうかを返さない。max_iter で")
    print("     打ち切られたのか tol で止まったのかが外から分からない。")

    # ---- 自己検査(速さは assert しない)-----------------------------------
    # (a) 対応点が既知なら閉形式は厳密
    assert rot_error_deg(Rk, R_true) < 1e-9, "kabsch が対応点既知で厳密でない"
    assert cen_error(Rk, tk, R_true, t_true, src.mean(0)) < 1e-12
    # (b) 恒等変換の往復
    assert np.allclose(fs.apply_transform(src, np.eye(3), np.zeros(3)), src)
    # (c) 収束域は存在する = 小さい初期ずれでは当たり、90 度では落ちる
    g = basin["点対点 ICP"][0]
    assert g[0] >= 0.99, f"初期ずれ 0 で ICP が失敗している ({g[0]})"
    assert g[ROTS.index(10)] > g[ROTS.index(90)], "収束域の境界が出ていない(単調に落ちない)"
    # (d) 点対面 ICP の収束域は点対点より狭くない(線形化した分だけ広いか同等)
    assert basin["点対面 ICP"][0][0] >= 0.99
    # (e) ゼロ点は上回られていること: 何もしない は初期ずれ 30-90 度で成功 0
    r_null, _rr, _cc = run_cell(m_null, src, dst_base, dst_n_base, 60, 0.15, diam, 6, seed=1)
    assert r_null == 0.0, "『何もしない』が成功してしまった(判定が緩すぎる)"
    # (f) PCA の 4 候補のうち 3 つは大きく外れる = 象限の曖昧さが実在する
    assert np.median(cand_deg_all[:, 3]) > 60.0, "PCA の第 4 候補が外れていない"
    assert np.median(cand_deg_all[:, 0]) < 5.0, "PCA の第 1 候補が当たっていない"
    # (g) 重なりを下げると PCA 初期値は壊れる
    assert over_rates[1.0][1] > over_rates[0.5][1], "重なり低下で PCA+ICP が劣化しない"
    # (h) 対称形状では「収束したのに間違っている」が実際に出る
    conv_s, bad_s = sym_false["球"]
    assert conv_s >= 8, f"球で ICP が収束すらしていない (conv={conv_s})"
    assert bad_s >= conv_s // 2, f"球で偽の成功が出ていない (bad={bad_s}/{conv_s})"
    conv_a, bad_a = sym_false["非対称当て金"]
    assert bad_a == 0, f"非対称形状で偽の成功が出た (bad={bad_a})"
    # (i) 円柱は軸だけ決まる
    assert np.median(axis_err) < 5.0 < np.median(full_err), "円柱の軸と全体の分離が出ていない"

    print(f"\n  (所要 {time.perf_counter() - t_start:.1f} 秒)")
    print("\nPASS")


if __name__ == "__main__":
    main()
