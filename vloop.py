"""H1 — 遅延つき視覚閉ループの台。高速ビジョン研究フェーズの全段階の前提。

正本 = ``docs/HIGHSPEED_VISION.md``。

## これは何か

MuJoCo を 1 ms 刻みで回しながら ``{描画 → 知覚 → 制御}`` を閉じる。要点は
**遅延を明示的なパイプライン段数として持つ** こと:

    n_sensor    露光と転送(この歩の画像は n_sensor 歩前のもの)
    n_compute   知覚アルゴリズムの実行時間
    n_act       指令が効くまでの遅れ

``timestep = 0.001`` なので **遅延のステップ数がそのままミリ秒**。

石川グループ研究室の高速ビジョンは「遅延を固定値として下げる工学」だった。
シミュレーションでは遅延が **独立変数** になるので、出せるのは点ではなく
**関数 error(latency)** になる。それがこの台の存在理由。

## 場面

上から見た 1 次元の追従課題。赤い球が x 軸上を勝手に動き、緑の板が
**画像だけを頼りに** その真下に付いていく。板の位置は位置アクチュエータで
駆動するので、閉ループには本物のアクチュエータ動特性が入る。

知覚 = 赤画素の重心(画像モーメントの 0 次と 1 次)。石川研の
「多点瞬時解析プロセッサ」が計算していた量そのもので、H2 でもこれを使う。

## 成立条件(これを満たさなければ台が壊れている)

    G1  遅延 0 で、何もしない場合の誤差より十分小さい(= 閉ループが効いている)
    G2  誤差が遅延に対して単調に増える(Spearman 相関 > 0.9)
    G3  遅延を上げると、何もしない場合の水準まで壊れる(測定範囲が足りている)
    G4  線形域の傾きが対象の平均速度に一致する(誤差 ≈ 速度 x 遅延)

G4 は「素朴な予測が実測に乗るか」の検算。乗れば台が正しいことの強い証拠になる。

    import vloop
    vloop.main()          # 掃引して表と関門判定を出す
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

try:
    import mujoco
    _HAVE_MUJOCO = True
except ImportError:                                    # optional-extras 契約
    _HAVE_MUJOCO = False

XML = """
<mujoco model="vloop">
  <option timestep="0.001"/>
  <worldbody>
    <light pos="0 0 3" dir="0 0 -1" diffuse="1 1 1"/>
    <geom name="floor" type="plane" size="1.5 1.5 .1" rgba=".12 .12 .15 1"/>
    <body name="target" pos="0 .35 .06">
      <joint name="tx" type="slide" axis="1 0 0"/>
      <geom type="sphere" size=".05" rgba="1 .15 .1 1"/>
    </body>
    <!-- 板の動特性: 質量 1.08 kg, kp 8000, damping 150
         -> 固有 13.7 Hz / 減衰比 0.81。目標の最高成分 1.9 Hz に対し 7 倍の余裕。
         kp 300 / damping 4 だと 2.65 Hz・減衰比 0.11 で目標と共振し、
         遅延 0 でも追従できなかった(実測 G1 不合格) -->
    <body name="tracker" pos="0 -.35 .06">
      <joint name="px" type="slide" axis="1 0 0" damping="150"/>
      <geom type="box" size=".09 .05 .03" rgba=".1 .9 .3 1"/>
    </body>
    <camera name="top" pos="0 0 1.4" euler="0 0 0" fovy="70"/>
  </worldbody>
  <actuator>
    <position joint="px" kp="8000" ctrlrange="-1 1"/>
  </actuator>
