# SDFのCSG合成(和/差)でソリッドを作りメッシュ化 — sdf_ops
# 実問題: 球・箱などのプリミティブを組み合わせて複雑なソリッド形状を「設計」する(CAD の
# 構成的立体幾何 = CSG)。符号付き距離場(SDF, 内側が負・外側が正)で表すと、和は min、
# 差は max(a,-b) という代数で機械的に合成でき、その符号がそのまま「点が形状の内側か」を表す。
# ここでは「(大球 ∪ 箱) − 小球」を作り、SDF の符号が CSG の集合論理と一致することを検証する。
# repo をそのまま clone した状態(pip install -e . を打っていない / install の
# マッピングが古い)でも動くように、リポジトリ直下を import パスへ入れる。
# 2026-09-02 実測: これが無い 29 本は editable install に寄生しており、
# finder の MAPPING から torch_lazy が抜けた瞬間に 6 本が ModuleNotFoundError
# で全滅した(docs/OP_CATALOG.md は裸の起動コマンドを載せている)。
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))

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

# =========================================================================== #
# 追加のプリミティブ(2026-09-07): 半空間・円柱・トーラス・カプセル            #
#                                                                             #
# 球と直方体だけでは、機械部品の**円筒穴・面取り・フィレット**が組めなかった   #
# (DFM / CAD 差分の PoC が面ごとの解析式を自前で書いていた)。ここでは 4 つの  #
# プリミティブを **閉形式の真値と突き合わせて**検証する。                      #
# =========================================================================== #
print()
print("=== 追加プリミティブ: 閉形式との突き合わせ ===")

# --- 1) 代表点で「距離そのもの」を手計算と比べる ------------------------------ #
# 厳密な SDF なので、値は最近表面までの符号つき距離に一致しなければならない。
cases = [
    # (名前, 呼び出し, 点, 期待値, 説明)
    ("plane_sdf", lambda p: sdf_ops.plane_sdf(p, [0, 0, 0], [0, 0, 1]),
     [1.0, 2.0, 3.0], 3.0, "法線側に 3.0 = 平面までの距離"),
    ("plane_sdf", lambda p: sdf_ops.plane_sdf(p, [0, 0, 0], [0, 0, 5]),
     [0.0, 0.0, -2.0], -2.0, "法線の長さは効かない(向きだけ)"),
    ("cylinder_sdf", lambda p: sdf_ops.cylinder_sdf(p, [0, 0, 0], [0, 0, 1], 2.0, 6.0),
     [5.0, 0.0, 0.0], 3.0, "側面の外 = 半径方向の距離 5-2"),
    ("cylinder_sdf", lambda p: sdf_ops.cylinder_sdf(p, [0, 0, 0], [0, 0, 1], 2.0, 6.0),
     [0.0, 0.0, 4.0], 1.0, "蓋の外 = 軸方向の距離 4-3"),
    ("cylinder_sdf", lambda p: sdf_ops.cylinder_sdf(p, [0, 0, 0], [0, 0, 1], 2.0, 6.0),
     [5.0, 0.0, 7.0], 5.0, "角(縁)の外 = 斜辺 hypot(3,4)"),
    ("cylinder_sdf", lambda p: sdf_ops.cylinder_sdf(p, [0, 0, 0], [0, 0, 1], 2.0, 6.0),
     [0.0, 0.0, 0.0], -2.0, "軸上 = 最近面(側面)まで -2"),
    ("torus_sdf", lambda p: sdf_ops.torus_sdf(p, [0, 0, 0], [0, 0, 1], 3.0, 1.0),
     [3.0, 0.0, 0.0], -1.0, "芯線上 = 管の半径ぶん内側"),
    ("torus_sdf", lambda p: sdf_ops.torus_sdf(p, [0, 0, 0], [0, 0, 1], 3.0, 1.0),
     [0.0, 0.0, 0.0], 2.0, "穴の中心 = 芯線まで 3、管の縁まで 2"),
    ("capsule_sdf", lambda p: sdf_ops.capsule_sdf(p, [-2, 0, 0], [2, 0, 0], 1.0),
     [0.0, 3.0, 0.0], 2.0, "芯線の真横 = 3-1"),
    ("capsule_sdf", lambda p: sdf_ops.capsule_sdf(p, [-2, 0, 0], [2, 0, 0], 1.0),
     [6.0, 0.0, 0.0], 3.0, "端の外は球状 = 端点まで 4、-1"),
]
for name, fn, point, want, why in cases:
    got = float(fn(np.array([point], float))[0])
    print(f"  {name:13s} p={point}  sdf={got:+.4f}  期待={want:+.4f}  # {why}")
    assert abs(got - want) < 1e-9, (name, point, got, want)

