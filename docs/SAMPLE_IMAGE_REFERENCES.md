# Sample images — provenance, source papers & public repositories

> ユーザー指摘(2026-08-16): 「元になった論文とか、GitHub にもいっぱいあるだろう」。
> Fullseye の公開開示ポリシー([[project_imgevolve_goal_knowledge_layer_2026_08_13]])に従い、
> 収集したサンプル画像の**出所・ライセンス・元論文・公開リポジトリ**を監査可能な形で記録する。
> **外部から画像を勝手にダウンロードしていない**(合成 = 自作、それ以外 = scikit-image に同梱される
> classic 画像のみ)。**MVTec/HALCON のサンプル画像は proprietary ゆえ収集しない。**

収集物 = `studio_assets/sample_images/`(機械可読 provenance は同 dir の `manifest.json`)。
再生成 = `py -3.11 tools/gen_sample_images.py`、アクセス = `sample_images.py`。

## 収集したサンプル画像

### 合成(own work・Fullseye 生成・ライセンス自由)
`gradient` / `blobs` / `shapes` / `checker_noisy` — `tools/gen_sample_images.py` が決定的に生成。
第三者の権利は一切含まない。

### scikit-image `skimage.data`(BSD-3-Clause プロジェクト・各画像は下記)
正典 = <https://github.com/scikit-image/scikit-image>(`skimage/data/`、各画像のライセンスは
`skimage/data/README.txt` / `LICENSE.txt`)/ API = <https://scikit-image.org/docs/stable/api/skimage.data.html>

| name | 内容 | ライセンス / 出所 |
|---|---|---|
| `coins` | ギリシャ硬貨の写真(blob/segmentation の定番) | scikit-image 同梱・public domain 相当(`skimage/data/README.txt`) |
| `camera` | "cameraman"(古典テスト画像) | **CC0**(撮影者 Lav Varshney)。v0.18 で著作権配慮のため差替え済みの CC0 版 |
| `page` | スキャンした文書ページ(2 値化/OCR 前処理) | scikit-image 同梱・public domain 相当 |
| `cell` | 定量位相イメージング(digital hologram 由来) | **CC0**(public domain)。credit = Paul Müller, Mirjam Schürmann, Salvatore Girardo, Gheorghe Cojoc, Jochen Guck。元論文 = 球状物体の size/屈折率の正確評価(quantitative phase imaging)。取得ライブラリ = `qpformat` |

> honest: `coins`/`page` の一次撮影者は skimage 側で "public domain / no known copyright" として同梱。
> 厳密な原典追跡は `skimage/data/README.txt` を正本とする(バージョンで更新されうる)。

## さらに多くのサンプル画像がある公開データセット/リポジトリ(参照のみ・未取込)

古典的画像処理のベンチマーク画像は以下に多数ある。**取り込む場合は各ライセンスを個別確認**すること
(研究/学術限定のものが多い)。Fullseye は現状これらを同梱していない(参照に留める)。

| データセット / repo | 内容 | 元論文 / URL・ライセンス |
|---|---|---|
| **scikit-image data** | 上記 classic 群 + astronaut/coffee/chelsea 等 | github.com/scikit-image/scikit-image(BSD-3、各画像 CC0/PD) |
| **OpenCV samples** | lena 代替・fruits・building 等 | github.com/opencv/opencv `samples/data/`(Apache-2.0) |
| **USC-SIPI Image Database** | Baboon(Mandrill)/Peppers/cameraman 等の標準テスト画像 | sipi.usc.edu/database(研究利用)。※Lena は倫理的配慮で非推奨 |
| **BSDS500**(Berkeley Segmentation) | 自然画像 500 + 人手セグメンテーション | Arbeláez, Maire, Fowlkes, Malik, "Contour Detection and Hierarchical Image Segmentation", IEEE TPAMI 2011(学術) |
| **Set5 / Set14 / BSD68 / DIV2K** | 超解像・ノイズ除去ベンチマーク | 各 SR/denoising 論文(DIV2K = Agustsson & Timofte, CVPRW 2017) |
| **MVTec AD**(異常検知) | 産業欠陥画像 | Bergmann et al., "MVTec AD", CVPR 2019(**研究限定・商用不可**、要ライセンス確認) |

> ★注意: **HALCON 同梱のサンプル画像(MVTec)は proprietary** ゆえ Fullseye には収集しない。
> op / アルゴリズムの元論文は各 backend の docstring と `docs/REFERENCES.md` に記録済み
> (RANSAC=Fischler&Bolles 1981、SGM=Hirschmüller、PPF=Drost2010 等)。

## 出典(本 doc 作成の一次確認)
- scikit-image data API: <https://scikit-image.org/docs/stable/api/skimage.data.html>
- scikit-image リポジトリ(各画像ライセンス): <https://github.com/scikit-image/scikit-image>