</mujoco>
"""


@dataclass(frozen=True)
class VLoopCfg:
    n_sensor: int = 0          # 露光 + 転送(歩 = ms)
    n_compute: int = 0         # 知覚の実行時間
    n_act: int = 0             # アクチュエータの遅れ
    res: int = 64              # 描画解像度(正方)
    steps: int = 3000          # 1 試行の長さ(ms)
    warmup_frac: float = 0.2   # 最初のこの割合は評価から外す(過渡)
    amp: float = 0.45          # 目標の振幅 [m]
    f1: float = 0.7            # 目標の運動 = 2 つの正弦の和 [Hz]
    f2: float = 1.9
    predict: bool = False      # 実効遅延ぶんの外挿で補償するか(H4 の前倒し)
    open_loop: bool = False    # 対照: 板を動かさない

    @property
    def latency(self) -> int:
        return self.n_sensor + self.n_compute + self.n_act


def available() -> bool:
    return _HAVE_MUJOCO


def target_x(t_ms: np.ndarray | float, c: VLoopCfg, phase: float = 0.0):
    """目標の軌道。正弦 2 本の和なので単純な外挿では当たらない。"""
    t = np.asarray(t_ms, dtype=float) * 1e-3
    return c.amp * (0.6 * np.sin(2 * np.pi * c.f1 * t + phase)
                    + 0.4 * np.sin(2 * np.pi * c.f2 * t + 1.7 * phase))


def target_speed(c: VLoopCfg, phase: float = 0.0) -> float:
    """平均 |速度| [m/s]。G4(誤差 ≈ 速度 x 遅延)の予測に使う。"""
    t = np.arange(c.steps, dtype=float)
    x = target_x(t, c, phase)
    return float(np.abs(np.diff(x)).mean() * 1000.0)


def _centroid_x(img: np.ndarray) -> float | None:
    """赤画素の重心の列位置。見つからなければ None(= 知覚の失敗)。"""
    r = img[:, :, 0].astype(np.int16)
    g = img[:, :, 1].astype(np.int16)
    b = img[:, :, 2].astype(np.int16)
    mask = (r > 110) & (r - g > 60) & (r - b > 60)
    m00 = float(mask.sum())
    if m00 < 3.0:
        return None
    cols = np.arange(img.shape[1], dtype=float)
    m10 = float((mask * cols[None, :]).sum())
    return m10 / m00


class VLoop:
    """遅延を持つ視覚閉ループ。1 回の run で誤差の時系列を返す。"""

    def __init__(self, cfg: VLoopCfg):
        if not _HAVE_MUJOCO:
            raise RuntimeError(
                "vloop は mujoco を要求する: pip install mujoco")
        self.c = cfg
        self.model = mujoco.MjModel.from_xml_string(XML)
        self.data = mujoco.MjData(self.model)
        self.renderer = mujoco.Renderer(self.model, cfg.res, cfg.res)
        self.tx = self.model.joint("tx").qposadr[0]
        self.px = self.model.joint("px").qposadr[0]
        self.pix_to_x = self._calibrate()

    # -- 画素 -> world の較正(2 点。カメラ内部行列を持ち出さない) --------
    def _calibrate(self):
        pts = []
        for x in (-0.5, 0.5):
            self.data.qpos[self.tx] = x
            mujoco.mj_forward(self.model, self.data)
            self.renderer.update_scene(self.data, camera="top")
            u = _centroid_x(self.renderer.render())
            if u is None:
                raise RuntimeError("較正に失敗: 目標が画像に写っていない")
            pts.append((u, x))
        (u0, x0), (u1, x1) = pts
        a = (x1 - x0) / (u1 - u0)
        return lambda u: x0 + a * (u - u0)

    def run(self, phase: float = 0.0, cfg: VLoopCfg | None = None) -> dict:
        c = cfg or self.c
        d, m = self.data, self.model
        mujoco.mj_resetData(m, d)

        # 遅延の実装 = 単純なリングバッファ 3 本
        img_delay = max(c.n_sensor, 0)
        meas_buf: list[float | None] = [None] * (c.n_compute + 1)
        cmd_buf: list[float] = [0.0] * (c.n_act + 1)
        frames: list[np.ndarray] = []

        err = np.zeros(c.steps)
        tgt = np.zeros(c.steps)
        trk = np.zeros(c.steps)
        miss = 0
        last_meas, last_t = 0.0, 0

        for k in range(c.steps):
            xt = float(target_x(k, c, phase))
            d.qpos[self.tx] = xt
            d.qvel[self.tx] = 0.0
            # qpos を書いたら前向き運動学を回してから描く。これを忘れると
            # 画像が 1 歩前の姿勢を映し、隠れた +1 ms の遅延になる(実測で発覚)
            mujoco.mj_forward(m, d)

            self.renderer.update_scene(d, camera="top")
            frames.append(self.renderer.render())
            if len(frames) > img_delay + 1:
                frames.pop(0)
            img = frames[0]              # 先頭 = img_delay 歩前のフレーム

            u = _centroid_x(img)
            if u is None:
                miss += 1
                meas = None
            else:
                meas = float(self.pix_to_x(u))
            meas_buf.append(meas)
            ready = meas_buf.pop(0)

            if ready is not None:
                if c.predict:                     # 実効遅延ぶん外挿する
                    dt = max(1, k - last_t)
                    v = (ready - last_meas) / dt
                    cmd = ready + v * c.latency
                else:
                    cmd = ready
                last_meas, last_t = ready, k
            else:
                cmd = cmd_buf[-1]
            cmd_buf.append(float(np.clip(cmd, -1.0, 1.0)))
            applied = cmd_buf.pop(0)

            d.ctrl[0] = 0.0 if c.open_loop else applied
            mujoco.mj_step(m, d)

            tgt[k] = xt
            trk[k] = float(d.qpos[self.px])
            err[k] = abs(trk[k] - xt)

        w = int(c.steps * c.warmup_frac)
        return {"rmse": float(np.sqrt((err[w:] ** 2).mean())),
                "max_err": float(err[w:].max()), "miss": miss,
                "err": err, "target": tgt, "tracker": trk,
                "latency": c.latency}


def sweep(latencies=(0, 1, 2, 4, 8, 16, 32, 64, 128), phases=(0.0, 0.9, 1.8),
          base: VLoopCfg | None = None, predict: bool = False) -> dict:
    """遅延を掃引する。遅延は n_compute に載せる(どの段でも効果は同じはず)。"""
    from dataclasses import replace
    base = base or VLoopCfg()
    loop = VLoop(base)                    # GL コンテキストは 1 つだけ作る
    null = [loop.run(ph, replace(base, open_loop=True))["rmse"] for ph in phases]
    rows = []
    for L in latencies:
        cfg = replace(base, n_compute=int(L), predict=predict)
        r = [loop.run(ph, cfg) for ph in phases]
        rows.append({"latency": int(L),
                     "rmse": float(np.mean([x["rmse"] for x in r])),
                     "max": float(np.mean([x["max_err"] for x in r])),
                     "miss": int(sum(x["miss"] for x in r))})
    return {"null": float(np.mean(null)), "rows": rows,
            "speed": float(np.mean([target_speed(base, p) for p in phases]))}


def stage_equivalence(base: VLoopCfg | None = None, L: int = 32,
                      phases=(0.0, 0.9, 1.8)) -> dict:
    """**検算**: 同じ遅延をどの段に載せても結果は同じか。

    sweep は遅延を n_compute にだけ載せている。「どの段でも同じはず」は
    推論であって測定ではないので、ここで確かめる。3 つが一致しなければ
    遅延の実装のどこかが非対称。
    """
    from dataclasses import replace
    base = base or VLoopCfg()
    loop = VLoop(base)
    out = {}
    for name, kw in (("n_sensor", {"n_sensor": L}),
                     ("n_compute", {"n_compute": L}),
                     ("n_act", {"n_act": L}),
                     ("三等分", {"n_sensor": L // 3, "n_compute": L // 3,
                                 "n_act": L - 2 * (L // 3)})):
        cfg = replace(base, **kw)
        out[name] = float(np.mean([loop.run(ph, cfg)["rmse"] for ph in phases]))
    return out


def gates(res: dict) -> list[tuple[str, bool, str]]:
    """成立条件の判定。台が壊れていないことの確認であって、成果ではない。"""
    rows, null, v = res["rows"], res["null"], res["speed"]
    e = np.array([r["rmse"] for r in rows], dtype=float)
    L = np.array([r["latency"] for r in rows], dtype=float)
    out = []

    out.append(("G1 遅延 0 で閉ループが効いている", bool(e[0] < 0.25 * null),
                f"rmse(0)={e[0]:.4f}  何もしない={null:.4f}  "
                f"比 {e[0] / null:.2f}(< 0.25 が合格)"))

    rk_e = np.argsort(np.argsort(e))
    rk_L = np.argsort(np.argsort(L))
    rho = float(np.corrcoef(rk_e, rk_L)[0, 1])
    out.append(("G2 誤差が遅延に対して単調に増える", bool(rho > 0.9),
                f"Spearman rho={rho:.3f}(> 0.9 が合格)"))

    out.append(("G3 大遅延で何もしない水準まで壊れる", bool(e[-1] > 0.7 * null),
                f"rmse({int(L[-1])}ms)={e[-1]:.4f}  何もしない={null:.4f}"))

    # 線形域(遅延 <= 32 ms)の傾きを平均速度と比べる
    sel = (L > 0) & (L <= 32)
    if sel.sum() >= 3:
        slope = float(np.polyfit(L[sel] * 1e-3, e[sel], 1)[0])
        ok = bool(0.3 * v <= slope <= 3.0 * v)
        out.append(("G4 傾き ≈ 対象の平均速度", ok,
                    f"傾き={slope:.3f} m/s  平均速度={v:.3f} m/s  "
                    f"比 {slope / v:.2f}(0.3〜3.0 が合格)"))
    return out


def main():
    if not available():
        print("mujoco が無い。pip install mujoco")
        return
    base = VLoopCfg()
    print("H1 — 遅延つき視覚閉ループの台")
    print(f"  timestep 1 ms なので遅延のステップ数 = ミリ秒")
    print(f"  解像度 {base.res}x{base.res} / 1 試行 {base.steps} ms / 位相 3 通り")

    res = sweep(base=base)
    print(f"\n  対象の平均速度 {res['speed']:.3f} m/s")
    print(f"  何もしない場合の誤差 {res['null']:.4f} m")
    print(f"\n  {'遅延 ms':>8}{'RMSE m':>10}{'最大 m':>10}{'見失い':>8}")
    for r in res["rows"]:
        print(f"  {r['latency']:>8}{r['rmse']:10.4f}{r['max']:10.4f}"
              f"{r['miss']:>8}")

    print("\n  関門")
    allok = True
    for name, ok, note in gates(res):
        allok &= ok
        print(f"   [{'合格' if ok else '不合格'}] {name}  —  {note}")
    print(f"\n  台の判定: {'成立。H2 へ進める' if allok else '**不成立**。先へ進まない'}")

    eq = stage_equivalence(base)
    v = list(eq.values())
    spread = (max(v) - min(v)) / max(np.mean(v), 1e-12)
    print("")
    print(f"  検算: 同じ 32 ms をどの段に載せても同じか"
          f"(ばらつき {spread * 100:.1f}%)")
    for k, x in eq.items():
        print(f"   {k:<10} rmse {x:.4f}")

    # 補償(実効遅延ぶんの外挿)を入れると境界がどれだけ動くか
    res2 = sweep(latencies=(0, 8, 16, 32, 64, 128), base=base, predict=True)
    print("\n  参考: 遅延ぶんを外挿で補償した場合(H4 の前倒し)")
    print(f"  {'遅延 ms':>8}{'補償なし':>12}{'補償あり':>12}")
    ref = {r["latency"]: r["rmse"] for r in res["rows"]}
    for r in res2["rows"]:
        a = ref.get(r["latency"])
        print(f"  {r['latency']:>8}{(a if a is not None else float('nan')):12.4f}"
              f"{r['rmse']:12.4f}")


if __name__ == "__main__":
    main()
