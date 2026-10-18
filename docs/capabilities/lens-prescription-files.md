---
id: lens-prescription-files
title: 光学設計ファイル(.zmx の逐次処方を読む・書く・分類する)
title_en: Lens design files (read, write and triage sequential .zmx prescriptions)
category: 光と色
ops: [lens_file_read, lens_file_system, lens_file_write, lens_file_report]
examples: [poc_lens_file_roundtrip]
version: 0.6.1
inputs: [table]
pipeline: [lens_file_read, lens_file_system, paraxial_trace, spot_stats, lens_file_write]
alternatives: [lens_file_report, read_glass_catalog_agf, lens_system, optimize_lens, lens_section_drawing]
limits: 座標変換面(傾き・偏心・折り返し)は非共軸の追跡器へ読む(SCBD・物体空間を動かす先頭の変換・OBNA・像高の視野は拒否)。理想レンズ・トーリック・奇数次非球面は拒否。ケラレ係数・曲がった像面・多構成・温度は allow_partial のときだけ近似として読む。ソルブは保存値で読む。カタログに無い硝材は拒否(.agf を置く)。
calibration: 長さは mm に換算、波長は µm、視野は度(無限遠)か mm(有限の物体)。画素校正は不要。
---

# 光学設計ファイル(.zmx の逐次処方を読む・書く・分類する)

## できること

市販の逐次光線追跡の設計ソフトが保存する処方のテキスト(`.zmx`)を、`lens_file_read` がそのまま `raytrace.lens_system` の処方にします。別の模型を作らないので、実光線(`spot_stats` / `ray_fan`)・Seidel 和(`seidel_coefficients`)・波面と PSF(`opd_map` / `psf_from_opd`)・色収差(`chromatic_shift`)・公差(`tolerance_analysis`)・最適化(`optimize_lens`)・断面図(`lens_section_drawing`)がそのまま使えます。視野と波長はファイルの並びのまま持ち、`lens_file_system` で 1 つ選んだ処方にします。直した処方は `lens_file_write` が同じ形式で書き戻し(視野・波長・まだ有効なソルブを保つ)、`lens_file_report` は読まずに全キーワードを「読む / 無視(理由つき)/ 扱えない」に分けます。硝材は材料表か、手元の `.agf`(`glass_dir` か環境変数 `FULLSEYE_GLASS_DIR`、`read_glass_catalog_agf` が読む)を名前の完全一致で引きます。

座標変換面(`TYPE COORDBRK`: 傾き・偏心・折り返し鏡・傾いた平板)を含むファイルは、`raytrace.lens_system` でなく `raytrace3d.noncoaxial_system` の break 要素へ写ります(`p["noncoaxial"]` が True、`lens_file_system` は視野 (x, y) ごとの `noncoaxial_system` を返し、`noncoaxial_spot` / `noncoaxial_trace` などがそのまま使えます)。順序フラグ(先に偏心か先に傾けるか)、鏡の後の符号の反転(ファイルは座標系を返さず負の厚みを使う)、直前の変換を打ち消す戻り(追跡器の undo)、`PPAR` の照合、傾いた絞りでの入射瞳の換算まで読みます。`lens_file_write` は break 要素を `COORDBRK` 面に直して書き戻します。

PoC `poc_lens_file_roundtrip` は、同じファイルを別の 2 実装(ray-optics・optiland)がそれぞれ自分の読み手で読んだ値と、近軸・Seidel 和・実光線を照合し、硝材を差し替えて崩れた三枚玉を直して書き戻すまでを通します。

## What it does

`lens_file_read` turns the plain-text sequential prescription that commercial lens-design programs save (`.zmx`) into a `raytrace.lens_system` (or, when the file has `COORDBRK` coordinate breaks — tilts, decentres, fold mirrors — into a `raytrace3d.noncoaxial_system`, with the order flag, the frame flip at mirrors, returns and `PPAR` pickups handled), so every Fullseye optics op (real rays, Seidel sums, OPD / PSF / MTF, colour, tolerances, DLS optimisation, section drawings) runs on it unchanged. Fields and wavelengths are kept as listed in the file; `lens_file_system` picks one. `lens_file_write` writes a prescription (optionally the geometry of an edited system) back, and `lens_file_report` classifies every keyword as read, ignored (with a reason) or unsupported without importing. Glasses come from the material table or your own `.agf` catalogues, matched by exact name. The PoC checks first-order data, Seidel sums and real rays against what two independent readers (ray-optics, optiland) computed from the same files.

