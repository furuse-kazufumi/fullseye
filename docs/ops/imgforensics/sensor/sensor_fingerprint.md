---
op: sensor_fingerprint
dim: imgforensics
category: sensor
in: images
out: fingerprint
examples: [image_forensics_audit]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0  # fullseye lib version this note was generated for
---

# sensor_fingerprint — IMGFORENSICS `sensor` op

- **データ種**: `images` → `fingerprint`
- **呼び出し**: `import imgforensics; imgforensics.sensor_fingerprint(images, denoiser: 'str' = 'wiener', sigma: 'float' = 0.02, zero_mean: 'bool' = True) -> 'np.ndarray'` (または `opsimgforensics.get("sensor_fingerprint")`)

## 使い方

複数枚から **PRNU センサ指紋** K を最尤推定する(Chen et al. 2008)。

``K = Σ_i W_i I_i / Σ_i I_i²``(``W_i = I_i - denoise(I_i)``)。撮像モデル
``I = I⁰ + I⁰·K + Θ`` の下で、これが K の最尤推定量になる —— 明るい画素ほど
PRNU が強く出る(乗法的な欠陥だから)ので、**明るさで重み付けした平均**である。

返りは ``(H, W)`` の float64 で、``zero_mean=True``(既定)なら行・列平均を
抜いたうえで **標準偏差 1 に正規化**してある。正規化は :func:`fingerprint_correlate`
の PCE をスケール不変にするためで、指紋の絶対的な強さは
:func:`fingerprint_strength_map` が別に返す。

``images`` は同じ shape の 2 枚以上。**リサイズして揃えてはいけない** ——
PRNU は画素の物理位置そのものなので、内挿した瞬間に指紋は消える(shape 不一致は
:class:`ValueError`)。

枚数と分離度の実測(``tests/test_imgforensics.py::test_prnu_separates_two_sensors``、
128x128・PRNU 強度 3%・読み出し雑音 σ=0.01、既定 ``denoiser="wiener"``):

====== ======================== ================= =================
枚数   真の K との相関          同一センサの PCE  別センサの PCE
====== ======================== ================= =================
2      +0.727                   5295             16.5
4      +0.809                   6472             14.5
8      +0.859                   7246             13.1
16     +0.892                   7755             -12.3
====== ======================== ================= =================

**「真の K との相関」を測ることが重要**である。PCE だけを見ていると、
指紋がセンサのパターンをまったく捉えていなくても「分離しているように見える」
—— 実際この実装は一度その状態にあった(:func:`_wiener_denoise` の docstring)。
PCE は「同一センサで一貫して現れる何か」を測るので、それが PRNU である保証は
PCE 自体には無い。

``denoiser="wavelet"``(PyWavelets 必須)は同じ条件で相関 +0.745 〜 +0.901、
同一センサ PCE 6068 〜 8852 と一貫して強い。既定を ``"wiener"`` にしてあるのは
**optional 依存を必須にしないため**であって、精度で選んだのではない。

**これは合成雑音での値**であり、実カメラでは被写体の内容が残差に漏れるので
桁で小さくなる。この表は「実装が正しく動いている」ことの固定であって、
実運用のしきい値ではない。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [image_forensics_audit](../../../../examples/image_forensics_audit.py) — `py -3.11 examples/image_forensics_audit.py`

## 型が繋がる次の op(`fingerprint` を入力に取れる)

[fingerprint_correlate](fingerprint_correlate.md) · [fingerprint_strength_map](fingerprint_strength_map.md)

## 同カテゴリ(`sensor`)

[fingerprint_correlate](fingerprint_correlate.md) · [fingerprint_strength_map](fingerprint_strength_map.md)

---
*Provenance: imgforensics.py — IMGFORENSICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
