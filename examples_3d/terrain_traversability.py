"""事例: 屋外地形の走行可能性マップ(ロボットのナビ地図)を作る (mapping).

移動ロボットは、深度センサから起こした点群を 2.5-D の標高マップ(heightmap)に落とし、
そこから「足を置ける / 越えられる場所」を走行可能性(traversability)マスクとして判定する。
急な段差や壁を非走行可能と正しく弾けないと、ロボットはそこへ突っ込む。ここでは terrain op
(elevation_map / traversability)だけで、平坦地・緩やかなスロープ・急な段差(壁)からなる
地形の点群 → 標高マップ → 走行可能性マップを作り、段差を「置いた既知の位置」と突き合わせる。

検証(GT): 地形は自分で組んだので真値がわかる。
  * 平坦地(x∈[0.5,1.5])と緩スロープ(x∈[2.5,3.5]・勾配0.10 ≒ 5.7度)のセルは走行可能。
  * 急な段差(x∈[4.0,4.4)・高低差0.5m ≒ 勾配1.25)のセルは非走行可能。段差の位置は既知。
  beat-null: 「全部走行可能」の定数マップ(や、壁を無視する巨大 max_step)は段差セルを
  1 つも弾けない。実 op は段差セルを非走行可能(検出率≒1.0)にし、両 null(検出率0)を
  上回る=判別的。閾値(max_step / max_slope)を外すと壁が消える、という因果も同時に示す。
"""
import numpy as np
import terrain  # elevation_map / traversability(numpy+scipy のみ)

RNG = np.random.RandomState(42)             # 決定的(計測ノイズの種)

# --- パラメータ --------------------------------------------------------------
CELL = 0.1                                   # 標高マップの解像度 [m/セル]
BOUNDS = (0.0, 6.0, 0.0, 3.0)               # x∈[0,6]m, y∈[0,3]m の地形
MAX_STEP, MAX_SLOPE, WINDOW = 0.1, 0.6, 3   # 段差<=0.1m / 勾配<=0.6 / 3x3 近傍

# --- 地形の高さプロファイル z=f(x)(y には依存しない=断面を y 方向へ押し出し)---
RAMP_X0 = 2.0                                # 緩スロープ開始
WALL_X0, WALL_X1 = 4.0, 4.4                 # 急な段差(壁)区間 [4.0,4.4)
RAMP_SLOPE = 0.10                            # スロープ勾配 0.10(緩やか=走行可能側)
WALL_RISE = 0.5                             # 段差の高さ 0.5m(急峻=非走行可能側)
Z_RAMP_TOP = RAMP_SLOPE * (WALL_X0 - RAMP_X0)      # スロープ頂上 = 0.2
Z_TOP = Z_RAMP_TOP + WALL_RISE                     # 段上の平坦地 = 0.7
WALL_SLOPE = WALL_RISE / (WALL_X1 - WALL_X0)       # 壁の勾配 = 1.25(>> 0.6)


def height(x):
    """x [m] → 高さ z [m]。平坦地→緩スロープ→急な段差→段上の平坦地。"""
    x = np.asarray(x, float)
    z = np.zeros_like(x)                                        # 平坦地: z=0
    ramp = (x >= RAMP_X0) & (x < WALL_X0)                       # 緩スロープ
    z[ramp] = RAMP_SLOPE * (x[ramp] - RAMP_X0)
    wall = (x >= WALL_X0) & (x < WALL_X1)                       # 急な段差(壁)
    z[wall] = Z_RAMP_TOP + WALL_SLOPE * (x[wall] - WALL_X0)
    z[x >= WALL_X1] = Z_TOP                                     # 段上の平坦地
    return z


# --- 1) 地形表面の点群を作る(密にサンプルし微小な計測ノイズを載せる)-----------
xs = np.arange(0.0, 6.0 + 1e-9, 0.02)       # x を 0.02m 刻み(各セルに複数点)
ys = np.arange(0.0, 3.0 + 1e-9, 0.05)       # y を 0.05m 刻み
gx, gy = np.meshgrid(xs, ys)
gx, gy = gx.ravel(), gy.ravel()
gz = height(gx) + RNG.normal(0.0, 0.003, gx.shape)             # 決定的な微小ノイズ
points = np.stack([gx, gy, gz], axis=1)                        # (N,3) 点群

# --- 2) 点群 → 標高マップ → 走行可能性マップ(実 op)---------------------------
grid, extent = terrain.elevation_map(points, cell=CELL, agg="max", bounds=BOUNDS)
trav = terrain.traversability(grid, cell=CELL, max_step=MAX_STEP,
                              max_slope=MAX_SLOPE, window=WINDOW)

