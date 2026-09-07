---
op: match_logpolar_z
dim: 3d
category: match_pose
in: voxel × voxel
out: rot_scale
gpu: true
examples: [shape_desc_pose]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# match_logpolar_z — 3D `match_pose` op

- **データ種**: `voxel × voxel` → `rot_scale`
- **呼び出し**: `import fullseye as fs; fs.ledger.match_logpolar_z(a, b, device='cpu', project='mip', nt=360, nr=192)` (実装を直接呼ぶなら `import match3d; match3d.match_logpolar_z(a, b, device='cpu', project='mip', nt=360, nr=192)`、台帳から引くなら `ops3d.get("match_logpolar_z")`)
- **GPU**: この op は GPU 経路あり(`device="cuda"`)

## 使い方

log-polar × 位相相関(Fourier-Mellin)で **z 軸回転 + 等方スケール**を復元。

構造=voxel × 手法=Fourier-Mellin。PCA が点対応を要すのに対し、これはテンプレ/対応不要で
回転(z 軸)とスケールを同時推定する唯一の列。核心: z 投影(MIP)を取ると z 軸回転=面内回転・
等方スケール=面内スケールに落ち、確立された 2D Fourier-Mellin(|FFT|→高域強調→log-polar→
位相相関)が使える。返り値 (angle_deg, scale)。

honest な限界(**coarse 推定器**、下流で NCC/ICP 精緻化前提): |回転|≲40° で誤差 ~2-5°。
|FFT| の 180° 対称により ±45°/±90° 近傍は別名化して外し得る。スケールは中央ローブ偏りで
~10% 過小に出る。full-whitening はこの投影の非シフト DC プラトーでゼロロックするため、
plain 相関 + rho-Hann 窓 + 放物線サブピクセルを用いる。

引数: ``a``, ``b`` は 3-D volume(同形でなくてもよいが、投影の縦横比が違うと log-polar の
対応が崩れる)。``project="mip"`` で軸 0 の最大値投影、それ以外は軸 0 の総和投影。``nt``/``nr``
は log-polar の角度・半径サンプル数(角度分解能 180°/nt)。
返り値 ``(angle_deg, scale)``: ``b`` が ``a`` を軸 0 まわりに ``angle_deg`` 回して ``scale``
倍したものと推定する(``b ≈ zoom(rotate(a, angle_deg, axes=(1,2)), scale)``、回転の向きは
``scipy.ndimage.rotate`` と同じ)。角度は ±90° の範囲で別名化する。
後段: ``refine_rotation_z(scene=b, template=a, init_angle_deg=angle_deg)`` で追い込み →
``match_phase_3d`` で並進。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [shape_desc_pose](../../../../examples_3d/shape_desc_pose.py) — `py -3.11 examples_3d/shape_desc_pose.py`

## 型が繋がる次の op(`rot_scale` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md)

## 同カテゴリ(`match_pose`)

[match_phase_3d](match_phase_3d.md) · [match_pca](match_pca.md) · [moment_axes](moment_axes.md)

---
*Provenance: match3d.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
