---
title: バイアル回転停止後の異物検査
applies_to: [pharma]
---

# バイアル回転停止後の異物検査

`vial_spin_stop_sequence` は、停止後に指数減衰する軸対称の旋回流と、Stokes
抗力領域の沈降・浮上を合成する。返る真値には投影座標、径、密度、物体種別、
各フレームの可視性が入る。`track_moving_particles` は画像列を時間中央値から
差し引き、動く候補と静止傷を別々に表へ出す。上向きの移動軌跡は気泡と表示する。

これは CFD、屈折補正済みレンダラ、USP <1790> の適格性手順ではない。孤立した
小球、低 Reynolds 数、既知の粘度を前提とする。壁は位置を幾何学的に反射して
容器外への脱出を防ぐだけであり、壁面近傍の抗力補正、気泡変形、凝集、実ガラスの
屈折・散乱は含まない。実機画像で真値照合する前に合否根拠へ使ってはいけない。

```python
from vialops import vial_spin_stop_sequence, track_moving_particles

frames, truth = vial_spin_stop_sequence(
    particle_diameter_um=90, particle_contrast=0.065,
    illumination="back", seed=42,
)
tracks = track_moving_particles(frames, threshold=0.014)
```

検出性能は同じ試行で調整と評価を混ぜず、保持した hit/miss を
`pod_hitmiss_fit` へ、良品の false call を `proportion_interval` へ渡す。
実行例は `examples/poc_vial_particle_pod.py` である。
