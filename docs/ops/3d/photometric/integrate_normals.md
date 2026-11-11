---
op: integrate_normals
dim: 3d
category: photometric
in: normalmap
out: image2d
gpu: なし
examples: [photometric_stereo]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.0.0  # fullseye lib version this note was generated for
---

# integrate_normals — 3D `photometric` op

- **データ種**: `normalmap` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.integrate_normals(normals, mask=None)` (実装を直接呼ぶなら `import photometric; photometric.integrate_normals(normals, mask=None)`、台帳から引くなら `ops3d.get("integrate_normals")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

法線場 → 高さ場 z を Frankot-Chellappa 積分。→ z HxW(定数分の自由度あり・平均0基準)。

手順: 法線 ``(H,W,3)`` を勾配 ``p = -nx/nz``、``q = -ny/nz`` に直し(``|nz| < 1e-6`` の
画素は nz を ±1e-6 に置き換えて零割を避ける)、FFT 領域で最小二乗解
``Z(wx,wy) = (-j·wx·P - j·wy·Q) / (wx² + wy²)`` を求め(直流成分は 0)、逆変換して
平均を 0 に引く。``mask`` (bool HxW) を与えると mask 外の勾配を 0 にしてから積分する
(その領域は平坦として扱われる)。返り値は float64 の ``(H,W)``。
注意点:
- 周期境界を仮定するため、画像の上下・左右がつながるように端が歪む(全体の傾きは下の★で戻す)。
- 絶対高さは決まらない(平均 0)。格子間隔 1 画素で積分するので ``z`` も画素単位の
  高さになり、実寸には画素ピッチを掛ける。
- ``nz ≈ 0``(輪郭付近・視線に平行な面)は勾配が発散し、波打ちを周囲へ広げる。
  ``mask`` で除くか法線を事前に平滑する。
``surface_normals`` が逆変換で、``photometric_stereo`` の法線をここへ渡すと形状(高さ場)が得られる。
空の入力(``normals`` が 0 要素)は ValueError。

★全体の傾き(2026-11-09): 周期境界の Frankot-Chellappa は勾配の平均(直流)を 0 に落とし、
傾いた平面を水平に戻していた(傾き 0.2 px/px → 復元 0.0000、rms 5.5 px)。積分の後に平均の
勾配の一次の項 ``mean(p)·(x − x̄) + mean(q)·(y − ȳ)`` を足し戻す(平均は ``mask`` 外の 0 も含む
格子全体)。傾いた平面は厳密に戻り、平均の勾配が 0 の面(マスクした球など)は丸め屑しか動かない。
素の周期解が要るときは :func:`integrate_gradients`。
★足し戻す傾きは**平均**なので外れ値に弱い(独立レビュー 2026-11-09): 平らな面に、同じ向きに大きく
傾いた法線(nz 0.002、1e-3 の切りは通る)が 20 画素あるだけで rms 誤差 10.7 → 27.9 px(2.6 倍悪化)。
輪郭の片側に並ぶ斜めの法線は実データで普通に出るので、``mask`` で外してから渡す。中央値などの
頑健な推定に替えないのは、段差の壁のように「少数の大きな勾配」が正しい傾きを担う面で傾きを失うため。
もう 1 つの限界: 傾きは**測れた法線**の平均で、照度差ステレオが撮れない段差の壁などは入らない ——
段差のある部品では足し戻した傾きが真値の平均勾配と違う(3-D 方式比べの PoC で −0.066〜−0.084
vs 真値 +0.0125 px/px)。
★入力の門: ``(H,W,3)`` 以外・非有限の法線(NaN 1 画素で FFT が全画素を NaN にしていた)は
ValueError。``|nz| < 1e-3``(勾配が 1000 を超える、輪郭・視線に平行な面)の画素は勾配を 0 に
して積分から外し、件数を RuntimeWarning で知らせる(nz=0 の 1 画素が高さを 2.3e5 px 振っていた)。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [photometric_stereo](../../../../examples_3d/photometric_stereo.py) — `py -3.11 examples_3d/photometric_stereo.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[fuse_to_voxel](../fusion/fuse_to_voxel.md) · [fit_poly_surface](../surface_fit/fit_poly_surface.md) · [eval_poly_surface](../surface_fit/eval_poly_surface.md) · [surface_form_error](../surface_fit/surface_form_error.md) · [background_flatten](../surface_fit/background_flatten.md) · [polar_unwrap](../curvilinear/polar_unwrap.md) · [fit_zernike](../curvilinear/fit_zernike.md) · [matcap_shade](../render/matcap_shade.md)

## 同カテゴリ(`photometric`)

[photometric_stereo](photometric_stereo.md) · [surface_normals](surface_normals.md) · [render_lambertian](render_lambertian.md)

---
*Provenance: photometric.py — 3D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
