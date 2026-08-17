"""Fullseye sim ソースアダプタ — LiDAR 最小 spike(MuJoCo mj_ray 走査 → 点群 → pcseg).

先の要件(docs/UNIFIED_API_REQUIREMENTS.md §F4)で設計した sim ソースアダプタの
``sim.MuJoCo(xml).lidar(...)`` を、MuJoCo の ``mj_ray``(GL 不要の幾何レイキャスト)で
薄く実装する additive な spike(既存 op を一切変更しない・throwaway 可)。

  sensor → LiDAR 点群 → fullseye 知覚 op で「知覚ループ」を閉じる:
  points = sim.MuJoCo(SCENE).lidar(origin=(0,0,1.0))     # (N,3) world 点群
  ground_removed, _ = fs.remove_ground(points)            # 床を落とす
  clusters = fs.euclidean_clusters(ground_removed)        # 物体候補に分ける
  centroid = fs.centroid(ground_removed[clusters[i]])     # 各物体の重心 → 姿勢へ

★設計原則(先の議論と整合):
- LiDAR は物理エンジンから得る(sim=物理を担い、fullseye=その出力を視覚処理する分業)。
- MuJoCo native の ``mj_ray`` を走査パターンでループ=回転式多ビーム LiDAR を薄く自作
  (onocollo.mujoco の rangefinder ラッパは凍結ゆえ再利用せず、生 API で実装)。
- sim の距離は **ground-truth(完全値)**。ノイズ/強度/ドロップアウトは載せていない
  (honest 評価には真値がむしろ好都合。realistic 化は別レイヤの課題)。
- Qt 風: 名前空間 ``sim`` + 設定オブジェクト ``LidarPattern`` + 動詞メソッド ``.lidar()``。
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

import fullseye as fs

try:
    import mujoco
except ImportError as e:  # pragma: no cover - spike は mujoco 前提
    raise SystemExit("この spike は mujoco が要ります: py -3.11 -m pip install mujoco") from e


# 床 + 既知位置の 3 物体(box/sphere)を置いた自己完結シーン(外部アセット不要)。
SCENE = """
<mujoco model="lidar_spike">
  <worldbody>
    <geom name="floor" type="plane" size="0 0 0.1" pos="0 0 0"/>
    <geom name="box_a"    type="box"    size="0.25 0.25 0.25" pos="2.0  0.0 0.25"/>
    <geom name="box_b"    type="box"    size="0.20 0.20 0.30" pos="-1.5 1.0 0.30"/>
    <geom name="sphere_c" type="sphere" size="0.30"           pos="0.5 -2.0 0.30"/>
  </worldbody>