## 向くところ / 向かないところ

**向く**: 設計ソフトで作った共軸のレンズ(球面・円錐・偶数次の非球面・鏡)を、画像処理の検査系のシミュレーション(PSF・歪曲・周辺光量)へ持ち込む。最適化や公差の結果を設計ソフトへ返す。手元の古い処方ファイルの束を、読めるもの / 近似つきなら読めるもの / 読めないもの(理由つき)に分ける。

**向かない**: 理想レンズ(PARAXIAL)・トーリック・奇数次の非球面・回折面などの面は拒否します。座標変換面は読みますが、`SCBD`(面の傾き・偏心、並びが公開資料に無い)、最初の面の前に置いた変換(物体空間を動かす規約を確かめていない)、`OBNA`・像高の視野、有限物体の ENPD / FNUM は拒否します。多軸の傾きの順序は第 2 の実装(optiland)が順序 0 しか読まないため、順序 1 は閉形式と手で組んだ系で確かめています。ケラレ係数・曲がった像面・多構成(ズーム)・温度は `allow_partial=True` のときだけ近似として読み、結果に `approximate=True` が立ちます。ソルブはファイルに保存された値(保存した時点の形)で読み、ピックアップだけは元の面と食い違わないかを確かめます。カタログに無い硝材は拒否します(`.agf` を置くか、`allow_partial=True` で n_d・ν_d のモデルに代える)。材料表の別名は辿りません(古い鉛ガラスの名が無鉛の別の硝材に化けるため)。`.zar`(パッケージ)は展開してから中の `.zmx` を渡してください。絞りの縁を通る実光線は、近軸の入射瞳の縁から出すと瞳の収差で絞りの外に出て「けられ」に数えられることがあります(瞳の 98 % で数えるのが既定)。

## 推奨パイプライン

`lens_file_read` → `lens_file_system` → `paraxial_trace` → `spot_stats` → `lens_file_write`

設計ファイルを `lens_file_read` で読み(まず `report` の扱えない件数と `approximate` を見る)→ `lens_file_system` で視野と波長を選んだ処方にし → `paraxial_trace` で EFL・F 値・入射瞳をファイルの値と突き合わせ → `spot_stats`(や `seidel_coefficients`・`psf_from_opd`・`optimize_lens`)で解析・修正し → `lens_file_write` で同じ形式に書き戻す。

## 代替

読まずに分類だけなら `lens_file_report`(古いファイルの束の仕分け)。硝材のカタログは `read_glass_catalog_agf`。処方を手で組むなら `lens_system`、図面は `lens_section_drawing`。

## 限界

- 座標変換面は非共軸の追跡器へ読む(上記の拒否を除く)。理想レンズ(PARAXIAL)・トーリック・奇数次非球面・回折面・r² の非球面項は拒否する。傾いた絞りでは、絞りの縁の円と入射瞳の円が一致しない(`pupil["anisotropy"]`、絞りの半径は入射瞳の面積を保つ)。
- ケラレ係数・曲がった像面・多構成・温度 / 気圧・未知の面のキーワードは `allow_partial=True` のときだけ近似として読み、`approximate=True` を立てる。
- ソルブは保存された値で読む(ピックアップだけは元の面と照合)。カタログに無い硝材と、材料表に別名でしか無い硝材は拒否する。
- 設計ソフトそのものでの往復は試していない(第 2・第 3 の実装として ray-optics と optiland で照合した)。

## 実寸校正

長さはファイルの単位(MM / CM / IN / METER)から mm に換算する。波長は µm のまま、視野は度(無限遠の物体)か mm(有限の物体)。画素の校正は要らない。

## 最初の 1 本

```python
import lensfile as LF
import raytrace as RT

p = LF.lens_file_read()                        # 同梱の三枚玉(ファイルのパスかテキストを渡す)
print(round(RT.paraxial_trace(p["system"])["efl"], 4), p["report"]["n_unsupported"])   # 50.0213 0
s20 = LF.lens_file_system(p, field_index=2)    # 3 つめの視野(20°)
print(round(RT.spot_stats(s20, pupil_fill=0.98)["rms_radius"] * 1e3, 1), "um")
text = LF.lens_file_write(p)["text"]           # 書き戻す(path= で保存)
```

走らせて見るなら `py -3.11 examples/poc_lens_file_roundtrip.py`(図は `FULLSEYE_FIGURE_DIR` を指定したとき)。
