"""事例: 向きバラバラの3Dスキャンを「種類」で引き当てる形状検索 (shape_descriptors).

倉庫や生産ラインで物体を3Dスキャンすると、毎回まったく違う向きで転がっている。
同じ種類(球・立方体・トーラス・円柱・円錐)は、どんな姿勢でも「同じ形」として
データベースから引き当てたい。素朴に座標や占有をそのまま比べると、少し回すだけで
数字が総入れ替わりになり、同じ形なのに別物と判定して検索が破綻する。

手法(線→面リフト): sh_descriptor は物体を中心まわりの同心球シェルに割り、各シェルの
模様を球面調和(SH)へ展開して「帯域(周波数)エネルギー」を (半径 x 帯域) の行列に
する。帯域エネルギーは回転しても帯域の内側で成分が混ざるだけで値が変わらない
(= 回転不変, Kazhdan 2003)。ここでは各クラスを点群として作り、fullseye の
points_to_voxel で密度ボクセルに焼き、sh_descriptor で記述子化。クエリは各クラスを
一様ランダムな3次元回転(Shoemake)で回し別サンプルし直したもので、
match_sh_descriptor(コサイン類似度)で最近傍クラスを引く。

検証(GT): クエリが自分のクラスを最近傍に引けるか(=検索成功)を全クラス・複数回転で
測り正解率を出す。beat-the-null: 回転不変性を持たない null 記述子(各軸の座標分布=
周辺分布を並べた軸別 Wasserstein 距離)を同条件で回す。null は「回転なし」なら別サンプル
でも正しく引けるのに、ランダム回転を掛けた瞬間に周辺分布が崩れて検索を外す。SH の
回転あり正解率が null の回転あり正解率を明確に上回ること、かつ null 自身が
「回転なし > 回転あり」で崩れることを assert し、勝因が回転不変性だと判別的に示す。
"""
import sys
from pathlib import Path

# 同名の example ファイルが top-level module を隠さないよう repo root を最優先に。
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

import match3d as X


# ═══════════════════════════════════════════════════════════════════════════
# 形状クラス = 点群ジェネレータ(表面サンプル、seed で決定的)
# ═══════════════════════════════════════════════════════════════════════════
def sphere_points(n, rng):
    """単位球の表面。等方(どの向きにも同じ)= 回転対称の代表。"""
    v = rng.normal(size=(n, 3))
    return v / (np.linalg.norm(v, axis=1, keepdims=True) + 1e-12)


def cube_points(n, rng):
    """立方体 [-1,1]^3 の6面。立方対称(l=4 に特徴が出る)。"""
    f = rng.integers(0, 6, size=n)                 # どの面か
    uv = rng.uniform(-1.0, 1.0, size=(n, 2))       # 面上の一様点
    P = np.empty((n, 3))
    ax = f // 2                                    # 固定する軸
    sign = np.where(f % 2 == 0, -1.0, 1.0)
    cols = np.array([[1, 2], [0, 2], [0, 1]])      # 面ごとの自由2軸
    for a in range(3):
        m = ax == a
        P[m[:, None] & (np.arange(3) == a)[None, :]] = 0  # placeholder
        P[np.ix_(m, [a])] = sign[m][:, None]
        free = cols[a]
        P[np.ix_(m, free)] = uv[m]
    return P


def torus_points(n, rng):
    """トーラス(主半径 R, 管半径 r)。中央に穴 = 内側シェルが空く独特の径方向profile。"""
    R, r = 0.65, 0.32
    th = rng.uniform(0, 2 * np.pi, n)
    ph = rng.uniform(0, 2 * np.pi, n)
    x = (R + r * np.cos(ph)) * np.cos(th)
    y = (R + r * np.cos(ph)) * np.sin(th)
    z = r * np.sin(ph)
    return np.stack([x, y, z], axis=1)


def cylinder_points(n, rng):
    """z軸まわりの円柱(側面+上下フタ)。軸対称+平らなフタ。"""
    rc, h = 0.55, 0.85
    lateral = rng.random(n) < 0.70                 # 側面 70% / フタ 30%
    th = rng.uniform(0, 2 * np.pi, n)
    P = np.empty((n, 3))
    zl = rng.uniform(-h, h, n)
    P[lateral, 0] = rc * np.cos(th[lateral])
    P[lateral, 1] = rc * np.sin(th[lateral])
    P[lateral, 2] = zl[lateral]
    cap = ~lateral
    rr = rc * np.sqrt(rng.random(cap.sum()))
    P[cap, 0] = rr * np.cos(th[cap])
    P[cap, 1] = rr * np.sin(th[cap])
    P[cap, 2] = np.where(rng.random(cap.sum()) < 0.5, -h, h)
    return P


