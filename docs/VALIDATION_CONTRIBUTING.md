# 実機・実データでの検証を報告する

[English](VALIDATION_CONTRIBUTING.en.md) · **日本語**

Fullseye は個人開発で、物理の計測装置を持っていません。CI が確かめられるのは、
仮想の光学系・合成した真値・閉形式で計算できる真値までです。Apache-2.0 で公開して
いるのは、実機や実データを持つ人に確かめてもらうためでもあります。報告が 1 件
増えるごとに、[成熟度台帳](MATURITY.md)の検証は少しずつ正確になります。

**データは共有しなくて構いません。** 企業の画像・CAD・測定値は普通、外に出せません。
結果の数値だけの報告も正規の経路として受け付けます(重みは、再現できる報告より
低くなります。下の「昇格規則」を参照)。

## 2 つの経路

| 経路 | 使う場面 |
|---|---|
| [検証報告フォーム](https://github.com/furuse-kazufumi/fullseye/issues/new?template=real_validation_report.yml)(GitHub issue) | 能力の段(`verified-synthetic` → `validated-public-real-data` → `validated-hardware`)を動かすための報告 |
| [Discussions › Show and tell](https://github.com/furuse-kazufumi/fullseye/discussions/categories/show-and-tell) | 「手元の装置で試してみた」程度の気軽な結果共有や質問。段は動かしませんが、ここから正式な報告に育つこともあります |

公開の場に書きたくない場合は、保守者にメールで送ることもできます
(kazufumi@furuse.work。`pyproject.toml` の作者欄と同じ宛先です)。その場合、
公開するのは**同意を得た集計値だけ**で、台帳の `source` 欄には `private-submission`
と記録します。

## 歓迎する報告

- 実機での結果: カメラ・センサ・光学系・照明を実際に組んで、Fullseye の能力・PoC・op
  を走らせ、独立した基準と比べたもの
- 公開実データでの結果: ライセンスと URL がはっきりしたデータセットで走らせたもの
- 非公開の実データでの結果: 数値だけの報告、または合成で作り直したデータを添えたもの
- **失敗した条件**: 照明・表面・大きさ・ノイズなど、どこで崩れたか。成功と同じだけ
  役に立ちます

真値の取り方は、基準計測器・校正ターゲット・認証された基準器・公表値のどれかで、
その**不確かさを単位つきで**書いてください(例: ±0.005 mm, k=2)。

## プライバシーとデータの扱い

- 社内データ・画像・製品名は**書かないでください**。装置は一般的な説明
  (「1/2 型モノクロ、テレセントリック 0.5 倍、同軸照明」など)で十分です。
- 所属・勤務先は求めません。台帳にもその欄はありません
  (`tools/gen_maturity.py` は未知の欄を持つ記録を拒みます)。
- データの出し方は 3 通りです:

| `data_sharing` | フォームの選択肢 | 意味 |
|---|---|---|
| `shared` | 共有可 | データを共有する(ライセンスと URL を書く) |
| `synthetic-recreation` | 合成で再現したデータを共有 | 本物の代わりに、同じ条件を合成で作り直したデータを共有する。**歓迎します** —— 保守者が再現でき、元のデータは出ません |
| `results-only` | 結果のみ(データは非公開) | 数値だけを報告する |

## 検証キット

手元のデータを外に出さずに、決まった集計のしかたで数字を出す道具です。

```text
python -m fullseye.validation_kit list
python -m fullseye.validation_kit run blob-count --manifest truth.csv --out result.json
```

`truth.csv` は `file,truth` の 2 列(`file` は CSV の置き場所からの相対パス、`truth` は
基準で得た真値)。出力 JSON に入るのは、件数・誤差の集計(平均・符号つき平均・RMS・
最大・完全一致率など)・Fullseye の版とコミット・Python / numpy の版・OS の種類・
入力ファイルの SHA-256 だけです。**画素・ファイル名・パスは入りません**
(ハッシュも要らなければ `--no-hashes`)。この JSON をフォームの「結果」欄に貼って
ください。

いまある手順は `blob-count`(能力 `blob-and-region`: 物体の個数を数えて基準の個数と
比べる)の 1 つです。手順を足すには `fullseye/validation_kit.py` の `KITS` に `Kit` を
1 つ足し(`measure` は灰色画像と引数を受けてスカラーを 1 つ返す)、
`tests/test_validation_kit.py` に既知の真値での試験を足してください。

## 昇格規則

段を決めるのは**保守者**です。保守者は報告を読んで受理(`accepted`)するかを決め、
受理した報告を `docs/validation_reports.json` に記録します。ただし受理しただけでは
段は上がりません。`tools/gen_maturity.py` が次の規則を**機械的に**当てはめ、満たした
ときだけ段が上がります。規則は [MATURITY.md](MATURITY.md) にも書き出されます。

| 規則 | 上がる段 | 条件 |
|---|---|---|
| `hardware-reproducible` | `validated-hardware` | 実機の報告 **1 件**。受理済み・真値が追跡可能(校正済み計測器 / 認証された基準器 / 公表値)・データか合成で作り直したデータと手順を共有・保守者がそれで再実行して、申告した不確かさの中で同じ数値を得た |
| `hardware-independent-results` | `validated-hardware` | 実機の報告 **2 件以上**(結果のみで可)。受理済み・報告者が別・装置構成が別・どれも真値が追跡可能・どれも申告した不確かさの中で合っている |
| `public-data-reproduced` | `validated-public-real-data` | 公開実データの報告 **1 件**。受理済み・データの URL とライセンスがある・保守者が同じデータで再実行して報告どおりの数値を得た |

結果のみの報告は 1 件では段を上げません。再現できないぶん、別の人・別の装置での
一致を求めます。ただし 1 件でも台帳に記録され、謝辞に載り、次の報告と合わせて
数えられます。外部報告が段を**下げる**ことはありません(再現できなかった報告は
`not-reproduced` として記録に残ります)。

`validated-public-real-data` には、もう 1 つの道として、公開実データを使う例を CI
の門で走らせる道があります(これまでの経路。`data: real` の例)。

## 記録のされ方

`docs/validation_reports.json` の `reports` に 1 件ずつ記録します。

| 欄 | 中身 |
|---|---|
| `id` / `capability` / `kind` | 報告の識別子 / 能力の id(`docs/capabilities/`)/ `hardware` か `public-real-data` |
| `review` | `pending` / `accepted` / `not-reproduced` / `withdrawn` |
| `source` | issue の URL、または `private-submission` |
| `reporter` / `setup` | 報告を区別するための短い鍵(ハンドルや `anon-1` など)/ 装置構成の短い説明 |
| `ground_truth` / `ground_truth_uncertainty` | 真値の取り方 / その不確かさ |
| `procedure` / `fullseye_version` / `result` | 手順 / 版 / 結果の要約(単位と n つき) |
| `data_sharing` | `shared` / `synthetic-recreation` / `results-only` |
| `credit` | 謝辞に載せる名前・ハンドル(任意。`null` なら匿名) |
| 任意 | `traceable_reference` / `reproduced_by_maintainer` / `within_stated_uncertainty` / `data_licence` / `data_url` / `reviewed_on` / `failure_conditions` / `note` |

記録したら `py -3.11 tools/gen_maturity.py` で台帳を作り直します
(`tests/test_maturity.py` と `tests/test_validation_reports.py` が形と規則を確かめます)。

## 謝辞

`credit` を書いた報告は、[MATURITY.md](MATURITY.md) の「外部からの検証報告」の表と
リリースノートに名前(またはハンドル)が載ります。空欄なら匿名のままです。
取り下げたいときは issue かメールで知らせてください。`withdrawn` にして段の計算から
外します。
