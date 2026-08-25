"""H5 — 動的プロジェクションマッピング。動く物体に模様を貼り続ける。

正本 = ``docs/HIGHSPEED_VISION.md`` §4 H5。

## シミュレーションでやる利点

**投影機の光学モデルが要らない。** 投影とは「物体表面のどこに何を描くか」なので、
シミュレーションでは物体の姿勢を推定して、その姿勢で模様の座標を写すだけでよい。
実機の VarioLight / Lumipen が解いていた光学・機械の問題を全部飛ばして、
**遅延の効果だけ** を純粋に測れる。

## 場面

板が画面内を滑りながら **回る**(並進 + 面内回転)。系は板の姿勢を画像から推定し、
板の局所座標で定義された模様を画像座標へ写す = 投影する。

姿勢の推定は **画像モーメント**:
  0 次 = 面積 / 1 次 = 重心 / 2 次 = 傾き(共分散行列の主軸)
H2 の追跡と同じ道具立て。石川研の「多点瞬時解析プロセッサ」が計算していた量。

## 事前登録した予測

- **ズレ ≈ 速度 x 遅延**。H1 で追従誤差について確認した関係が、投影でも成り立つはず
- **回転の寄与は中心から遠いほど大きい**。並進のズレは模様全体で一定だが、
  回転のズレは半径に比例する。したがって **大きな模様ほど不利**
- 予測補償(実効遅延ぶんの外挿)は H1 と同様、ある遅延までは効いてそれ以降で崩れる
- 外れる可能性: 2 次モーメントによる傾き推定が雑音に弱く、遅延より推定誤差が支配する。
  その場合は遅延の効果が見えないので、推定を先に直す

    import projmap
    projmap.main()
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

try:
    import mujoco
    _HAVE = True
except ImportError:
    _HAVE = False

XML = """
<mujoco model="projmap">
  <compiler angle="radian"/>
  <option timestep="0.001" gravity="0 0 0"/>
  <visual><global offwidth="512" offheight="512"/></visual>
  <worldbody>
    <light pos="0 -1 2" dir="0 .4 -1" diffuse="1 1 1"/>
    <geom name="back" type="box" pos="0 .3 .3" size="2 .02 1.2"
          rgba=".07 .07 .09 1"/>
    <body name="plate" pos="0 0 .30">
      <joint name="px" type="slide" axis="1 0 0"/>
      <joint name="pz" type="slide" axis="0 0 1"/>
      <joint name="ry" type="hinge" axis="0 1 0"/>
      <geom type="box" size=".16 .012 .10" rgba=".92 .90 .86 1"/>
    </body>
    <camera name="cam" pos="0 -1.05 .30" euler="1.5708 0 0" fovy="40"/>
  </worldbody>