def cone_points(n, rng):
    """z軸まわりの円錐(側面+底円)。軸対称だが上下非対称(先細り)。"""
    rb, zb, za = 0.78, -0.72, 0.92                 # 底半径 / 底z / 頂点z
    lateral = rng.random(n) < 0.78                 # 側面 78% / 底 22%
    th = rng.uniform(0, 2 * np.pi, n)
    P = np.empty((n, 3))
    s = np.sqrt(rng.random(lateral.sum()))          # 頂点付近が細いので面積補正
    rlat = rb * (1.0 - s)
    P[lateral, 0] = rlat * np.cos(th[lateral])
    P[lateral, 1] = rlat * np.sin(th[lateral])
    P[lateral, 2] = zb + s * (za - zb)
    base = ~lateral
    rr = rb * np.sqrt(rng.random(base.sum()))
    P[base, 0] = rr * np.cos(th[base])
    P[base, 1] = rr * np.sin(th[base])
    P[base, 2] = zb
    return P


SHAPES = {
    "sphere": sphere_points,
    "cube": cube_points,
    "torus": torus_points,
    "cylinder": cylinder_points,
    "cone": cone_points,
}


# ═══════════════════════════════════════════════════════════════════════════
# 幾何ユーティリティ(回転・正規化)— GT/前処理用(op ではない)
# ═══════════════════════════════════════════════════════════════════════════
def random_rotation(rng):
    """一様ランダムな3次元回転行列(Shoemake の四元数法, SO(3) 上一様)。"""
    u1, u2, u3 = rng.random(3)
    x = np.sqrt(1 - u1) * np.sin(2 * np.pi * u2)
    y = np.sqrt(1 - u1) * np.cos(2 * np.pi * u2)
    z = np.sqrt(u1) * np.sin(2 * np.pi * u3)
    w = np.sqrt(u1) * np.cos(2 * np.pi * u3)
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
    ])


def normalize_cloud(P):
    """重心を原点へ、重心からの最大距離で割って半径1へ = 回転不変な正準化。

    回転は重心からの距離集合を保存するのでスケール係数は回転で不変。よって回転した
    点群 = R @(正準化した点群)となり、SH も null も同じ土俵で比べられる。
    """
    Q = np.asarray(P, np.float64)
    Q = Q - Q.mean(axis=0, keepdims=True)
    rmax = np.linalg.norm(Q, axis=1).max()
    return Q / (rmax + 1e-12)


# 全形状を同一格子・同一 bounds に載せる(=マッチングの前提)。半径1をわずかに包む箱。
GRID = 48
LO = (-1.06, -1.06, -1.06)
HI = (1.06, 1.06, 1.06)
SMOOTH = 1.3
N_PTS = 8000


def voxelize(P):
    """点群 → 正準化 → fullseye points_to_voxel で密度ボクセル(sh_descriptor の入力)。"""
    return X.points_to_voxel(normalize_cloud(P), GRID, bounds=(LO, HI), smooth=SMOOTH)


# ═══════════════════════════════════════════════════════════════════════════
# null(回転不変でない記述子)= 各軸の座標分布を並べた軸別 Wasserstein 距離
# ═══════════════════════════════════════════════════════════════════════════
K_Q = 64


def null_signature(P):
    """正準化した点群の各軸の周辺分布を分位点 K_Q 個で表す(3*K_Q 次元)。

    周辺分布(x,y,z の値のヒストグラム相当)は物体の向きに強く依存する=回転不変でない。
    立方体を回すと角が別の軸へ伸び、各軸の分布が総入れ替わる → 同一形状でも遠くなる。
    """
    Q = normalize_cloud(P)
    xs = np.linspace(0.0, 1.0, K_Q)
    return np.stack([np.quantile(np.sort(Q[:, a]), xs) for a in range(3)], axis=0)


def null_distance(sig_a, sig_b):
    """軸別の1次元 Wasserstein 距離(=分位点関数の L1)の和。小さいほど同形状。"""
    return float(np.abs(sig_a - sig_b).mean(axis=1).sum())


def sh_distance_vol(vol_q, vol_db):
    """SH 記述子コサイン距離 (1 - 類似度)。match_sh_descriptor は 1=同形状。"""
    return 1.0 - X.match_sh_descriptor(vol_q, vol_db)


def nearest(dist_row):
    """{label: distance} から最小距離のラベルを返す。"""
    return min(dist_row, key=dist_row.get)


