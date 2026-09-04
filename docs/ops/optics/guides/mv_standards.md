---
guide: mv_standards
dim: optics
title: カメラインターフェースの規格と団体
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0
applies_to: optics/imaging_sim, videostream
---

<!-- fullseye guide: 機械視覚の周辺知識。op ではなく、op に渡す値の
     出どころを示す教材。関連 op: sensor_spec / lens_spec / light_spec / interface_budget -->

# カメラインターフェースの規格と団体

産業用カメラのインターフェースは**業界標準として規格化**されており、各規格に所管団体が
ある。どの団体がどれを持っているかを押さえておくと、仕様の一次情報にたどり着ける。

## 1. 誰がどれを持っているか

| 団体 | 所管する規格 |
| --- | --- |
| **A3**（Association for Advancing Automation、旧 AIA・米） | **Camera Link**（PoCL / PoCL-Lite を含む）、**Camera Link HS**、**GigE Vision**、**USB3 Vision** |
| **JIIA**（日本インダストリアルイメージング協会） | **CoaXPress**（2013 年リリース）、IIDC2、SLVS-EC 系 |
| **EMVA**（European Machine Vision Association） | **GenICam**（GenApi / **GenTL** / **SFNC** / PFNC）、**EMVA1288**（カメラ性能の測定法）、**OOCI**（Open Optics Camera Interface） |
| **VDMA**（独） | 規格そのものより、解説・普及・調整の側 |
| **CMVU**（中） | 中国側の窓口 |
| **G3** | 上記を横断する**調整体**。ハードウェア規格をまたいで共通のソフト層を保つ枠組み |

## 2. 層が 2 つある（ここが要点）

```
アプリケーション
      │
  GenICam（EMVA）          ← ソフトの層：機能名と設定の共通化
      │  GenApi / SFNC / GenTL / PFNC
      ├── Camera Link / Camera Link HS  (A3)
      ├── GigE Vision                   (A3)
      ├── USB3 Vision                   (A3)
      ├── CoaXPress                     (JIIA)
      └── Open Optics Camera Interface  (EMVA)
```

**GenICam は G3 の全ハードウェア規格が使う共通のソフト層**である。だから
「露光時間を変える」「ROI を切る」といった操作は、伝送規格が Camera Link でも
CoaXPress でも GigE でも**同じ機能名**（SFNC = Standard Features Naming Convention）で
書ける。ケーブルと帯域は規格ごとに違うのに、アプリは書き換えなくてよい。

* **GenApi** — カメラが自分の機能を XML で記述し、ホストがそれを読んで UI/API を作る。
* **SFNC** — 機能名の標準（`ExposureTime`, `Gain`, `Width`, `OffsetX`, `TriggerMode` …）。
* **GenTL** — トランスポート層の共通 API。フレームグラバーやドライバの差を吸収する。
* **PFNC** — 画素フォーマット名の標準（`Mono8`, `BayerRG12p`, `RGB8` …）。

## 3. EMVA1288（性能の測定法）

同じ EMVA が持つ**カメラ性能の測定・表記の標準**。QE・時間ダークノイズ・飽和容量・
ダイナミックレンジ・最大 SNR・絶対感度しきい値を、**同じ手順で測って同じ形で出す**。

`image_sensors.md` のセンサ表がメーカーを跨いで横並び比較できるのは、
値が全部 EMVA1288 で測られているからである。逆に、EMVA1288 レポートを出していない
カメラの数値は、そのままでは他社と比べられない。

## 4. 仮想化への含意

* **伝送規格が変わっても、制御の語彙（SFNC）は変わらない**。だから
  `optscene` のセンサ/レンズ/照明オブジェクトも、伝送規格に依存しない量
  （露光・ゲイン・ROI・トリガ）で持つのが正しい。伝送は `interface_budget` に
  分離してある、という切り分けはこの構造に合っている。
* **EMVA1288 が単一真実源**。カタログの QE / 雑音 / 飽和容量はここから取る。
  独自指標の数値を混ぜると横並び比較が壊れる。
* 一次情報のたどり方: 伝送規格の仕様書は A3 / JIIA、ソフト層と測定法は EMVA。
  カメラの実測値はメーカーの EMVA1288 レポート。