</mujoco>
"""
_OBJECT_GEOMS = ("box_a", "box_b", "sphere_c")   # 床以外=クラスタで見つけたい物体


# ── sim ソースアダプタ(名前空間 + 設定オブジェクト + 動詞メソッド)───────────── #
@dataclass
class LidarPattern:
    """回転式多ビーム LiDAR の走査パターン(Velodyne 風の水平×垂直グリッド)。"""

    h_res: int = 120                                   # 水平ビーム数(方位)
    v_res: int = 24                                    # 垂直チャンネル数(仰角)
    az_range: tuple[float, float] = (-math.pi, math.pi)          # 360°
    el_range: tuple[float, float] = (math.radians(-70.0), math.radians(8.0))  # 下向き〜わずか上
    max_range: float = 20.0

    def directions(self) -> np.ndarray:
        """(h_res*v_res, 3) の単位方向ベクトル群を返す(vec=[cosEl cosAz, cosEl sinAz, sinEl])。"""
        az = np.linspace(*self.az_range, self.h_res, endpoint=False)
        el = np.linspace(*self.el_range, self.v_res)
        A, E = np.meshgrid(az, el)
        A, E = A.ravel(), E.ravel()
        return np.column_stack([np.cos(E) * np.cos(A), np.cos(E) * np.sin(A), np.sin(E)])


@dataclass
class _SimMuJoCo:
    xml: str
    _m: mujoco.MjModel = field(init=False, repr=False)
    _d: mujoco.MjData = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._m = mujoco.MjModel.from_xml_string(self.xml)
        self._d = mujoco.MjData(self._m)
        mujoco.mj_forward(self._m, self._d)            # geom 世界姿勢を確定(レイキャスト前提)

    def step(self, n: int = 1) -> "_SimMuJoCo":
        for _ in range(n):
            mujoco.mj_step(self._m, self._d)
        return self

    def lidar(self, origin=(0.0, 0.0, 1.0), pattern: LidarPattern | None = None) -> np.ndarray:
        """LiDAR を 1 スキャンし、ヒット点の world 座標 (N,3) を返す(真値・ノイズ無し)。"""
        pat = pattern or LidarPattern()
        pnt = np.asarray(origin, dtype=np.float64)
        dirs = pat.directions()
        geomid = np.zeros(1, dtype=np.int32)
        hits = []
        for vec in dirs:
            dist = mujoco.mj_ray(self._m, self._d, pnt, vec, None, True, -1, geomid)
            if 0.0 <= dist <= pat.max_range and geomid[0] >= 0:
                hits.append(pnt + dist * vec)
        return np.asarray(hits, dtype=np.float64) if hits else np.empty((0, 3))

    def ground_truth(self) -> dict[str, np.ndarray]:
        """各 geom の world 重心位置(honest 評価の真値=クラスタ重心と突き合わせる)。"""
        out = {}
        for name in _OBJECT_GEOMS:
            gid = mujoco.mj_name2id(self._m, mujoco.mjtObj.mjOBJ_GEOM, name)
            out[name] = np.array(self._d.geom_xpos[gid], dtype=np.float64)
        return out


class sim:  # noqa: N801 — namespace module 風(unified_api_spike.py と同じ house style)
    MuJoCo = _SimMuJoCo


def _demo() -> None:
    scene = sim.MuJoCo(SCENE)

    print("== LiDAR 1 スキャン(mj_ray 走査・GL 不要)==")
    points = scene.lidar(origin=(0.0, 0.0, 1.0), pattern=LidarPattern(h_res=120, v_res=24))
    print(f"  sim.MuJoCo(SCENE).lidar() -> 点群 {points.shape}(120x24 ビーム中ヒット {len(points)})")

    print("\n== 知覚ループ: 床除去 → クラスタ → 重心 ==")
    ground_removed, ground_mask = fs.remove_ground(points, thresh=0.03)
    print(f"  fs.remove_ground()        -> 床 {int(ground_mask.sum())} 点除去 / 残 {len(ground_removed)}")
    clusters = fs.euclidean_clusters(ground_removed, tol=0.25, min_size=5)
    print(f"  fs.euclidean_clusters()   -> 物体候補 {len(clusters)} 個")

    gt = scene.ground_truth()
    print("\n== honest 評価: クラスタ重心 vs sim 真値(xy 平面で最近傍 geom に対応)==")
    gt_xy = {k: v[:2] for k, v in gt.items()}
    for i, idx in enumerate(clusters):
        c = fs.centroid(ground_removed[idx])
        # 最近傍の真値 geom を対応付け(xy)。LiDAR は見える面だけ当たるので z はズレる=正直に xy で。
        name = min(gt_xy, key=lambda k: np.linalg.norm(gt_xy[k] - c[:2]))
        err_xy = float(np.linalg.norm(gt_xy[name] - c[:2]))
        print(f"  cluster{i} 重心 xy=({c[0]:+.2f},{c[1]:+.2f}) n={len(idx):3d}"
              f" -> {name} 真値 xy=({gt[name][0]:+.2f},{gt[name][1]:+.2f}) 誤差 {err_xy:.3f} m")

    print("\n[spike OK] sim(物理)→ LiDAR 点群 → fullseye 知覚 op の分業ループが薄く載って動作")


if __name__ == "__main__":
    _demo()