def main():
    labels = list(SHAPES)
    n_cls = len(labels)

    # --- 1) データベース(正準向き)を点群→ボクセル化。SH 記述子を1つ明示計算して形確認 ---
    db_vol, db_sig = {}, {}
    for i, name in enumerate(labels):
        rng = np.random.default_rng(1000 + i)      # クラスごと固定 seed
        P = SHAPES[name](N_PTS, rng)
        db_vol[name] = voxelize(P)
        db_sig[name] = null_signature(P)
    desc = X.sh_descriptor(db_vol["cube"], L=8, nradii=12)
    assert desc.shape == (12, 9), f"sh_descriptor 返り形が異常: {desc.shape}"
    print(f"点群 {N_PTS} 点/クラス → {GRID}^3 密度ボクセル → sh_descriptor")
    print(f"sh_descriptor(cube) 形 = {desc.shape} (半径 x 帯域L+1), "
          f"帯域エネルギー総和 = {float(desc.sum()):.4f}")
    print(f"クラス: {labels}")
    print("-" * 72)

    # --- 2) クエリ: 各クラスを別サンプル(別 seed)し直し、(a)回転なし (b)ランダム回転 ---
    ROT_PER_CLASS = 3
    sh_ok_rot = 0
    null_ok_rot = 0
    null_ok_norot = 0
    total = 0
    sh_same_max = 0.0      # SH: 回転クエリ vs 自クラスの距離の最大(小さいほど良い)
    sh_cross_min = 1e9     # SH: 回転クエリ vs 他クラスの距離の最小(大きいほど良い)

    for i, true_label in enumerate(labels):
        for j in range(ROT_PER_CLASS):
            total += 1
            qrng = np.random.default_rng(50_000 + 100 * i + j)   # クエリは別 seed
            Pq = SHAPES[true_label](N_PTS, qrng)                 # 別サンプル(素の一致でない)
            R = random_rotation(np.random.default_rng(9_000 + 100 * i + j))
            Pq_rot = Pq @ R.T                                    # 一様ランダム3D回転

            # (a) 回転なしクエリ: null がちゃんと引ける(=まともな記述子)ことの対照
            sig_q0 = null_signature(Pq)
            null0 = {name: null_distance(sig_q0, db_sig[name]) for name in labels}
            null_ok_norot += int(nearest(null0) == true_label)

            # (b) 回転ありクエリ: SH(回転不変) と null(非不変)を同条件で検索
            vol_q = voxelize(Pq_rot)
            sig_q = null_signature(Pq_rot)
            sh_d = {name: sh_distance_vol(vol_q, db_vol[name]) for name in labels}
            null_d = {name: null_distance(sig_q, db_sig[name]) for name in labels}
            sh_pick, null_pick = nearest(sh_d), nearest(null_d)
            sh_ok_rot += int(sh_pick == true_label)
            null_ok_rot += int(null_pick == true_label)

            sh_same_max = max(sh_same_max, sh_d[true_label])
            for other in labels:
                if other != true_label:
                    sh_cross_min = min(sh_cross_min, sh_d[other])

            if j == 0:   # 1本だけ距離表を表示(冗長回避)
                print(f"クエリ={true_label:8s} (回転)  "
                      f"SH最近傍={sh_pick:8s}"
                      f"{'[正]' if sh_pick == true_label else '[誤]'}  "
                      f"null最近傍={null_pick:8s}"
                      f"{'[正]' if null_pick == true_label else '[誤]'}")

    sh_acc = sh_ok_rot / total
    null_acc_rot = null_ok_rot / total
    null_acc_norot = null_ok_norot / total
    margin = sh_cross_min - sh_same_max
    print("-" * 72)
    print(f"SH   回転あり 検索正解率 : {sh_ok_rot}/{total} = {sh_acc:.2%}")
    print(f"null 回転なし 検索正解率 : {null_ok_norot}/{total} = {null_acc_norot:.2%} (対照)")
    print(f"null 回転あり 検索正解率 : {null_ok_rot}/{total} = {null_acc_rot:.2%}")
    print(f"SH 同形状距離の最大 : {sh_same_max:.4f} / 異形状距離の最小 : {sh_cross_min:.4f}")
    print(f"SH 分離マージン     : {margin:.4f} (>0 なら回転しても自クラスが最近傍)")

    # --- 3) GT 検証(beat-the-null) ---
    # (a) SH は回転クエリでほぼ全問正解(回転不変な検索が成立)。
    assert sh_acc >= 0.90, f"SH の回転あり正解率が低い: {sh_acc:.2%}"
    # (b) SH は同形状(回転)距離 < 異形状距離。マージン>0 = 判別的に分離。
    assert margin > 0.0, f"SH の同形状/異形状が分離できていない: margin={margin:.4f}"
    # (c) beat-the-null: SH の回転あり正解率が null の回転あり正解率を明確に上回る。
    assert sh_acc >= null_acc_rot + 0.30, \
        (f"SH が null を十分に上回っていない: SH={sh_acc:.2%} null={null_acc_rot:.2%}")
    # (d) 勝因は回転不変性: null は「回転なし」なら引けるのに「回転あり」で崩れる。
    assert null_acc_norot > null_acc_rot, \
        (f"null が回転で崩れていない(勝因が回転不変性でない疑い): "
         f"norot={null_acc_norot:.2%} rot={null_acc_rot:.2%}")

    print(f"PASS: SH 回転不変検索 {sh_ok_rot}/{total}={sh_acc:.0%}・分離マージン {margin:.3f}>0。"
          f"null は回転なし {null_acc_norot:.0%} → 回転あり {null_acc_rot:.0%} へ崩れ、"
          f"SH が +{(sh_acc - null_acc_rot):.0%} 上回る")


if __name__ == "__main__":
    main()
