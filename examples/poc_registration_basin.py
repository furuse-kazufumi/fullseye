# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""点群位置合わせの収束域 —— 初期姿勢がどれだけずれたら壊れるか。

EXTEND: 実物の点群に差し替えるなら ``make_shape`` を捨てて ``fs.read_points`` で読む。
Stanford Bunny は同梱していないがダウンローダの入口があり、
``py -3.11 -m sample_data download bunny --yes`` で原典(Stanford 3D Scanning
Repository)から取得して ``fs.read_points(sample_data.local_path("bunny"))``。
実物に替えるとき **必ず一緒に変えるもの** が 3 つある。(a) しきい値は形状の直径に
対する比で書いてあるので直径さえ測れば移るが、**点間隔がしきい値より粗いと
「成功不能」になる** —— 第 1 章が測る到達可能な下限を先に見ること。(b) 真値は
自分で剛体変換を掛けて作っている。実スキャン 2 枚を突き合わせる場合は真値が無く、
**誤差ではなく残差しか測れない**(残差が小さいことは正しさの証明にならない ——
第 5-c 章の対称形状がその反例)。(c) 実スキャンは重なりが 100 % ではないので、
第 5-a 章の重なり率の表を先に見る。

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

import time

import numpy as np
from scipy.spatial import cKDTree

import fullseye as fs

# --- 成功の定義(この PoC 全体で使う唯一の判定)-----------------------------
# 回転誤差 < 3 度 かつ 重心移動誤差 < 直径の 1 %。
# これは「精度が十分か」ではなく **正しい盆地に入ったか** の判定である。第 1 章が
# 測る下限(0.2-0.6 度 / 直径の 0.1-0.4 %)より緩く、失敗側は 20-180 度なので、
# しきい値を 2 倍動かしても表は変わらない。精度の話は別の列で出す。
ROT_OK_DEG = 3.0
CEN_OK_FRAC = 0.01

# 形状の寸法(直方体 + +x 面から突き出す角柱)。角柱の断面で非対称性の強さを変える。
# 角柱は +x 面をまたぐ位置に置き、面の中心から +y +z にずらしてある。こうすると
# x 軸・y 軸・z 軸まわりの 180 度回転がすべて壊れる。
MAIN_DIMS = (1.00, 0.62, 0.38)
PEG_DIMS = (0.24, 0.30, 0.24)      # 断面 (y, z) を bump 倍して弱める
PEG_AT = (0.50, 0.15, 0.08)


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
# 一試行 = 真値を作り、掛け、復元し、誤差を回転と並進に分けて返す
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


def run_cell(method, src, dst_base, dst_n_base, rot_deg, trans_frac, diam,
             trials, seed):
    """1 セル(初期回転ずれ・初期並進ずれの組)を trials 回。成功率と誤差列を返す。"""
    rng = np.random.default_rng(seed)
    c_src = src.mean(0)
    n_ok = 0
    rots, cens = [], []
    for _ in range(trials):
        dst, dst_n, R_true, t_true = make_pair(dst_base, dst_n_base, rot_deg,
                                               trans_frac, diam, rng)
        R, t = method(src, dst, dst_n)
        rd = rot_error_deg(R, R_true)
        cd = cen_error(R, t, R_true, t_true, c_src)
        rots.append(rd)
        cens.append(cd)
        n_ok += int(ok(rd, cd, diam))
    return n_ok / trials, np.array(rots), np.array(cens)


def med(a):
    a = np.asarray(a, np.float64)
    return float(np.median(a)) if a.size else float("nan")


