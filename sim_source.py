"""F4 sim-source アダプタ — 物理シミュが視覚 op に入力を供給する同一契約.

分業(honest, FullSense の核): **fullseye は物理をやらない**。RGB/depth/LiDAR/真値は
シミュ側(sim-source)が供給し、視覚 op(fullseye)がそれを計算する。sim-source は
OSS アダプタ(``oss_adapter.py``)と同じ F1〜F4 契約に従う: config オブジェクト + 動詞
メソッド + ``.backend`` / ``.available`` + 不在時は明示エラー(optional-extras)。

共通の動詞(要件 §5-F4):
  ``.intrinsics(cam)``   カメラ内部行列 K(GL 不要・fovy から算出)
  ``.rgb(cam)``          RGB フレーム(GL 描画)
  ``.depth(cam)``        メトリック深度(GL 描画)
  ``.point_cloud(cam)``  深度を逆投影した world 点群 → elevation_map 等の視覚 op が消費
  ``.ground_truth()``    真の body 姿勢(honest 評価の真値源・GL 不要)

MuJoCo は本環境で headless 描画が動く=実供給。Gazebo/IsaacSim は未接続の honest scaffold
(``.available=False``、動詞は「未接続」を明示 raise)。
"""
from __future__ import annotations

import numpy as np


class MuJoCo:
    """MuJoCo sim-source: RGB/深度を描画し、K を算出、真値姿勢を出し、深度を逆投影して
    world 点群にする(視覚 op が消費)。model は MjModel / .xml パス / XML 文字列を受ける。"""

    backend = "mujoco"
    available = True

    def __init__(self, model, data=None, width: int = 320, height: int = 240) -> None:
        import mujoco
        if isinstance(model, str):
            model = (mujoco.MjModel.from_xml_path(model) if model.strip().endswith(".xml")
                     else mujoco.MjModel.from_xml_string(model))
        self._m = model
        self._d = data if data is not None else mujoco.MjData(model)
        mujoco.mj_forward(self._m, self._d)
        self.width, self.height = int(width), int(height)
        self._renderer = None

    # -- カメラ列挙 / 解決 -------------------------------------------------
    def cameras(self) -> list:
        import mujoco
        names = [mujoco.mj_id2name(self._m, mujoco.mjtObj.mjOBJ_CAMERA, i)
                 for i in range(self._m.ncam)]
        return [n for n in names if n]

    def _cam_id(self, cam) -> int:
        import mujoco
        if isinstance(cam, int):
            return cam
        cid = mujoco.mj_name2id(self._m, mujoco.mjtObj.mjOBJ_CAMERA, cam)
        if cid < 0:
            raise ValueError(f"MuJoCo: camera {cam!r} が無い。候補: {self.cameras()}")
        return cid

    # -- GL 不要 -----------------------------------------------------------
    def intrinsics(self, cam=0) -> np.ndarray:
        """内部行列 K(fovy=垂直画角 + 解像度から。正方画素前提 fx=fy)。"""
        cid = self._cam_id(cam)
        fovy = float(self._m.cam_fovy[cid])
        H, W = self.height, self.width
        fy = 0.5 * H / np.tan(np.radians(fovy) / 2.0)
        return np.array([[fy, 0.0, W / 2.0], [0.0, fy, H / 2.0], [0.0, 0.0, 1.0]])

    def ground_truth(self) -> dict:
        """真の body 姿勢 {name: (pos(3,), quat(4,))}(honest 評価の真値源)。"""
        import mujoco
        out = {}
        for b in range(self._m.nbody):
            nm = mujoco.mj_id2name(self._m, mujoco.mjtObj.mjOBJ_BODY, b)
            if nm:
                out[nm] = (self._d.xpos[b].copy(), self._d.xquat[b].copy())
        return out

    # -- GL 描画 -----------------------------------------------------------
    def _rend(self):
        import mujoco
        if self._renderer is None:
            self._renderer = mujoco.Renderer(self._m, height=self.height, width=self.width)
        return self._renderer

    def rgb(self, cam=0) -> np.ndarray:
        r = self._rend()
        r.disable_depth_rendering()
        r.update_scene(self._d, camera=cam)
        return r.render()

    def depth(self, cam=0) -> np.ndarray:
        r = self._rend()
        r.enable_depth_rendering()
        r.update_scene(self._d, camera=cam)
        dep = r.render().copy()
        r.disable_depth_rendering()
        return dep

    def point_cloud(self, cam=0, stride: int = 2, max_range: float | None = None) -> np.ndarray:
        """深度を逆投影した world 点群 (N,3)。背景(遠クリップ面)は除外。
        視覚 op(``elevation_map`` 等)にそのまま渡せる = sim→vision の橋。"""
        dep = self.depth(cam)
        cid = self._cam_id(cam)
        K = self.intrinsics(cam)
        fx, fy, cx, cy = K[0, 0], K[1, 1], K[0, 2], K[1, 2]
        H, W = dep.shape
        vs, us = np.mgrid[0:H:stride, 0:W:stride]
        z = dep[::stride, ::stride]
        far = float(z.max())
        keep = z < (max_range if max_range is not None else far * 0.99)
        # カメラ座標(右 x, 上 y, 前 -z)へ逆投影
        X = (us - cx) * z / fx
        Y = -(vs - cy) * z / fy
        Z = -z
        cam_pts = np.stack([X, Y, Z], axis=-1)[keep]
        # world へ: cam_xmat 列 = カメラ軸の world 表現 → world = R @ p + pos
        R = self._d.cam_xmat[cid].reshape(3, 3)
        pos = self._d.cam_xpos[cid]
        return cam_pts @ R.T + pos


