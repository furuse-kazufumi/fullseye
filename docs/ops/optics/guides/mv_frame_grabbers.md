---
guide: mv_frame_grabbers
dim: optics
title: フレームグラバとインターフェースの知識
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0
applies_to: optics/imaging_sim, videostream
---

<!-- fullseye guide: 機械視覚の周辺知識。op ではなく、op に渡す値の
     出どころを示す教材。関連 op: interface_budget -->

# フレームグラバーボード（光学系ではないが、撮れるかを決める）

光学が「必要なコントラストで写るか」を決めるのに対し、フレームグラバーは
**それを落とさずに運べるか**を決める。高解像度・高速・ラインスキャンでは、
律速がセンサではなく**伝送帯域**になることが普通にある。

## インターフェースの帯域（一次資料で確認した値）

| 規格 | 1 接続あたり | 実用構成 | 備考 |
| --- | --- | --- | --- |
| **CoaXPress CXP-6** | 6.25 Gbps | 1〜8 接続 | 同軸 1 本で電源（PoCXP）・制御・データ |
| **CoaXPress CXP-12** | **12.5 Gbps** | **4 接続 = 50 Gbps = 5 GB/s** | 8 bit・16k ラインセンサを **300 kHz** で回せる帯域 |
| **Camera Link Base** | 2.04 Gbps | 24 bit × 85 MHz、コネクタ 1 本 | 旧来だが現役。ケーブルが太く短い（〜10 m） |
| **Camera Link Medium** | 4.08 Gbps | 48 bit、コネクタ 2 本 | |
| **Camera Link Full** | 5.44 Gbps | 64 bit | |
| **Camera Link Deca** | 6.80 Gbps | 80 bit | Camera Link の上限 |
| Camera Link HS | 3.125 Gbps/lane | 複数 lane | 長距離（光ファイバ可） |
| **Opt-C:Link**（アバールデータ独自） | **6.25 Gbps/ch**、2 ch 束ねて **12.5 Gbps** | 光ファイバ（コア 50 / 62.5 µm、クラッド 125 µm） | **数百 m 延長可・ノイズに強い**。画像・シリアル・トリガ・リンク・ユーザの 5 種パケットで制御まで光に載る。Camera Link カメラは変換ユニット（AOC-162 等）で接続 |
| GigE Vision | 1 / 5 / 10 / 25 GigE | — | ケーブルが安く長い。CPU 負荷は高め |

**16k × 300 kHz × 8 bit ≈ 4.9 GB/s** が CXP-12 ×4 の 5 GB/s にちょうど収まる、という
設計になっている。Vieworks VT シリーズ（TDI・最大 300 kHz）はこの帯域を前提にした製品。

## 主なメーカーと現行ボード

| メーカー | 製品 | 確認した仕様 |
| --- | --- | --- |
| **Euresys** | Coaxlink Quad CXP-12 | PCIe 3.0 x8、カメラ帯域 5000 MB/s、CXP-12 ×4 |
| Euresys | Coaxlink Quad CXP-12 JPEG | 4 独立チャネル + **ベースライン JPEG エンコーダ 250 Mpixel/s**（ボード上で圧縮） |
| Euresys | Coaxlink QSFP+ / Duo / Mono LH | 1〜8 カメラ、CXP-6〜CXP-12 の幅で構成できる |
| **Matrox** | Rapixo CXP（RAP8G4C12P602） | CoaXPress 2.0、CXP-12 ×4、PCIe 3.1 x8、**12.5 GB/s カメラ帯域**、PoCXP |
| **Teledyne DALSA** | Xtium2-CXP PX8 Quad | CXP-12 ×4、カメラ帯域 5000 MB/s、PCIe Gen3 x8（バス 7000 MB/s まで） |
| BitFlow | Claxon / Cyton | CXP / Camera Link |
| Active Silicon | FireBird | CXP / Camera Link |
| Kaya Instruments | Komodo | CXP |
| **アバールデータ** | APX-3312A / APX-3313A（Camera Link）、Opt-C:Link 系 | Camera Link 対応ボードと、独自光 I/F の両方を持つ。国内の装置向けで強い |
| Euresys | Grablink（Camera Link） | CXP の Coaxlink と別系統で Camera Link を継続 |

## なぜ仮想化で無視できないか

0. **長距離が要るなら選択肢が絞られる**。Camera Link は 10 m 級で頭打ちだが、
   Opt-C:Link（光）なら数百 m。装置が大きい・電気ノイズが多い現場（溶接、
   モータドライブの近く）では、帯域より先に**距離とノイズ耐性**で規格が決まる。
1. **エリアスキャンでは普通センサが律速**。IMX541（20.3 MP・8 bit）は 1 枚 20.3 MB なので
   5 GB/s なら理論 246 fps 出せるが、センサ自体が 18〜42 fps。→ 帯域は余る。
2. **ラインスキャン / TDI では帯域が律速**になる。16k × 300 kHz で 4.9 GB/s を使い切る。
   ラインレートを上げたいなら、まずボードとケーブルの本数の話になる。
3. **エンコーダ同期**（ラインスキャン専用）。搬送速度とラインレートを同期させるのは
   グラバーの仕事で、ここがずれると**画像の縦横比が崩れる**。エリアスキャンには
   存在しない故障モードで、光学をいくら詰めても直らない。
4. **ボード上の前処理**。シェーディング補正・ビット詰め・JPEG 圧縮をボードでやると
   ホストの負荷が下がる。合成データで学習したモデルを載せるとき、
   **推論の前段にこの補正が入る**ので、学習データ側にも同じ補正を通すか、
   補正前の生データで学習するかを決めておく必要がある。
5. **トリガのジッタ**。パルス照明やストロボと同期する場合、ジッタが露光ばらつき＝
   明るさばらつきになる。ドメインランダム化の `intensity_jitter` は本来ここに根拠がある。

## 実装との接続

`optscene.interface_budget()` が、センサの画素数・ビット深度・インターフェースから
**帯域律速の最大フレームレート / ラインレート**を返す。センサ側の上限と突き合わせて
「どちらが律速か」を先に知るための op。
