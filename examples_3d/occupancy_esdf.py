"""事例: 部屋の点群 → 3-D 占有格子 → ESDF → 任意点の障害物クリアランス照会.

現実の問題(平易に): 6-DoF アームや小型ドローンを部屋の中で動かすとき、経路上の
任意の点で「一番近い障害物まで何メートルあるか(クリアランス)」を連続値で知りたい。
ロボット半径以上のクリアランスがある点だけを通れば衝突しない。占有格子(0/1)は
「その一点が塞がっているか」しか答えず距離を持たないので、そこから距離場を作る。

方法(mapping op を連鎖):
  1. occupancy_grid : 部屋の点群(4 壁 + 既知位置の箱障害物)を 3-D 占有ボクセル(bool)へ。
  2. esdf          : 占有格子を Euclidean 符号付き距離場へ(外 + = 最近占有まで,
                     内 - = 最近自由まで)。← 1 の出力を入力に取る。
  3. query_distance: ESDF を任意の world 座標で三線形補間し、その点のクリアランスを得る。
                     ← 2 の出力を入力に取る。

真値チェック(GT): 箱と壁は軸並行なので、自由空間の照会点から最近接障害物までの距離を
  解析式で厳密に出せる。query_distance の返り値がこの解析クリアランスと 1 ボクセル以内で
  一致すれば合格(ボクセル境界の離散化誤差 ≒ 1 ボクセル)。

beat-the-null: 占有格子(0/1)そのものは連続クリアランスを持たない。自由ボクセルを引くと
  0(= 非占有)しか返らず、実際には障害物まで距離があるのに「クリアランス 0」と誤る
  (部屋スケールで外す)。ESDF への変換こそが 0/1 を使える連続距離に変える。同じ照会点で
  ESDF と null を比べ、ESDF が解析値に一致・null が大きく外すことを assert する。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

# occupancy.py はリポジトリ直下(この事例は examples_3d/ の下)。
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from occupancy import occupancy_grid, esdf, query_distance  # noqa: E402


def dist_point_box(p, lo, hi):
    """点 p と軸並行箱 [lo, hi] 表面の距離(符号なし・正)。

    外側なら箱表面までの Euclidean 距離、内側なら最近面までの距離を返す。
    """
    p = np.asarray(p, float)
    lo = np.asarray(lo, float)
    hi = np.asarray(hi, float)
    if np.all((p >= lo) & (p <= hi)):                     # 箱の内側 -> 最近面まで
        return float(np.min(np.concatenate([p - lo, hi - p])))
    outside = np.maximum(np.maximum(lo - p, p - hi), 0.0)  # 箱の外側 -> 表面まで
    return float(np.linalg.norm(outside))


def analytic_clearance(p, box_lo, box_hi, room):
    """自由空間点 p から占有集合(箱 + 4 壁)までの解析最近接距離."""
    (x0, x1), (y0, y1), (z0, z1) = room
    d_box = dist_point_box(p, box_lo, box_hi)
    # 4 壁 = x0, x1, y0, y1 の各平面(床・天井は無し = 開いた 4 壁)
    d_walls = min(p[0] - x0, x1 - p[0], p[1] - y0, y1 - p[1])
    return min(d_box, d_walls)


def build_room_cloud(room, box_lo, box_hi, spacing=0.1):
    """部屋(4 壁)+ 中の充実箱障害物を密にサンプルした点群 (N, 3) を作る.

    spacing はボクセル辺長より細かく取り、各占有ボクセルが確実に点を含むようにする。
    """
    (x0, x1), (y0, y1), (z0, z1) = room

    def ax(a, b):
        return np.arange(a, b + 1e-9, spacing)

    parts = []
    # 壁 x = x0, x = x1(y, z 全面)
    ys, zs = np.meshgrid(ax(y0, y1), ax(z0, z1), indexing="ij")
    for xv in (x0, x1):
        parts.append(np.column_stack(
            [np.full(ys.size, xv), ys.ravel(), zs.ravel()]))
    # 壁 y = y0, y = y1(x, z 全面)
    xs, zs2 = np.meshgrid(ax(x0, x1), ax(z0, z1), indexing="ij")
    for yv in (y0, y1):
        parts.append(np.column_stack(
            [xs.ravel(), np.full(xs.size, yv), zs2.ravel()]))
    # 充実箱障害物(体積を密に埋める)
    bx, by, bz = np.meshgrid(ax(box_lo[0], box_hi[0]),
                             ax(box_lo[1], box_hi[1]),
                             ax(box_lo[2], box_hi[2]), indexing="ij")
    parts.append(np.column_stack([bx.ravel(), by.ravel(), bz.ravel()]))
    return np.vstack(parts)


def main():
    # --- 部屋と格子の定義(等方立方ボクセル)---
    room = ((0.0, 10.0), (0.0, 10.0), (0.0, 10.0))         # 10 m 立方の部屋
    res = 50                                               # 各軸 50 ボクセル
    voxel = (room[0][1] - room[0][0]) / res                # ボクセル辺長 = 0.2 m
    box_lo, box_hi = (4.0, 4.0, 4.0), (6.0, 6.0, 6.0)      # 既知位置の箱障害物 [4,6]^3

    # --- 合成点群(既知境界): 4 壁 + 中央の箱 ---
    cloud = build_room_cloud(room, box_lo, box_hi, spacing=0.1)

    # === op 連鎖 ===
    # op1: 点群 -> 3-D 占有ボクセル(bool)
    occ = occupancy_grid(cloud, room, res)
    # op2: 占有 -> ESDF(op1 の出力を入力に取る)
    esdf_grid = esdf(occ, voxel_size=voxel)

    # --- 自由空間の照会点(すべてボクセル中心に載せて補間ノイズを排除)---
    # 中心線 y = z = 5.1 上で箱の -x 面へ、および箱の +z 面(天井方向)へ近づく点。
    free_pts = np.array([
        [3.5, 5.1, 5.1],    # 箱 -x 面(x=4)まで 0.5、壁は 3.5 以上 -> 箱が最近
        [2.5, 5.1, 5.1],    # 箱 -x 面まで 1.5、壁は 2.5 以上 -> 箱が最近
        [5.1, 5.1, 9.1],    # 箱 +z 面(z=6)まで 3.1、壁は 4.9 以上 -> 箱が最近
        [5.1, 5.1, 9.9],    # 箱 +z 面まで 3.9(部屋スケールの離隔)
    ])
    analytic = np.array(
        [analytic_clearance(p, box_lo, box_hi, room) for p in free_pts])

    # op3: ESDF を任意 world 座標で照会(op2 の出力を入力に取る)
    esdf_pred = query_distance(esdf_grid, room, res, free_pts, mode="trilinear")

    # --- null(ベースライン): esdf を飛ばし占有格子(0/1)を距離場代わりに引く ---
    # 自由ボクセルは占有 0 -> クリアランス 0 と誤る(連続距離を持てない)。
    null_pred = query_distance(occ.astype(np.float64), room, res,
                               free_pts, mode="nearest") * voxel

    esdf_err = np.abs(esdf_pred - analytic)
    null_err = np.abs(null_pred - analytic)
    tol = voxel                                            # GT 許容 = 1 ボクセル

    print(f"部屋           : {room[0][1]:.0f} m 立方 / res={res} / ボクセル={voxel:.2f} m")
    print(f"箱障害物       : x,y,z in [{box_lo[0]:.0f}, {box_hi[0]:.0f}] m")
    print(f"占有ボクセル数 : {int(occ.sum())} / {occ.size}")
    print("照会点            解析クリアランス   ESDF照会   誤差(m)   null照会   null誤差(m)")
    for p, a, e, ee, n, ne in zip(free_pts, analytic, esdf_pred,
                                  esdf_err, null_pred, null_err):
        print(f"  ({p[0]:.1f},{p[1]:.1f},{p[2]:.1f})   "
              f"{a:>10.2f}      {e:>7.2f}   {ee:>6.2f}   {n:>7.2f}   {ne:>8.2f}")

    print(f"ESDF 最大誤差  : {esdf_err.max():.3f} m  (許容 1 ボクセル = {tol:.3f} m)")
    print(f"null 最大誤差  : {null_err.max():.3f} m  (占有 0/1 は連続距離を持てない)")

    # --- GT 検証 ---
    # (1) ESDF 照会が解析クリアランスと 1 ボクセル以内で一致
    assert np.all(esdf_err <= tol + 1e-9), \
        f"ESDF が解析距離から 1 ボクセル超ずれ: {esdf_err} > {tol}"
    # (2) beat-the-null: 占有 0/1 のみは 1 ボクセルの壁を越えられず、ESDF が明確に上回る
    assert null_err.max() > tol, \
        f"null が偶然 1 ボクセル以内に収まった(想定外): {null_err.max()} <= {tol}"
    assert esdf_err.max() < null_err.max(), \
        f"ESDF が null を上回れていない: {esdf_err.max()} >= {null_err.max()}"

    # (3) 符号付きの固有価値: 箱内部の照会は負(最近自由まで)になる
    inside_pt = np.array([[5.1, 5.1, 5.1]])               # 箱の中心付近(占有)
    esdf_inside = float(query_distance(esdf_grid, room, res, inside_pt)[0])
    inside_face = dist_point_box(inside_pt[0], box_lo, box_hi)   # 最近面まで 0.9 m
    print(f"箱内部の照会   : ESDF={esdf_inside:.2f} m (符号 -, 最近面 解析 {inside_face:.2f} m)")
    assert esdf_inside < 0.0, \
        f"占有内部なのに ESDF が非負: {esdf_inside}"

    beat_ratio = null_err.max() / max(esdf_err.max(), 1e-9)
    print(f"PASS: query_distance が解析クリアランスと {esdf_err.max():.2f} m "
          f"(<= 1 ボクセル {tol:.2f} m)で一致し、占有 0/1 の null(最大誤差 "
          f"{null_err.max():.2f} m)を約 {beat_ratio:.0f} 倍上回った。ESDF は箱内部で負値も返す。")


if __name__ == "__main__":
    main()