# --- 3) 既知の地形位置(GT)を列で切り出す ------------------------------------
ncol = grid.shape[1]
col_x = (np.arange(ncol) + 0.5) * CELL       # 各列中心の x 座標
flat_cols = np.where((col_x >= 0.5) & (col_x <= 1.5))[0]        # 平坦地(走行可)
ramp_cols = np.where((col_x >= 2.5) & (col_x <= 3.5))[0]        # 緩スロープ(走行可)
wall_cols = np.where((col_x >= WALL_X0) & (col_x < WALL_X1))[0]  # 段差(非走行可)

flat_trav_rate = trav[:, flat_cols].mean()
ramp_trav_rate = trav[:, ramp_cols].mean()
wall_block_rate = (~trav[:, wall_cols]).mean()    # 段差を非走行可能と弾いた率

print(f"標高マップ                : grid{grid.shape}  高さ [{np.nanmin(grid):.3f},{np.nanmax(grid):.3f}] m")
print(f"段差(壁)の列              : {wall_cols.tolist()}  x∈[{WALL_X0},{WALL_X1}) 高低差{WALL_RISE}m")
print(f"平坦地セル 走行可能率      : {flat_trav_rate:.3f}  (GT=1.0)")
print(f"緩スロープセル 走行可能率  : {ramp_trav_rate:.3f}  (GT=1.0)")
print(f"段差セル 非走行可能率      : {wall_block_rate:.3f}  (GT=1.0 で弾く)")

# --- 4) beat-null: 「全部走行可能」定数 / 壁を無視する巨大 max_step ------------
trav_null_all = np.ones_like(trav)            # null-A: 何でも走行可能とみなす
trav_null_huge = terrain.traversability(       # null-B: 閾値を外して壁を無視
    grid, cell=CELL, max_step=5.0, max_slope=50.0, window=WINDOW)

real_step_flag = (~trav[:, wall_cols]).mean()          # 実 op が段差を弾く率
null_all_step_flag = (~trav_null_all[:, wall_cols]).mean()   # null-A の段差検出率(=0)
null_huge_step_flag = (~trav_null_huge[:, wall_cols]).mean()  # null-B の段差検出率(≒0)

# GT ラベルに対する精度(平坦+緩スロープ=走行可, 段差=非走行可)
gt_trav_cols = np.concatenate([flat_cols, ramp_cols])
acc_real = np.concatenate([trav[:, gt_trav_cols].ravel(),
                           (~trav[:, wall_cols]).ravel()]).mean()
acc_null_all = np.concatenate([trav_null_all[:, gt_trav_cols].ravel(),
                               (~trav_null_all[:, wall_cols]).ravel()]).mean()

print(f"beat-null 段差検出率      : 実 op {real_step_flag:.3f} / null-A(全可) "
      f"{null_all_step_flag:.3f} / null-B(巨大max_step) {null_huge_step_flag:.3f}")
print(f"GT 全体精度               : 実 op {acc_real:.3f} / null-A {acc_null_all:.3f}")

# ═══ GT 検証(段差の位置は既知。緩い assert でなく既知位置と突き合わせる)═══
# (a) 平坦地・緩スロープは全セル走行可能(勾配 0.10・段差 ~0 は閾値内)
assert flat_trav_rate == 1.0, f"平坦地が走行可能でない: {flat_trav_rate:.3f}"
assert ramp_trav_rate == 1.0, f"緩スロープが走行可能でない: {ramp_trav_rate:.3f}"
# (b) 急な段差は全セル非走行可能(高低差 0.5m・勾配 1.25 が閾値超)
assert wall_block_rate == 1.0, f"段差を弾けていない: {wall_block_rate:.3f}"
# beat-null: 実 op は段差セルを弾く(>0.95)が、両 null は 1 つも弾けない
assert real_step_flag > 0.95, f"実 op の段差検出率が低い: {real_step_flag:.3f}"
assert null_all_step_flag == 0.0, f"null-A(全可)が段差を弾いた: {null_all_step_flag:.3f}"
assert null_huge_step_flag < 0.05, f"null-B(巨大max_step)が段差を弾いた: {null_huge_step_flag:.3f}"
assert real_step_flag > null_all_step_flag, "実 op が全可 null を段差で上回っていない"
assert real_step_flag > null_huge_step_flag, "実 op が巨大max_step null を段差で上回っていない"
# GT 全体精度でも実 op が null を上回る
assert acc_real > acc_null_all, f"GT 精度で null を上回っていない: {acc_real:.3f} vs {acc_null_all:.3f}"

print(f"PASS: 平坦/緩スロープ 走行可能率 {flat_trav_rate:.2f}/{ramp_trav_rate:.2f}・"
      f"段差(x∈[{WALL_X0},{WALL_X1}) 高低差{WALL_RISE}m)非走行可能率 {wall_block_rate:.2f}。"
      f"段差検出率 実 op {real_step_flag:.2f} > null-A {null_all_step_flag:.2f}/"
      f"null-B {null_huge_step_flag:.2f}、GT精度 {acc_real:.2f} vs null {acc_null_all:.2f}")