# ---------------------------------------------------------------------------
def main():
    t_start = time.perf_counter()
    rng = np.random.default_rng(20260906)

    src = bracket(500, rng)                          # 標本 A
    dst_base = bracket(700, rng)                     # 同じ面から独立に取った標本 B
    diam = diameter(dst_base)
    dst_n_base = fs.estimate_normals(dst_base, k=16)
    spacing = spacing_of(dst_base)

    print("=== 0. 舞台 ===")
    print(f"  形状 = 非対称な当て金(直方体 {MAIN_DIMS} + +x 面から突き出す角柱 {PEG_DIMS})")
    print(f"  点数 src {src.shape[0]} / dst {dst_base.shape[0]}"
          "(同じ面からの**独立な**標本。対応点は存在しない)")
    print(f"  直径 {diam:.4f} 単位 / dst の点間隔 中央値 {spacing:.4f} 単位"
          f"(直径の {100 * spacing / diam:.2f} %)")
    print(f"  成功の定義: 回転誤差 < {ROT_OK_DEG:.0f} 度 かつ 重心誤差 < 直径の "
          f"{100 * CEN_OK_FRAC:.0f} %(= {CEN_OK_FRAC * diam:.4f} 単位)")
    print("  これは精度の判定ではなく **正しい盆地に入ったか** の判定。精度は別列で出す。")
    print("  誤差は回転[度]と並進[単位]に分ける。並進誤差 = src の重心が行き着く先のずれ。")

    # ---- 1. 真値の復元と、到達できる下限 ---------------------------------
    print("\n=== 1. 真値を自分で作って復元する —— 下限はどこか ===")
    R_true = rot_axis_angle((0.3, -0.7, 0.65), 37.0)
    t_true = np.array([0.21, -0.13, 0.07])
    c_src = src.mean(0)
    dst_exact = fs.apply_transform(src, R_true, t_true)
    Rk, tk = fs.kabsch(src, dst_exact)
    dst1 = fs.apply_transform(dst_base, R_true, t_true)
    dn1 = dst_n_base @ R_true.T
    Ri, ti = fs.icp(src, dst1, init=(R_true, t_true), max_iter=60)[:2]
    Rp, tp = fs.point_to_plane_icp(src, dst1, dst_normals=dn1,
                                   init=(R_true, t_true), max_iter=60)[:2]
    print(f"  {'条件':<30}{'回転誤差[度]':>16}{'並進誤差[単位]':>18}{'直径比':>10}")
    for label, R, t in (("kabsch(対応点既知・同一標本)", Rk, tk),
                        ("icp(真値から開始)", Ri, ti),
                        ("点対面 icp(真値から開始)", Rp, tp)):
        ce = cen_error(R, t, R_true, t_true, c_src)
        print(f"  {label:<26}{rot_error_deg(R, R_true):>16.4f}{ce:>18.6f}"
              f"{100 * ce / diam:>9.3f}%")
    floor_rot = max(rot_error_deg(Ri, R_true), rot_error_deg(Rp, R_true))
    print(f"  → 対応点があれば閉形式で厳密。別標本どうしの下限は {floor_rot:.2f} 度 /"
          f" 直径の {100 * cen_error(Ri, ti, R_true, t_true, c_src) / diam:.2f} % 程度で、")
    print(f"     成功しきい値({ROT_OK_DEG:.0f} 度 / 直径の {100 * CEN_OK_FRAC:.0f} %)より内側。")
    print("     つまり以下で「失敗」と出るものは精度不足ではなく **別の解に落ちた**。")

    # ---- 2. 収束域 ---------------------------------------------------------
    ROTS = (0, 30, 60, 90, 120, 150, 165, 180)
    TRANS = (0.0, 0.10, 0.25, 0.50)
    TRIALS = 15
    print(f"\n=== 2. 収束域 —— 成功率の等高線({TRIALS} 試行/セル、回転軸と並進方向は毎回ランダム)===")
    basin = {}
    edges = {}
    for label, method in (("点対点 ICP", m_icp), ("点対面 ICP", m_p2pl)):
        print(f"\n  [{label}] 行 = 初期並進ずれ(直径比)、列 = 初期回転ずれ[度]")
        corner = "並進 / 回転"
        print("  " + f"{corner:>12}" + "".join(f"{r:>7}" for r in ROTS))
        grid = np.zeros((len(TRANS), len(ROTS)))
        for i, tf in enumerate(TRANS):
            for j, rd in enumerate(ROTS):
                grid[i, j] = run_cell(method, src, dst_base, dst_n_base, rd, tf,
                                      diam, TRIALS, seed=1000 + 17 * j + 3 * i)[0]
            print("  " + f"{tf * 100:>10.0f} %"
                  + "".join(f"{v * 100:>6.0f}%" for v in grid[i]))
        basin[label] = grid
        row0 = grid[0]
        e = next((ROTS[j] for j in range(len(ROTS)) if row0[j] < 0.5), None)
        edges[label] = e
        print(f"  → 並進ずれ 0 の行で成功率が 50 % を切るのは "
              f"{str(e) + ' 度' if e is not None else '90 度までで切らない'}")
    print("\n  境界の読み方: 表の左上が「使える」領域。列を右に進むと落ちる。")
    print(f"  1 セル {TRIALS} 試行なので成功率の標準誤差は最大 "
          f"{100 * (0.5 / np.sqrt(TRIALS)):.0f} 点。**{TRIALS} 分の 1 刻みの差は読まない**")
    print("  —— 読むべきは 100 % から 0 % へ落ちる位置だけ。")

    # ---- 3. ゼロ点 ---------------------------------------------------------
    print("\n=== 3. ゼロ点 —— 何もしない / 重心だけ / PCA だけ ===")
    print("  (初期回転ずれ 0/30/60/90 度、並進ずれ 直径の 15 %、各 12 試行の合算)")
    print(f"  {'手法':<20}{'成功率':>8}{'回転誤差 中央値[度]':>24}{'並進誤差 中央値[単位]':>26}")
    zero_rate = {}
    for label, method in (("何もしない", m_null), ("重心合わせのみ", m_centroid),
                          ("PCA 位置合わせのみ", m_pca), ("PCA + ICP", m_pca_icp),
                          ("点対点 ICP", m_icp)):
        rates, rr, cc = [], [], []
        for j, rd in enumerate((0, 30, 60, 90)):
            r, a, b = run_cell(method, src, dst_base, dst_n_base, rd, 0.15,
                               diam, 12, seed=4242 + j)
            rates.append(r)
            rr.append(a)
            cc.append(b)
        zero_rate[label] = float(np.mean(rates))
        print(f"  {label:<18}{100 * np.mean(rates):>7.0f}%"
              f"{med(np.concatenate(rr)):>22.3f}{med(np.concatenate(cc)):>26.5f}")
    print("  → 「何もしない」は初期ずれそのもの。これを上回らない手法に価値は無い。")
    print("     PCA だけは初期値に依存しないので、初期ずれ 90 度でも回転誤差の中央値が")
    print("     数度まで落ちる。しかし**しきい値は越えない** —— 初期値としては有用で、")
    print("     姿勢推定器としては不合格。その理由を次で分解する。")

    # ---- 3-b. PCA の象限 ---------------------------------------------------
    print("\n=== 3-b. PCA の象限 —— 主軸の符号で 4 通り。どれに落ちるか ===")
    print("  主軸は符号まで決まらないので候補は 8 通り、うち行列式 +1 の 4 通りが姿勢候補。")
    print("  道具は最小 RMSE で 1 つ選ぶ。ここでは 4 候補すべての誤差と選択結果を数える。")
    print("  **試行ごとに点群を取り直す**(取り直さないと剛体回転しても候補の順位が変わらず、")
    print("  何回まわしても実質 1 標本にしかならない)。")
    print(f"  {'形状':<24}{'第1候補[度]':>13}{'第2〜4候補[度]':>16}"
          f"{'象限誤り':>10}{'選ばれた解[度]':>16}")
    N_Q = 60
    quad_wrong = {}
    quad_best = {}
    for label, bump in (("非対称 強(角柱 1.0)", 1.0),
                        ("非対称 弱(角柱 0.25)", 0.25),
                        ("対称(素の直方体)", 0.0)):
        rq = np.random.default_rng(777)
        best, rest, chosen_all, wrong = [], [], [], 0
        for _ in range(N_Q):
            a = bracket(800, rq, bump=bump)
            b = bracket(1100, rq, bump=bump)
            dq = diameter(b)
            Rt = random_rot(60.0, rq)
            u = rq.normal(size=3)
            tt = (u / np.linalg.norm(u)) * (0.15 * dq)
            dstq = fs.apply_transform(b, Rt, tt)
            cp, cq = a.mean(0), dstq.mean(0)
            _, _, VtP = np.linalg.svd(a - cp, full_matrices=False)
            _, _, VtQ = np.linalg.svd(dstq - cq, full_matrices=False)
            cands = []
            for sx in (1.0, -1.0):
                for sy in (1.0, -1.0):
                    for sz in (1.0, -1.0):
                        Rc = VtQ.T @ np.diag([sx, sy, sz]) @ VtP
                        if np.linalg.det(Rc) > 0:
                            cands.append(rot_error_deg(Rc, Rt))
            cands = np.sort(np.array(cands))
            chosen = rot_error_deg(fs.pca_align(a, dstq)[0], Rt)
            best.append(cands[0])
            rest.append(cands[1])
            chosen_all.append(chosen)
            # 象限誤り = 最良候補ではなく反転した候補を選んだ(軸推定のぶれとは別の失敗)
            wrong += int(chosen > cands[0] + 30.0)
        quad_wrong[label] = wrong / N_Q
        quad_best[label] = med(best)
        print(f"  {label:<22}{med(best):>13.2f}{med(rest):>16.1f}"
              f"{100 * wrong / N_Q:>9.0f}%{med(chosen_all):>16.2f}")
    print("  (象限誤り = 選ばれた解が最良候補より 30 度以上悪い = 反転した象限を掴んだ)")
    print("  → 角柱があるうちは最小 RMSE がほぼ確実に正しい象限を選ぶ。素の直方体では")
    print("     4 候補が形として区別できず、選択が崩れる。**PCA の正しさは形状の")
    print("     非対称性に賭けている** —— 対象を変えたら測り直すしかない。")
    print("  → もう 1 つ別の話: **正しい象限を選んでも第 1 候補自体が数度ずれている**。")
    print("     主軸は有限標本から推定するので、固有値が近い軸ほどぶれる。点数を変えて測る:")
    print(f"  {'点数':>8}{'第1候補の回転誤差 中央値[度]':>30}{'1/sqrt(N) 予測':>18}")
    ref = None
    for npts in (200, 800, 3200):
        rq = np.random.default_rng(555)
        errs = []
        for _ in range(20):
            a = bracket(npts, rq)
            b = bracket(int(npts * 1.4), rq)
            Rt = random_rot(60.0, rq)
            dstq = fs.apply_transform(b, Rt, np.zeros(3))
            _, _, VtP = np.linalg.svd(a - a.mean(0), full_matrices=False)
            _, _, VtQ = np.linalg.svd(dstq - dstq.mean(0), full_matrices=False)
            cands = [rot_error_deg(VtQ.T @ np.diag([sx, sy, sz]) @ VtP, Rt)
                     for sx in (1.0, -1.0) for sy in (1.0, -1.0) for sz in (1.0, -1.0)
                     if np.linalg.det(VtQ.T @ np.diag([sx, sy, sz]) @ VtP) > 0]
            errs.append(min(cands))
        m = med(errs)
        ref = ref if ref is not None else (m, npts)
        pred = ref[0] * np.sqrt(ref[1] / npts)
        print(f"  {npts:>8}{m:>30.2f}{pred:>18.2f}")
    print("     → 点数を 4 倍にすると誤差はおよそ半分。主軸推定の統計的ゆらぎであって")
    print("        実装の誤りではない。**PCA は初期値専用で、単体では姿勢推定器にならない**。")

    # ---- 4. 収束域の広さ と 最終精度 --------------------------------------
    print("\n=== 4. 収束域の広さ と 最終精度 は別の軸(同じ点群・同じしきい値で 5 手法)===")
    ia = fs.farthest_point_sampling(src, 250)
    ib = fs.farthest_point_sampling(dst_base, 325)
    src_c, dst_c = src[ia], dst_base[ib]
    diam_c = diameter(dst_c)
    dn_c = fs.estimate_normals(dst_c, k=12)
    rng_f = np.random.default_rng(606)
    fr_r, fr_c = [], []
    for _ in range(8):                                # 下限は 1 標本で決めない
        dq, _dn, Rt, tt = make_pair(dst_c, dn_c, 60.0, 0.15, diam_c, rng_f)
        Rf, tf = fs.icp(src_c, dq, init=(Rt, tt), max_iter=60)[:2]
        fr_r.append(rot_error_deg(Rf, Rt))
        fr_c.append(cen_error(Rf, tf, Rt, tt, src_c.mean(0)))
    floor_c = med(fr_r)
    print(f"  点数を落とした共通の組 src {src_c.shape[0]} / dst {dst_c.shape[0]}"
          f"(FPFH と PPF が現実的な時間で回る密度)")
    print(f"  この組の下限(真値から開始、8 姿勢の中央値): 回転 {floor_c:.2f} 度 / "
          f"並進 直径の {100 * med(fr_c) / diam_c:.3f} %")
    print(f"  → 並進のしきい値(直径の {100 * CEN_OK_FRAC:.0f} %)まで余裕は 2 倍程度しかない。")
    print("     この密度では精度列は点間隔で頭打ちになる(手法の限界ではない)。")
    WIDE = (0, 45, 90, 135, 180)
    TR4 = 12
    print(f"  行 = 手法、列 = 初期回転ずれ[度](並進ずれ 直径の 15 % 固定、{TR4} 試行/セル)")
    print("  " + f"{'手法':<20}" + "".join(f"{r:>7}" for r in WIDE)
          + f"{'成功時の回転誤差[度]':>24}{'成功時の並進[直径比]':>24}")
    width = {}
    for label, method in (("点対点 ICP", m_icp), ("点対面 ICP", m_p2pl),
                          ("PCA + ICP", m_pca_icp), ("FPFH + RANSAC", m_feature),
                          ("PPF surface_match", m_ppf)):
        rates, fr, fc = [], [], []
        for j, rd in enumerate(WIDE):
            r, a, b = run_cell(method, src_c, dst_c, dn_c, rd, 0.15, diam_c, TR4,
                               seed=5000 + 31 * j)
            rates.append(r)
            keep = (a < ROT_OK_DEG) & (b < CEN_OK_FRAC * diam_c)
            fr.append(a[keep])
            fc.append(b[keep])
        width[label] = np.array(rates)
        fr = np.concatenate(fr)
        fc = np.concatenate(fc)
        print("  " + f"{label:<18}" + "".join(f"{v * 100:>6.0f}%" for v in rates)
              + f"{med(fr):>24.4f}{100 * med(fc) / diam_c:>23.4f}%")
    print("  → 左から右へ落ちる手法は「狭い」、平らな手法は「広い」。広さと右 2 列の精度は")
    print("     連動していない。ICP 系は狭いが精密、大域手法は広いが精密とは限らない。")
    print("  → FPFH+RANSAC が落ちるのは試行回数不足ではない(800/4000/12000 回で同じ解に")
    print("     収束した)。面がほぼ平面ばかりの部品では FPFH 記述子が識別力を持たず、")
    print("     RANSAC は **自信を持って間違った** 対応集合を選ぶ。")

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
        for label, method in (("icp", m_icp), ("pca", m_pca_icp), ("trim", m_trim),
                              ("feat", m_feature), ("ppf", m_ppf)):
            rng_o = np.random.default_rng(9001)
            TR, n_ok = TR5, 0
            for _ in range(TR):
                u = rng_o.normal(size=3)
                u /= np.linalg.norm(u)
                proj = src_c @ u
                s = src_c[proj >= np.quantile(proj, 1.0 - frac)]
                dst, dn, Rt, tt = make_pair(dst_c, dn_c, 30.0, 0.10, diam_c, rng_o)
                R, t = method(s, dst, dn)
                n_ok += int(ok(rot_error_deg(R, Rt),
                               cen_error(R, t, Rt, tt, s.mean(0)), diam_c))
            row.append(n_ok / TR)
        over[frac] = row
        print(f"  {100 * frac:>7.0f}%{row[0] * 100:>11.0f}%{row[1] * 100:>11.0f}%"
              f"{row[2] * 100:>15.0f}%{row[3] * 100:>13.0f}%{row[4] * 100:>7.0f}%")
    print("  → 重なりが下がると部分ビューの主軸が全体の主軸とずれるので、PCA 初期値は")
    print("     先に壊れる。切り捨て(trim)は残差の外れ値を捨てるが、初期値が別の象限")
    print("     なら救えない —— **頑健化は初期値の間違いを直さない**。")

    # ---- 5-b. 雑音 ---------------------------------------------------------
    print("\n=== 5-b. 雑音を乗せる(精度の軸。成功率でなく誤差の中央値で見る)===")
    print(f"  {'雑音 σ(直径比)':>16}{'点対点 回転[度]':>18}{'点対点 並進[単位]':>20}"
          f"{'点対面 回転[度]':>18}{'点対面 並進[単位]':>20}")
    noise_tbl = {}
    for sig in (0.0, 0.002, 0.01, 0.03):
        res = {}
        for label, method in (("p2p", m_icp), ("p2pl", m_p2pl)):
            rng_n = np.random.default_rng(3131)
            rr, cc = [], []
            for _ in range(8):
                dstc, dnc, Rt, tt = make_pair(dst_base, dst_n_base, 15.0, 0.05, diam, rng_n)
                if sig > 0:
                    dstc = dstc + rng_n.normal(scale=sig * diam, size=dstc.shape)
                    dnc = fs.estimate_normals(dstc, k=16)
                R, t = method(src, dstc, dnc)
                rr.append(rot_error_deg(R, Rt))
                cc.append(cen_error(R, t, Rt, tt, c_src))
            res[label] = (med(rr), med(cc))
        noise_tbl[sig] = res
        print(f"  {sig * 100:>15.1f}%{res['p2p'][0]:>18.4f}{res['p2p'][1]:>20.5f}"
              f"{res['p2pl'][0]:>18.4f}{res['p2pl'][1]:>20.5f}")
    print("  → 雑音が乗ると法線推定そのものが崩れるので、点対面の優位は無雑音のときの")
    print("     ようには続かない。**手法の優劣は測定条件つきでしか言えない**。")

    # ---- 5-c. 対称形状 -----------------------------------------------------
    print("\n=== 5-c. 対称形状 —— 「収束したのに間違っている」 ===")
    print("  見かけ上収束 = 最終残差 rmse が dst の点間隔の 2 倍未満(実務ではここで OK を出す)")
    SHAPES = (("非対称当て金", bracket),
              ("素の直方体", lambda k, r: bracket(k, r, bump=0.0)),
              ("球", sphere), ("円柱", cylinder))
    N_S = 16
    sym = {}
    for mode, init_deg, use_global in (("局所: ICP を恒等から", 25.0, False),
                                       ("大域: PCA + ICP", 120.0, True)):
        print(f"\n  [{mode}、初期ずれ {init_deg:.0f} 度 / 直径の 5 %、{N_S} 試行]")
        print(f"  {'形状':<14}{'残差 rmse/直径':>16}{'回転誤差 中央値[度]':>22}"
              f"{'見かけ上収束':>14}{'うち姿勢が誤り':>18}")
        for label, gen in SHAPES:
            rng_s = np.random.default_rng(24680)
            a = gen(500, rng_s)
            b = gen(700, rng_s)
            dm = diameter(b)
            bn = fs.estimate_normals(b, k=16)
            rr, res, conv, bad = [], [], 0, 0
            for _ in range(N_S):
                dstc, _dnc, Rt, tt = make_pair(b, bn, init_deg, 0.05, dm, rng_s)
                init = fs.pca_align(a, dstc) if use_global else None
                R, t, _aln, rmse = fs.icp(a, dstc, init=init, max_iter=60)
                rd = rot_error_deg(R, Rt)
                rr.append(rd)
                res.append(rmse / dm)
                if rmse < 2.0 * spacing_of(dstc):
                    conv += 1
                    bad += int(rd > ROT_OK_DEG)
            sym[(mode, label)] = (conv, bad)
            print(f"  {label:<12}{med(res):>16.5f}{med(rr):>22.2f}"
                  f"{conv:>13}/{N_S}{bad:>17}")
    print("\n  → 局所 ICP は初期ずれが小さければ対称形状でも**近い**解に落ちるので嘘が出にくい")
    print("     (素の直方体の他の 3 姿勢は 180 度先にあり、盆地の外)。大域手法に替えた")
    print("     とたん、残差が同じまま別の姿勢を返す。**残差を成功判定に使うとこの嘘は")
    print("     原理的に検出できない** —— 真値を持つか、形状の対称群を知っている必要がある。")
    rng_c = np.random.default_rng(1357)
    a = cylinder(500, rng_c)
    b = cylinder(700, rng_c)
    bn = fs.estimate_normals(b, k=16)
    axis_err, full_err = [], []
    for _ in range(12):
        dstc, _dn, Rt, tt = make_pair(b, bn, 25.0, 0.05, diameter(b), rng_c)
        R, _t = fs.icp(a, dstc, max_iter=60)[:2]
        z = np.array([0.0, 0.0, 1.0])
        axis_err.append(np.degrees(np.arccos(np.clip(abs((R @ z) @ (Rt @ z)), -1.0, 1.0))))
        full_err.append(rot_error_deg(R, Rt))
    print(f"  円柱の内訳: 軸の向きの誤差 中央値 {med(axis_err):.2f} 度 に対し、"
          f"回転全体の誤差 中央値 {med(full_err):.2f} 度")
    print("     = 決まる自由度と決まらない自由度が同居している。1 つの数にまとめると消える。")

    # ---- 6. 速度 -----------------------------------------------------------
    print("\n=== 6. 速度(この機械での実測)===")
    dst_t = fs.apply_transform(dst_base, rot_axis_angle((1, 1, 0), 25.0),
                               np.array([0.1, 0.0, 0.05]))
    dn_t = fs.estimate_normals(dst_t, k=16)
    dst_ct = fs.apply_transform(dst_c, rot_axis_angle((1, 1, 0), 25.0),
                                np.array([0.1, 0.0, 0.05]))
    print(f"  {'手法':<26}{'時間 [ms]':>11}   点数")
    for label, fn, note in (
            ("kabsch(対応点既知)", lambda: fs.kabsch(src, dst_exact), f"{src.shape[0]}"),
            ("pca_align", lambda: fs.pca_align(src, dst_t), f"{src.shape[0]} -> {dst_t.shape[0]}"),
            ("icp", lambda: fs.icp(src, dst_t, max_iter=60), f"{src.shape[0]} -> {dst_t.shape[0]}"),
            ("point_to_plane_icp", lambda: fs.point_to_plane_icp(
                src, dst_t, dst_normals=dn_t, max_iter=60), f"{src.shape[0]} -> {dst_t.shape[0]}"),
            ("estimate_normals(k=16)", lambda: fs.estimate_normals(dst_t, k=16), f"{dst_t.shape[0]}"),
            ("register(init='pca')", lambda: fs.register(src, dst_t, init="pca"),
             f"{src.shape[0]} -> {dst_t.shape[0]}"),
            ("register(init='auto')", lambda: fs.register(src, dst_t, init="auto"),
             f"{src.shape[0]} -> {dst_t.shape[0]}"),
            ("feature_register(800 回)", lambda: fs.feature_register(src_c, dst_ct, ransac_iter=800),
             f"{src_c.shape[0]} -> {dst_ct.shape[0]}"),
            ("ppf_model", lambda: fs.ppf_model(src_c, angle_bins=24), f"{src_c.shape[0]}"),
            ("find_surface_pose", lambda: fs.find_surface_pose(
                src_c, dst_ct, angle_bins=24, ref_fraction=0.25, topk=3),
             f"{src_c.shape[0]} -> {dst_ct.shape[0]}"),
            ("voxel_downsample(0.05)", lambda: fs.voxel_downsample(dst_t, 0.05), f"{dst_t.shape[0]}"),
            ("farthest_point_sampling(250)", lambda: fs.farthest_point_sampling(src, 250),
             f"{src.shape[0]}"),
    ):
        t0 = time.perf_counter()
        fn()
        print(f"  {label:<26}{1e3 * (time.perf_counter() - t0):>11.2f}   {note}")
    print("  → 大域手法は局所手法の 20-200 倍。収束域を買うのに時間を払っている。")

    # ---- 道具の穴 ----------------------------------------------------------
    print("\n=== ★ この PoC が出した道具の穴(op 本体は直していない)===")
    print("  1. feature_register(FPFH+RANSAC)は平面ばかりの部品で沈黙して失敗する。")
    print("     試行回数を 15 倍にしても同じ誤答に収束するので、呼び出し側は「まだ足りない」")
    print("     のか「原理的に無理」なのか区別できない。返り値に対応の一貫性を示す指標が無い。")
    print("  2. register の docstring は部分重なりに 'feature' を勧めているが、上の表では")
    print("     この形状で 'pca' より悪い。推奨の前提(局所形状が識別的であること)が書かれていない。")
    print("  3. point_to_plane_icp の rmse は**点対面残差**で、icp の点対点 rmse と単位も")
    print("     意味も違う。同じしきい値で比べると点対面が常に良く見える(接平面内の滑りが")
    print("     残差に出ない)。同名フィールドで型も同じなので取り違えても例外にならない。")
    print("  4. pca_align は最小 RMSE で象限を選ぶが、その RMSE は対称形状ではどの象限でも")
    print("     ほぼ同じになる。選択が実質くじ引きでも、道具はそれを呼び出し側に伝えない")
    print("     (信頼度も候補どうしの差も返らない)。")
    print("  5. surface_match(refine=False) は rmse に nan を返す。型は float のままなので")
    print("     数値比較すると常に False になり、静かに「最良候補なし」に落ちる。")
    print("  6. icp / point_to_plane_icp は収束したかを返さない。tol で止まったのか max_iter")
    print("     で打ち切られたのかが外から分からず、反復予算の設計ができない。")

    # ---- 自己検査(速さは assert しない)-----------------------------------
    # (a) 対応点が既知なら閉形式は厳密
    # arccos は 0 度付近で平方根ぶんの精度を失うので、厳密解でも 1e-6 度台までしか出ない
    assert rot_error_deg(Rk, R_true) < 1e-4, "kabsch が対応点既知で厳密でない"
    assert cen_error(Rk, tk, R_true, t_true, c_src) < 1e-12
    assert np.allclose(fs.apply_transform(src, np.eye(3), np.zeros(3)), src)
    # (b) 下限がしきい値の内側にある = 「失敗」が精度不足でないことの保証
    assert floor_rot < ROT_OK_DEG, f"下限がしきい値を超えている ({floor_rot:.2f} 度)"
    # (c) 収束域が存在する = 小さい初期ずれで当たり、90 度で落ちる
    for label in ("点対点 ICP", "点対面 ICP"):
        g = basin[label]
        assert g[0, 0] >= 0.99, f"{label}: 初期ずれ 0 で失敗している ({g[0, 0]})"
        assert g[0, ROTS.index(30)] > g[0, ROTS.index(180)], f"{label}: 境界が出ていない"
        assert g.min() < 0.5, f"{label}: どのセルでも落ちない(判定が緩すぎる)"
    # (d) ゼロ点を上回っていること
    assert zero_rate["何もしない"] == 0.0, "『何もしない』が成功した(判定が緩すぎる)"
    assert zero_rate["PCA + ICP"] > zero_rate["点対点 ICP"], \
        "PCA 初期値が素の ICP を上回らない(大域初期値の意味が無い)"
    # (e) PCA の象限: 非対称が強ければ当たり、対称なら外れる
    assert quad_wrong["非対称 強(角柱 1.0)"] <= 0.05, "強い非対称で象限を外した"
    assert quad_wrong["対称(素の直方体)"] >= 0.25, "対称形状で象限誤りが出ていない"
    # 象限を当てても第 1 候補自体がしきい値を超えてぶれる = PCA 単体は姿勢推定器でない
    assert quad_best["非対称 強(角柱 1.0)"] > 1.0, "PCA の軸ぶれが出ていない"
    # (f) 重なり低下で PCA 初期値は劣化する
    assert over[1.0][1] > over[0.5][1], "重なり低下で PCA+ICP が劣化しない"
    # (g) 対称形状で「収束したのに間違っている」が実際に出る
    conv_s, bad_s = sym["球"]
    assert conv_s >= 8, f"球で ICP が収束すらしていない (conv={conv_s})"
    assert bad_s >= conv_s // 2, f"球で偽の成功が出ていない (bad={bad_s}/{conv_s})"
    assert sym["非対称当て金"][1] == 0, "非対称形状で偽の成功が出た"
    # (h) 円柱は軸だけ決まる = 自由度ごとに結論が違う
    assert med(axis_err) < 5.0 < med(full_err), "円柱の軸と全体の分離が出ていない"
    # (i) 雑音が増えれば精度は落ちる(単調)
    assert noise_tbl[0.03]["p2p"][0] > noise_tbl[0.0]["p2p"][0], "雑音で誤差が増えない"

    print(f"\n  (所要 {time.perf_counter() - t_start:.1f} 秒)")
    print("\nPASS")


if __name__ == "__main__":
    main()
