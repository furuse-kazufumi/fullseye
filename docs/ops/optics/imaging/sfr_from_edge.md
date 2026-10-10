---
op: sfr_from_edge
dim: optics
category: imaging
in: table
out: pairs
examples: [poc_veiling_glare]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# sfr_from_edge — OPTICS `imaging` op

- **データ種**: `table` → `pairs`
- **呼び出し**: `import fullseye as fs; fs.ledger.sfr_from_edge(esf, window, *, correction, ends=1.0, apodize='none')` (実装を直接呼ぶなら `import edgesfr; edgesfr.sfr_from_edge(esf, window, *, correction, ends=1.0, apodize='none')`、台帳から引くなら `opsoptics.get("sfr_from_edge")`)

## 使い方

ESF から SFR(エッジから測る MTF)を出す。

*esf* は :func:`edge_spread` の返り値(辞書)か、1 px 刻みの 1-D 配列(``oversample`` = 1 とみなす)。
エッジの中心(差分の絶対値の最大)から ±*window* px を切り、両端 *ends* px の平均を黒/白の基準に正規化し、
前進差分で LSF にしてフーリエ変換の絶対値を DC で割る。

*window*(必須、px): 切り出す半幅。★迷光(裾)は窓の外に居るので、窓を狭くするほど SFR から見えなくなる。
*correction*(必須): 標本化が作る sinc の割り戻し。
  ``"none"`` — 割り戻さない(離散の段差を離散の PSF で畳んだ像なら前進差分が離散 LSF そのもので、これが正しい)。
  ``"derivative"`` — 連続のエッジを点で標本した ESF の前進差分は幅 Δ の箱で LSF を均すので sinc(fΔ) で割る。
  ``"derivative+bin"`` — :func:`edge_spread` の升(幅 Δ)の平均がもう 1 つの箱なので sinc(fΔ)² で割る。
*apodize*: ``"none"`` か ``"hamming"``(ISO 12233:2017 の LSF の窓)。

返り値 ``(n, 2)`` の pairs: 列 0 = 周波数 [cyc/px] (エッジに垂直)、列 1 = SFR。0 〜 min(1.0, 0.5/Δ) cyc/px
(升の刻み Δ の Nyquist まで、ただし画素の Nyquist の 2 倍 = 1 cyc/px で打ち切る。その先は sinc の割り戻しが暴れる)。

**Raises** ``ValueError``: esf が空・NaN / window が正の有限でない・ESF の長さを越える / ends が window 以上 /
correction・apodize が一覧に無い / 黒と白の基準が等しい(エッジが無い)。

## ファミリ共通の入力契約(fail-closed)

optics の全 op は入力を検証してから計算する(黙って通さない):

- **単位は引数名に埋め込む** — `_mm` / `_um` / `_deg` / `_mrad`。mm と µm の取り違えは crash ではなく「もっともらしく間違った答え」なので、名前で防ぐ。大きさから単位を推測する処理は一切しない。
- **文字列は `ValueError`** — `float('50')` は成功してしまうため、未パースの設定値が長さとして通り抜ける(実測: `thin_lens('50', '200')` がもっともらしい 66.667 mm を返していた)。bool も `True == 1` の暗黙昇格として拒否。
- **complex / masked array は `ValueError`**(実数枠のみ。虚部の無言切り捨て・マスク剥がしを拒否)。**NaN/Inf は全入力で `ValueError`**。
- **0 除算とその親戚を名指しで拒否**: 焦点距離 0・曲率半径 0・屈折率 <= 0・不透明な開口(全 0 なので正規化が 0/0)・総和 <= 0 の PSF・S0 = 0 の Stokes ベクトル・物体が前側焦点にある(像が無限遠)。
- **非有限を返すのは 2 op だけ、しかも契約として明記**: `depth_of_field` の過焦点距離以遠の `far_mm = inf`(それが過焦点距離の定義)と `gaussian_beam` のウエストでの `wavefront_radius_mm = inf`(平面波面の曲率半径)。どちらも有限の相棒(`far_is_infinite` / `curvature_per_mm`)を併せて返す。**それ以外の無言 NaN/Inf は内部で検出して `ValueError`** —「float64 が溢れた」と「答えが無限大」は別の主張なので、後者の顔で前者を返さない。
- **サイズ上限**: 生成格子は `optics.MAX_GRID`(4096)、供給された場/PSF/開口は `optics.MAX_FIELD_ELEMENTS`(2^24)、ABCD 素子列は `optics.MAX_SYSTEM_ELEMENTS`(1024)、Zernike は `MAX_ZERNIKE_TERMS`(512)/ `MAX_ZERNIKE_ORDER`(40)/ `MAX_ZERNIKE_BASIS`(2^25)。小さな引数から巨大な内部確保が起きる経路(実測: n_max=40 × 4096² で 108 GB)を fail-closed で塞ぐ。
- **物理的に不可能な状態も拒否**: 偏光度 > 1 の Stokes ベクトル、負の透過率、負の強度、n-|m| が奇数などの不正な Zernike 添字。

## 詳しい使い方ガイド

- [optics_imaging ファミリ ガイド](../guides/optics_imaging.md)

## 背景知識ガイド(この op の手前にある物理・規約)

- [measurement_uncertainty](../../math/guides/measurement_uncertainty.md) — 計測の不確かさと校正の知識 — 「測れている」を主張するために
- [mv_cameras](../guides/mv_cameras.md) — 産業用カメラメーカー（センサとの紐付け・ラインスキャン / TDI）
- [virtual_machine_vision](../guides/virtual_machine_vision.md) — 仮想マシンビジョン — パラメータの洗い出しとオブジェクト模型

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_veiling_glare](../../../../examples/poc_veiling_glare.py) — `py -3.11 examples/poc_veiling_glare.py`

## 型が繋がる次の op(`pairs` を入力に取れる)

[mtf50](mtf50.md)

## 同カテゴリ(`imaging`)

[psf_to_mtf](psf_to_mtf.md) · [mtf_diffraction](mtf_diffraction.md) · [wavefront_stats](wavefront_stats.md) · [edge_spread](edge_spread.md) · [mtf50](mtf50.md) · [veiling_glare_index](veiling_glare_index.md)

---
*Provenance: edgesfr.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
