# SDFのCSG合成(和/差)でソリッドを作りメッシュ化 — sdf_ops
# 実問題: 球・箱などのプリミティブを組み合わせて複雑なソリッド形状を「設計」する(CAD の
# 構成的立体幾何 = CSG)。符号付き距離場(SDF, 内側が負・外側が正)で表すと、和は min、
# 差は max(a,-b) という代数で機械的に合成でき、その符号がそのまま「点が形状の内側か」を表す。
# ここでは「(大球 ∪ 箱) − 小球」を作り、SDF の符号が CSG の集合論理と一致することを検証する。
import numpy as np
import sdf_ops

# --- プリミティブの定義 ---
A_C, A_R = np.array([0.0, 0.0, 0.0]), 2.0        # 大球 A: 原点中心・半径2
B_C, B_HE = np.array([2.0, 0.0, 0.0]), np.array([1.0, 1.0, 1.0])  # 箱 B: 中心(2,0,0)・半辺1 → x∈[1,3]
C_C, C_R = np.array([0.0, 0.0, 0.0]), 0.8        # 小球 C: 原点中心・半径0.8(くり抜く穴)

# 評価用グリッド(ボクセル中心座標)。bounds は全形状を余裕で含む。
coords, extent = sdf_ops.grid_coords([[-3, 4], [-3, 3], [-3, 3]], 96)

# --- 各プリミティブの SDF をグリッド上で評価 ---
a = sdf_ops.sphere_sdf(coords, A_C, A_R)          # 大球
b = sdf_ops.box_sdf(coords, B_C, B_HE)            # 箱
c = sdf_ops.sphere_sdf(coords, C_C, C_R)          # 小球

# --- CSG 合成: solid = (A ∪ B) − C ---
u = sdf_ops.sdf_union(a, b)                        # A∪B = min(a,b)
solid = sdf_ops.sdf_subtract(u, c)                # (A∪B)\C = max(u, -c)

# --- GT: 集合論理を独立に計算(SDF を使わず membership を直接判定) ---
in_a = np.linalg.norm(coords - A_C, axis=-1) <= A_R
in_b = np.all(np.abs(coords - B_C) <= B_HE, axis=-1)
in_c = np.linalg.norm(coords - C_C, axis=-1) <= C_R
gt_inside = (in_a | in_b) & ~in_c                 # (A∪B) から C をくり抜いた真の内側

# --- 検証1: SDF の符号(内側<0)が CSG 論理と一致 ---
# min/max 合成はゼロ等値面を厳密に与えるので、境界(|solid|<~半ボクセル)を除き符号は厳密一致。
sdf_inside = solid < 0.0
voxel = (extent[1] - extent[0]) / coords.shape[0]  # 1 ボクセルの一辺長
margin = 0.5 * voxel                               # 境界セルは判定が割れて当然なので除外
comfortable = np.abs(solid) > margin               # 境界から十分離れたセルだけ厳密比較
mism = int(np.sum(sdf_inside[comfortable] != gt_inside[comfortable]))
print(f"grid={coords.shape[:3]}  interior voxels: A={int(in_a.sum())} B={int(in_b.sum())} "
      f"C={int(in_c.sum())}  solid={int(sdf_inside.sum())}")
print(f"sign vs CSG-logic mismatches (away from surface) = {mism}")
assert mism == 0, f"SDF sign must match CSG set-membership, got {mism} mismatches"

# --- 検証2: 手計算した代表点で符号を明示確認 ---
# (点, 期待: 内側=True/外側=False, 説明)
probes = [
    ([0.0, 0.0, 0.0], False, "原点=小球Cの中でくり抜かれ外側"),
    ([1.5, 0.0, 0.0], True,  "大球A内かつC外=残る"),
    ([2.8, 0.0, 0.0], True,  "箱Bだけの張り出し(A外)=残る"),
    ([0.0, 0.0, 5.0], False, "全形状の外"),
    ([0.0, 1.5, 0.0], True,  "大球A内・箱外・C外=残る"),
]
for p, want_inside, why in probes:
    p = np.array([p], float)
    sa = sdf_ops.sphere_sdf(p, A_C, A_R)
    sb = sdf_ops.box_sdf(p, B_C, B_HE)
    sc = sdf_ops.sphere_sdf(p, C_C, C_R)
    s = sdf_ops.sdf_subtract(sdf_ops.sdf_union(sa, sb), sc)[0]
    inside = s < 0.0
    print(f"  p={p[0]}  solid_sdf={s:+.4f}  inside={inside}  expect={want_inside}  # {why}")
    assert inside == want_inside, (p, s, want_inside)

# --- 検証3: 差(subtract)が実際に体積を削っている & ゼロ等値面が存在する ---
n_union = int((u < 0).sum())
n_solid = int((solid < 0).sum())
assert n_solid < n_union, "小球のくり抜きで内側ボクセルが減るはず"
assert n_solid > 0, "ソリッドは空でない"
# marching_cubes(skimage 依存=本環境の制約で不可)の代わりに、x 方向の符号反転数で
# ゼロ等値面が非空(=メッシュ化すれば頂点>0)であることを numpy だけで確認。
sign_flips = int(np.sum(np.diff(np.signbit(solid), axis=0) != 0))
print(f"union interior={n_union}  solid interior={n_solid}  "
      f"carved={n_union - n_solid}  zero-crossing edges(x)={sign_flips}")
assert sign_flips > 0, "ゼロ等値面(形状の表面)が存在する"
print("OK: (球∪箱−小球) の SDF 符号が CSG 集合論理と厳密一致し、表面も非空")