</mujoco>
"""


@dataclass(frozen=True)
class PMCfg:
    res: int = 256
    steps: int = 2500
    latency: int = 0           # 合計遅延 [ms = steps]
    ax: float = 0.28           # 並進の振幅 [m]
    az: float = 0.10
    fx: float = 0.55           # 並進の周波数 [Hz]
    fz: float = 0.90
    fr: float = 0.42           # 回転の周波数 [Hz]
    amp_r: float = 0.55        # 回転の振幅 [rad]
    pattern_r: float = 0.075   # 模様の半径 [m]。回転のズレはこれに比例するはず
    predict: bool = False
    warmup: float = 0.2


def available() -> bool:
    return _HAVE


def pattern_local(c: PMCfg) -> np.ndarray:
    """板の局所座標で定義した模様。中心 + 半径 r の 8 点。"""
    th = np.arange(8) * (np.pi / 4)
    pts = [(0.0, 0.0)]
    pts += [(c.pattern_r * np.cos(t), c.pattern_r * np.sin(t)) for t in th]
    return np.array(pts)


def true_pose(k: int, c: PMCfg):
    t = k * 1e-3
    return (c.ax * np.sin(2 * np.pi * c.fx * t),
            c.az * np.sin(2 * np.pi * c.fz * t + 1.1),
            c.amp_r * np.sin(2 * np.pi * c.fr * t + 0.4))


def _mask(img):
    return img.astype(np.int16).sum(2) > 480      # 明るい板だけ


def moments_pose(img):
    """0 次・1 次・2 次モーメントから (重心, 傾き) を出す。"""
    m = _mask(img)
    m00 = float(m.sum())
    if m00 < 40:
        return None
    ys, xs = np.nonzero(m)
    cy, cx = ys.mean(), xs.mean()
    dy, dx = ys - cy, xs - cx
    cxx = float((dx * dx).mean())
    cyy = float((dy * dy).mean())
    cxy = float((dx * dy).mean())
    # 共分散行列の主軸。長辺の向きが板の x 軸
    th = 0.5 * np.arctan2(2 * cxy, cxx - cyy)
    return cy, cx, th, m00


class ProjMap:
    def __init__(self, cfg: PMCfg):
        if not _HAVE:
            raise RuntimeError("mujoco が要る")
        self.c = cfg
        self.model = mujoco.MjModel.from_xml_string(XML)
        self.data = mujoco.MjData(self.model)
        self.renderer = mujoco.Renderer(self.model, cfg.res, cfg.res)
        self.q = [self.model.joint(n).qposadr[0] for n in ("px", "pz", "ry")]
        self.scale = self._calibrate()          # px / m

    def _set(self, x, z, r):
        self.data.qpos[self.q[0]] = x
        self.data.qpos[self.q[1]] = z
        self.data.qpos[self.q[2]] = r
        mujoco.mj_forward(self.model, self.data)

    def _render(self):
        self.renderer.update_scene(self.data, camera="cam")
        return self.renderer.render()

    def _calibrate(self) -> float:
        """px / m。2 点の重心のずれから求める。"""
        self._set(-0.2, 0.0, 0.0)
        a = moments_pose(self._render())
        self._set(0.2, 0.0, 0.0)
        b = moments_pose(self._render())
        return abs(b[1] - a[1]) / 0.4

    def place(self, pose, pts_local):
        """計測した姿勢 (cy, cx, th) で模様を画像座標へ写す。

        **真値も投影もこの同じ関数を通す。** 最初は真値を世界座標から別式で
        作っていたが、回転の符号規約が食い違い、遅延 0 でもズレ 77.85 mm と出た。
        同じ関数を通せば規約の食い違いは原理的に起きず、**遅延だけの効果** が残る。
        """
        cy, cx, th = pose
        cA, sA = np.cos(th), np.sin(th)
        w = pts_local @ np.array([[cA, -sA], [sA, cA]]).T
        return np.column_stack([cy + w[:, 1] * self.scale,
                                cx + w[:, 0] * self.scale])

    def run(self, cfg: PMCfg | None = None, frames_out=None) -> dict:
        c = cfg or self.c
        pts = pattern_local(c)

        buf: list = [None] * (c.latency + 1)
        err = np.zeros(c.steps)
        err_t = np.zeros(c.steps)
        err_r = np.zeros(c.steps)
        prev, prev_k = None, 0
        for k in range(c.steps):
            x, z, r = true_pose(k, c)
            self._set(x, z, r)
            img = self._render()
            est = moments_pose(img)
            buf.append(None if est is None else (est[0], est[1], est[2]))
            seen = buf.pop(0)
            if seen is None:
                continue
            cy_s, cx_s, th_s = seen
            if c.predict and prev is not None:
                dt = max(1, k - prev_k)
                cy_s = cy_s + (cy_s - prev[0]) / dt * c.latency
                cx_s = cx_s + (cx_s - prev[1]) / dt * c.latency
                dth = np.arctan2(np.sin(th_s - prev[2]), np.cos(th_s - prev[2]))
                th_s = th_s + dth / dt * c.latency
            prev, prev_k = seen, k

            proj = self.place((cy_s, cx_s, th_s), pts)      # 遅れた計測で投影
            truth = self.place((est[0], est[1], est[2]), pts)  # 今の計測 = 本来
            d = np.linalg.norm(proj - truth, axis=1)
            err[k] = float(np.sqrt((d ** 2).mean())) / self.scale * 1000
            err_t[k] = float(d[0]) / self.scale * 1000        # 中心 = 並進のズレ
            err_r[k] = float(np.sqrt((d[1:] ** 2).mean())) / self.scale * 1000
            if frames_out is not None and k % 12 == 0:
                frames_out.append((img.copy(), proj.copy(), truth.copy()))
        w0 = int(c.steps * c.warmup)
        return {"rmse": float(np.sqrt((err[w0:] ** 2).mean())),
                "trans": float(np.sqrt((err_t[w0:] ** 2).mean())),
                "ring": float(np.sqrt((err_r[w0:] ** 2).mean())),
                "max": float(err[w0:].max())}


def mean_speed(c: PMCfg) -> tuple[float, float]:
    """並進の平均速さ [m/s] と回転の平均角速度 [rad/s]。"""
    t = np.arange(c.steps) * 1e-3
    x = c.ax * np.sin(2 * np.pi * c.fx * t)
    z = c.az * np.sin(2 * np.pi * c.fz * t + 1.1)
    r = c.amp_r * np.sin(2 * np.pi * c.fr * t + 0.4)
    v = np.hypot(np.diff(x), np.diff(z)).mean() * 1000
    w = np.abs(np.diff(r)).mean() * 1000
    return float(v), float(w)


def save_gif(path: str, cfg: PMCfg, n: int = 60):
    """投影が遅れる様子を GIF に。緑 = 投影した点、赤 = 本来あるべき点。"""
    from PIL import Image, ImageDraw
    pm = ProjMap(cfg)
    fr: list = []
    pm.run(cfg, frames_out=fr)
    fr = fr[len(fr) // 3:len(fr) // 3 + n]
    ims = []
    for img, proj, truth in fr:
        im = Image.fromarray(img).resize((512, 512), Image.NEAREST)
        d = ImageDraw.Draw(im)
        s = 512 / img.shape[0]
        for (v, u) in truth:
            d.ellipse([u * s - 5, v * s - 5, u * s + 5, v * s + 5],
                      outline=(255, 70, 60), width=2)
        for (v, u) in proj:
            d.ellipse([u * s - 3, v * s - 3, u * s + 3, v * s + 3],
                      fill=(60, 230, 90))
        d.text((8, 8), f"latency {cfg.latency} ms", fill=(255, 255, 255))
        ims.append(im)
    ims[0].save(path, save_all=True, append_images=ims[1:], duration=60, loop=0)
    return path


def main():
    if not available():
        print("mujoco が無い")
        return
    from dataclasses import replace
    base = PMCfg()
    pm = ProjMap(base)
    v, w = mean_speed(base)
    print("H5 — 動的プロジェクションマッピング")
    print(f"  板: 並進 {v:.3f} m/s / 回転 {w:.3f} rad/s / 模様の半径 "
          f"{base.pattern_r * 1000:.0f} mm / 倍率 {pm.scale:.1f} px/m")
    print(f"\n  {'遅延 ms':>8}{'ズレ mm':>10}{'中心 mm':>10}{'外周 mm':>10}"
          f"{'予測 v*L mm':>13}")
    for L in (0, 2, 4, 8, 16, 32, 64):
        r = pm.run(replace(base, latency=L))
        print(f"  {L:>8}{r['rmse']:10.2f}{r['trans']:10.2f}{r['ring']:10.2f}"
              f"{v * L:13.2f}", flush=True)

    print(f"\n  模様の大きさを変える(回転の寄与は半径に比例するはず / 遅延 16 ms)")
    print(f"  {'模様半径 mm':>12}{'ズレ mm':>10}{'中心 mm':>10}{'外周 mm':>10}")
    for pr in (0.02, 0.05, 0.075, 0.10):
        r = pm.run(replace(base, latency=16, pattern_r=pr))
        print(f"  {pr * 1000:12.0f}{r['rmse']:10.2f}{r['trans']:10.2f}"
              f"{r['ring']:10.2f}", flush=True)

    print(f"\n  予測補償を入れる")
    print(f"  {'遅延 ms':>8}{'補償なし':>12}{'補償あり':>12}")
    for L in (0, 8, 16, 32, 64):
        a = pm.run(replace(base, latency=L))["rmse"]
        b = pm.run(replace(base, latency=L, predict=True))["rmse"]
        print(f"  {L:>8}{a:12.2f}{b:12.2f}", flush=True)


if __name__ == "__main__":
    main()
