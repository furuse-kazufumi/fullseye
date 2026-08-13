# Fullseye ドキュメント索引

**Fullseye**（作業名 imgevolve）は、numpy-native な画像処理オペレータ・ライブラリと、HDevelop 風のビジュアル・パイプライン設計環境（Fullseye Studio）+ 実行ランタイム（FullseyeEngine）を備えた、HALCON/HDevelop 級の実用ツールです。オペレータは約 **521**（レジストリ）、実 HALCON オペレータ **269/2313** を genuine 実装、31 カテゴリをカバーします。

> **まずはここから → [GETTING_STARTED.md](GETTING_STARTED.md)（5 分で動かす）**

---

## 使い方（ユーザー向け・まずこの 4 つ）

| ドキュメント | 内容 |
|---|---|
| **[GETTING_STARTED.md](GETTING_STARTED.md)** | 5 分ではじめる: インストール → 最初のパイプライン → Studio/CLI/コードで実行 → 結果を見る |
| **[INSTALL.md](INSTALL.md)** | 環境構築の完全ガイド: 前提・`pip install -e .` と extras の使い分け・Windows/Linux インストーラ・最小構成/組み込み・トラブルシュート |
| **[STUDIO_GUIDE.md](STUDIO_GUIDE.md)** | Fullseye Studio 完全ガイド: 3 パネル・オペレータブラウザ・ステップ実行・つまみ・Inspector・知覚パネル・Command palette・ショートカット・Export |
| **[ENGINE.md](ENGINE.md)** | FullseyeEngine（設計 → 実行）: 全メソッド・Python からの利用・CLI `run`・他プロジェクトからの呼び出し |

---

## オペレータ / API リファレンス

| ドキュメント | 内容 |
|---|---|
| [OPERATORS.md](OPERATORS.md) | 全 521 オペレータのカタログ（31 カテゴリ、sort 別、HALCON/OpenCV/scikit-image/MATLAB の対応 API） |
| [EXAMPLES.md](EXAMPLES.md) | オペレータ別のサンプルコード（他ライブラリとの等価呼び出し付き） |
| [OP_INDEX.json](OP_INDEX.json) | 機械可読なオペレータ索引（`imgevolve.py index` で再生成） |
| [ADDING_OPS.md](ADDING_OPS.md) | 新しいオペレータの追加方法（進化・codegen・カタログ・索引が自動追従） |
| [../examples/README.md](../examples/README.md) | 実行可能なエンドツーエンドのサンプルスクリプト集 |

## 知覚スタック（ロボティクス/ビジョン）

| ドキュメント | 内容 |
|---|---|
| [PERCEPTION.md](PERCEPTION.md) | 知覚スタック 1 枚リファレンス（stereo / terrain / detect / registration / pose / flow / motion） |
| [PERCEPTION_REALDATA.md](PERCEPTION_REALDATA.md) | 実写クリップでの計測結果（ビデオ I/O + honest な実測値） |

## HALCON パリティ / 被覆（honest disclosure）

| ドキュメント | 内容 |
|---|---|
| [HALCON_PARITY.md](HALCON_PARITY.md) | 「名前だけ」でなく実際に同じ処理ができるかの genuine 実装状況（269/2313） |
| [HALCON_COVERAGE.md](HALCON_COVERAGE.md) | 公式リファレンス（v2605）を実スクレイプした被覆計測 |
| [LIB_COVERAGE.md](LIB_COVERAGE.md) | 多ライブラリ横断被覆（HALCON 以外の distinctive op 取り込み） |
| [PARITY_CROSSBACKEND.md](PARITY_CROSSBACKEND.md) | 独立実装（scipy/cv2/skimage）同士のクロスバックエンド一致による parity 実証 |

## 品質 / 来歴 / 再現

| ドキュメント | 内容 |
|---|---|
| [ACCURACY_BENCH.md](ACCURACY_BENCH.md) | 進化 champion vs null（holdout）の常設精度テーブル |
| [PROVENANCE.md](PROVENANCE.md) | 公開アルゴリズムからの自作である旨の来歴 |
| [REFERENCES.md](REFERENCES.md) | 各オペレータの文献的裏付け |
| [REPRODUCE.md](REPRODUCE.md) | seed 駆動・決定論的な数値の再現手順 |
| [STATUS.md](STATUS.md) | プロジェクトの現在地・計画（plan_ref） |

## リリースノート / 設計

| ドキュメント | 内容 |
|---|---|
| [V13.md](V13.md) | v13 = 実用化 + クロスプロジェクト packaging + 知覚スタック |
| [V14.md](V14.md) | v14 = 知覚スタック完成（モーション + 堅牢化） |
| [STUDIO_UX.md](STUDIO_UX.md) | Fullseye Studio の UX/デザイン改善の意図と背景 |

---

## クイックコマンド

```powershell
py -3.11 -m pip install -e ".[opencv,gui]"     # 導入（画像 I/O + Studio）
py -3.11 studio.py                              # Fullseye Studio を起動（= fullseye-studio）
py -3.11 imgevolve.py ops --search edge         # オペレータ検索（= fullseye ops --search edge）
py -3.11 imgevolve.py apply gauss_filter in.png out.png --a 0.6
py -3.11 imgevolve.py run pipeline.json in.png --out result.png
py -3.11 imgevolve.py coverage                  # honest な被覆数
```

Python から:

```python
import fullseye, numpy as np
out = fullseye.run_pipeline(frame, ["gaussian", "sobel_amp", "otsu"])
eng = fullseye.FullseyeEngine.load("pipeline.json"); result = eng.run(frame)
```