class _Scaffold:
    """未接続の sim-source(optional-extras の honest scaffold)。動詞は明示 raise。"""
    available = False

    def __init__(self, *a, **k) -> None:
        pass

    def _na(self, *a, **k):
        raise RuntimeError(f"{self.backend} sim-source は未接続(optional)。"
                           f"本環境では MuJoCo を使用。{self.backend} 接続は別途ブリッジが要る。")

    cameras = intrinsics = rgb = depth = point_cloud = ground_truth = _na


class Gazebo(_Scaffold):
    """Gazebo sim-source(未接続 scaffold)。gz-transport ブリッジで RGB/depth/真値を供給予定。"""
    backend = "gazebo"


class IsaacSim(_Scaffold):
    """Isaac Sim sim-source(未接続 scaffold)。omni.replicator ブリッジで供給予定。"""
    backend = "isaacsim"


# (namespace, name, class, render_hint) — 統一 registry(F2/F3)へ登録するエントリ
SOURCES = [
    ("sim", "MuJoCo", MuJoCo, "point_cloud"),
    ("sim", "Gazebo", Gazebo, "point_cloud"),
    ("sim", "IsaacSim", IsaacSim, "point_cloud"),
]


def backends() -> dict:
    """{name: {'backend':..., 'available':...}} — どの sim-source が実供給できるか。"""
    return {name: {"backend": cls.backend, "available": bool(cls.available)}
            for _, name, cls, _ in SOURCES}


if __name__ == "__main__":
    xml = ('<mujoco><worldbody><light pos="0 0 2"/>'
           '<geom type="box" size=".1 .1 .1" pos="0 0 .5"/>'
           '<camera name="c" pos="0 -1 .5" xyaxes="1 0 0 0 0 1"/></worldbody></mujoco>')
    s = MuJoCo(xml, width=160, height=120)
    print("cameras:", s.cameras(), "backend:", s.backend)
    print("K=\n", np.round(s.intrinsics("c"), 1))
    pc = s.point_cloud("c")
    print("point_cloud:", pc.shape, "centroid≈", np.round(pc.mean(0), 2), "(box at 0,0,0.5)")
    print("ground_truth keys:", list(s.ground_truth())[:4])
    print("backends:", backends())