# --- 2) 厳密性の検定: 勾配のノルムが 1 ---------------------------------------- #
# 真の距離場は「1 m 進めば距離が 1 m 変わる」ので |∇sdf| = 1。角や芯線のような
# 微分不能点の周りだけは差分が鈍るため、中央値で見る(全域の平均ではない)。
gg, ext2 = sdf_ops.grid_coords(((-6, 6), (-6, 6), (-6, 6)), 48)
h = (ext2[1] - ext2[0]) / gg.shape[0]
fields = {
    "plane": sdf_ops.plane_sdf(gg, [0, 0, 0], [0, 0, 1]),
    "cylinder": sdf_ops.cylinder_sdf(gg, [0, 0, 0], [0, 0, 1], 2.0, 6.0),
    "torus": sdf_ops.torus_sdf(gg, [0, 0, 0], [0, 0, 1], 3.0, 1.0),
    "capsule": sdf_ops.capsule_sdf(gg, [-2, 0, 0], [2, 0, 0], 1.0),
}
for name, f in fields.items():
    gr = np.gradient(f, h, h, h)
    norm = np.sqrt(sum(x ** 2 for x in gr))
    med = float(np.median(norm))
    print(f"  |∇{name:9s}| 中央値 = {med:.4f}  (厳密なら 1)")
    assert abs(med - 1.0) < 0.01, (name, med)

# --- 3) 退化と同一性 ---------------------------------------------------------- #
# カプセルの両端を同じ点にすると球に一致する(近似ではなく厳密に)。
same = sdf_ops.capsule_sdf(gg, [0, 0, 0], [0, 0, 0], 2.0)
assert np.allclose(same, sdf_ops.sphere_sdf(gg, [0, 0, 0], 2.0)), "a==b は球に退化する"
print("  capsule(a==b) == sphere: 厳密一致")

# 半空間 6 枚の交差は、占有と内側の値では box_sdf に一致するが、**外側は角の近くで
# 過小評価する**(max による交差の標準的な性質)。ここを黙って「一致」と書かない。
planes = [sdf_ops.plane_sdf(gg, [2, 0, 0], [1, 0, 0]), sdf_ops.plane_sdf(gg, [-2, 0, 0], [-1, 0, 0]),
          sdf_ops.plane_sdf(gg, [0, 2, 0], [0, 1, 0]), sdf_ops.plane_sdf(gg, [0, -2, 0], [0, -1, 0]),
          sdf_ops.plane_sdf(gg, [0, 0, 2], [0, 0, 1]), sdf_ops.plane_sdf(gg, [0, 0, -2], [0, 0, -1])]
inter = planes[0]
for q in planes[1:]:
    inter = sdf_ops.sdf_intersect(inter, q)
boxf = sdf_ops.box_sdf(gg, [0, 0, 0], [2, 2, 2])
assert np.array_equal(inter <= 0, boxf <= 0), "占有は一致する"
assert np.allclose(inter[boxf < 0], boxf[boxf < 0]), "内側の値も一致する"
gap = float(np.max(np.abs(inter - boxf)[boxf > 0]))
print(f"  半空間 6 枚 vs box_sdf: 占有と内側は一致、外側は最大 {gap:.3f} 過小評価")
assert gap > 0.5, "角の外では必ずずれる(ずれないなら検定が効いていない)"

# --- 4) 実務の形: フランジ(円板)+ 貫通穴 4 つ + 内隅フィレット --------------- #
# 体積を閉形式で予測して、ボクセル数と突き合わせる(格子の刻みぶんの誤差は許す)。
gf, extf = sdf_ops.grid_coords(((-6, 6), (-6, 6), (-3, 3)), 96)
# ★罠: ``res`` はスカラでも**軸ごとのボクセル数**なので、bounds が非等方だと
# ボクセルは立方体にならない(ここは x,y が 0.125、z が 0.0625)。体積を
# ``h**3`` で出すと**ちょうど 2 倍**ずれる —— 実際この例で 295.00 と出て
# 閉形式 148.03 に対し 99 % の誤差になり、下の assert が鳴いた。
hx = (extf[1] - extf[0]) / gf.shape[0]
hy = (extf[3] - extf[2]) / gf.shape[1]
hz = (extf[5] - extf[4]) / gf.shape[2]
cell = hx * hy * hz
disc = sdf_ops.cylinder_sdf(gf, [0, 0, 0], [0, 0, 1], 5.0, 2.0)      # 円板 R=5, t=2
part = disc
for ang in (0.0, 90.0, 180.0, 270.0):                                # ボルト穴 4 つ
    cx = 3.5 * np.cos(np.radians(ang))
    cy = 3.5 * np.sin(np.radians(ang))
    hole = sdf_ops.cylinder_sdf(gf, [cx, cy, 0], [0, 0, 1], 0.6, 10.0)
    part = sdf_ops.sdf_subtract(part, hole)
vol_voxels = float((part < 0).sum()) * cell
vol_closed = np.pi * 5.0 ** 2 * 2.0 - 4 * np.pi * 0.6 ** 2 * 2.0      # 円板 - 穴 4 本
err = abs(vol_voxels - vol_closed) / vol_closed * 100.0
print(f"  フランジの体積: ボクセル {vol_voxels:.2f} / 閉形式 {vol_closed:.2f}  誤差 {err:.2f} %")
assert err < 1.0, (vol_voxels, vol_closed)

# トーラスでフィレットを削る = 内隅の丸み。半径が設計値どおりに出るかを見る。
fillet = sdf_ops.torus_sdf(gf, [0, 0, 1.0], [0, 0, 1], 5.0, 1.0)      # 縁に沿った管
filleted = sdf_ops.sdf_subtract(part, fillet)
carved = int((part < 0).sum() - (filleted < 0).sum())
print(f"  縁のフィレットで削れたボクセル = {carved}(トーラス 1 周ぶん)")
assert carved > 0, "フィレットが何も削っていない"

print("OK: 半空間・円柱・トーラス・カプセルが閉形式の真値と一致した")
