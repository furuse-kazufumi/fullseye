# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""生成物を**全部**、決まった順で作り直す(コミット前の 1 コマンド)。

## なぜ要るか(2026-09-09)

この repo には生成物が多い —— op ノート、TOC、Studio の help HTML、op カタログ、
展示ギャラリー、examples の README、6 言語の docs 索引、能力索引、堅牢性台帳、
成熟度台帳。それぞれに drift 検査があるので**壊れれば CI が教えてくれる**が、
**どれを回すべきかは人が記憶で選んでいた**。

同じ日に 3 回踏んだ:

* 展示を 1 本足した → `opdocs md` を回し忘れて CI が赤(`laplace_of_gauss` のノート)
* 図を作り直して `annotate_legend` / `annotate_inset` を使い始めた →
  また `opdocs` を回し忘れて CI が赤
* しかも 2 回目は「影響しそうな門」を**自分で選んで**回していた ——
  選んだ集合に `test_opdocs.py` が入っていなかった

**記憶で選ぶ手順は、選び漏れる。** だから順序を 1 か所に書いて、1 コマンドにする。

## 使い方

    py -3.11 tools/regen_all.py           # 全部作り直す
    py -3.11 tools/regen_all.py --check   # 作り直して、差分が出たら exit 1
    py -3.11 tools/regen_all.py --list    # 何をどの順で回すかだけ見る

``--check`` は**強い不変条件**を見る: 全部作り直したあとの作業ツリーが
きれいであること。個々の drift 検査の総和より広く、「回し忘れ」を 1 つ残らず拾う。
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: 回す順。**順序が意味を持つ** —— 上流(op ノート)が下流(索引・カタログ)の
#: 入力になる。足したら、ここに 1 行足す。
CHAIN = [
    # ★最上流。`auto_specs_data.py` は backends_auto が registry を組む入力(wheel 同梱の
    #   data/auto_specs/*.json の複製)なので、registry を読む下流すべてより先に回す。
    #   2026-10-07 まで `tools/` の外にあって鎖にも表にも無かった(差分は無かったが、
    #   spec を足して回し忘れても誰も気づけなかった)。
    (["gen_auto_specs_data.py"], "auto_specs_data.py(data/auto_specs/*.json の wheel 同梱用ミラー)"),
    (["tools/opdocs.py", "all"],
     "op ノート + SAMPLES + TOC + RAG skill のコーパス地図 + Studio help HTML(6 言語)"),
    (["tools/gen_op_catalog.py"], "1 ページの op カタログ"),
    (["tools/gen_capabilities_index.py"], "能力索引(docs/capabilities/*.md から)"),
    (["tools/gen_hardening_index.py"], "堅牢性台帳"),
    (["tools/gen_maturity.py"], "成熟度台帳(生成物 + 機械可読 JSON)"),
    # ★展示館より**先**に回す —— 生成器は見出しに収蔵番号を出すので、
    #   未発行の展示が 1 つでもあると BuildError で止まる。
    (["tools/gen_exhibit_numbers.py"], "収蔵番号の発行(追記のみ・既存は動かさない)"),
    (["tools/gen_wingpoc_gallery.py"], "PoC 展示館(総合案内 + 棟、ja/en)"),
    (["tools/gen_examples_readme.py"], "examples/README.md"),
    (["tools/gen_oss_landscape.py"], "既存 OSS の地図(docs/literature/oss_landscape.json → OSS_LANDSCAPE.md)"),
    # ViEW2026 案内ページ(7 言語)。docmap がその題を読むので gen_docs_index_ops より先。
    (["tools/gen_view2026_pages.py"], "docs/view2026/**/index.md(論文の QR の行き先、正本は exhibits.json)"),
    # ★gen_docs_index_ops より先: docmap が docs/OP_COUNT_HISTORY.md の題を読む。README*.md は
    #   両者が書くが、マーカーが別なので互いの中身には触れない。gen_maturity の後(maturity.json を読む)。
    (["tools/gen_trust_block.py"],
     "README.md + docs/README*.md の trust ブロックと docs/OP_COUNT_HISTORY.md(測定データ docs/*.json から)"),
    (["tools/gen_docs_index_ops.py"], "docs/README*.md の ops / poc / docmap ブロック"),
    (["tools/gen_examples3d_doc.py"], "docs/EXAMPLES_3D.md(3-D 例の一覧)"),
    (["tools/gen_sensor_playbook.py"], "センサー playbook"),
    # ★`tools/` の外にある唯一の生成物。だから取りこぼしていた ——
    # 生成器を `tools/*.py` で探す限り、これは永久に見つからない。
    (["imgevolve.py", "index"], "docs/OP_INDEX.json(レジストリの機械可読索引)"),
    # ★これも `tools/` の外。2026-09-20 まで鎖に無く、docs/OPERATORS.md が
    #   885 op / 47 分類(2026-09-06 の値)のまま置き去りだった(GenSpark 第 53 報と
    #   ユーザー指摘)。生成器が鎖に無い生成物は、必ず古びる。
    (["catalog.py"], "docs/OPERATORS.md(4 ライブラリの対応表と被覆率)"),
    # ★2026-10-07: 以下 3 本も `tools/` の外にあり、列挙が `tools/*.py` しか見ていなかったので
    #   鎖にも表にも無かった。どれも registry とコミット済みの入力だけから決まり、2 回
    #   回してバイト一致・各 3 秒(実測)。置き去りの実例:
    #   EXAMPLES.md は「67-op」、REFERENCES.md は「153 operators」、
    #   OP_DISPOSITION.json は implemented 324(実際 405)のままだった。
    (["dispositions.py"], "docs/OP_DISPOSITION.json(HALCON 全 2,313 op の処遇。入力は同梱の fullseye/data/halcon_graph.json)"),
    (["references.py"], "docs/REFERENCES.md(op ごとの出典)"),
    (["samples.py"], "docs/EXAMPLES.md(ライブラリ横断のサンプルコード)"),
    # 索引の後(複製するので)。ノートは opdocs の後なら何番目でもよい。
    (["tools/gen_mcp_data.py"], "fullseye/data/OP_INDEX.json + OP_NOTES.json(MCP が wheel から読む複製)"),
    (["tools/conversion_matrix.py"], "docs/CONVERSION_MATRIX.md(表現の変換表)"),
    (["tools/gen_design_notes.py"], "設計判断集(ソースの ★ から 6 言語)"),
]

#: **CHAIN に入れないものと、その理由**(2026-09-09)。
#:
#: この表が無いと CHAIN は「人が思い出せた生成器の集合」に逆戻りする ——
#: それはこの道具が潰したはずの失敗そのもの。実際、初版の CHAIN は手で選ばれて
#: いて `gen_examples3d_doc` が漏れており、`docs/EXAMPLES_3D.md` は
#: **`ops3d = 347 op` と書いたまま古びていた**(実際は 357)。
#:
#: 除外は「回さなくてよい」ではなく「**--check の門にできない**」の意味。
#: 記事の生成器は回すたびに出力が変わるので、drift 検査に混ぜると毎回赤になる:
#:
#:   * 図と GIF を描き直す → 同じ入力でもバイトが変わる(SHA-256 も、kB 表示も)。
#:     実測: `wing1d_aliasing.gif` は 1,135,171 → 1,130,583 バイト。
#:   * ベンチ由来の数値を書き込む(`_wing2d_meta.json` の `seconds_per_search`
#:     2.383 → 2.395)。これは**測定値**なので一致するはずがない。
#:   * ★そして危険: 生成直後の記事は画像を**相対パス**で書く。公開版は
#:     `raw.githubusercontent.com` の絶対 URL に直したもの(Qiita は相対パスだと
#:     画像が出ない —— memory `feedback_qiita_svg_path_and_cache`)。生成器だけを
#:     回すと、その絶対 URL が 42 行ぶん巻き戻る。**回すなら記事の公開手順まで
#:     通しでやること。**
#: 除外は**ファイル名で**書く。散文でまとめると(「wing*_gallery の 10 本」)
#: 機械で照合できず、下の `unclassified()` が働かない。
_ARTICLE_REASON = ("記事の生成器。図と GIF を描き直すのでバイトが変わり、ベンチ実測値を "
                   "書き込み、画像リンクを絶対 URL から相対パスに戻す —— drift 検査に "
                   "混ぜると毎回赤になる。回すなら記事の公開手順まで通しで。")
_HALCON_TABLE_REASON = ("入力 data/halcon_operators.json(MVTec のリファレンス表。説明文を含むので"
                        "再配布せず .gitignore —— 手元にしか無い)が CI に無い。")
_PROBE_REASON = ("第 2 実装の探針が書く実測の台帳。ノートがこれを契約として引用するので、"
                 "回し直す = 契約の書き換え(人が差分を読んで承認する)。値は backend の数値で、"
                 "SimpleITK のしきい値などは版で動く。")
_IMAGE_REASON = ("画像・動画の書き手。PNG/GIF のバイトは Pillow の zlib・FreeType・フォント・"
                 "エンコーダで変わり、Linux の CI と手元でバイト一致しない —— --check に混ぜると"
                 "毎回赤になる(gen_op_figures と同じ理由)。")
_SPIKE_REASON = ("スパイク(実験)の記録。spikes/out_gallery/ の図は当時の証跡として凍結してあり、"
                 "再描画(matplotlib / GUI)はバイトが変わる。")
EXCLUDED = {
    "tools/gen_wing1d_gallery.py": _ARTICLE_REASON,
    "tools/gen_wing2d_gallery.py": _ARTICLE_REASON,
    "tools/gen_wing3d_gallery.py": _ARTICLE_REASON,
    "tools/gen_wingastro_gallery.py": _ARTICLE_REASON,
    "tools/gen_wingconv_gallery.py": _ARTICLE_REASON,
    "tools/gen_wingct_gallery.py": _ARTICLE_REASON,
    "tools/gen_wingevo_gallery.py": _ARTICLE_REASON,
    "tools/gen_wingopt_gallery.py": _ARTICLE_REASON,
    "tools/gen_wingstudio_gallery.py": _ARTICLE_REASON,
    "tools/gen_wingvox_gallery.py": _ARTICLE_REASON,
    "tools/gen_academic_gallery.py": _ARTICLE_REASON,
    "tools/gen_industrial_gallery.py": _ARTICLE_REASON,
    "tools/gen_science_gallery.py": _ARTICLE_REASON,
    "tools/gen_literature_notes.py": "文献層(docs/literature)。入力の RAD コーパス(数千本)は repo の外にあるので CI では作れない —— 生成物を commit し、tests/test_literature_notes.py が形(op リンクの実在・抄録なし・手元パスなし)を守る。",
    "tools/gen_ai_inputs.py": "記事用の入力素材づくり。API キーを読むので CI では回さない。",
    "tools/gen_backmatter_figs.py": _ARTICLE_REASON,
    "tools/gen_article_assets.py": _ARTICLE_REASON,
    "tools/gen_newops_media.py": _ARTICLE_REASON,
    "tools/gen_sample_images.py": "サンプル素材の再生成。入力が変わらない限り回す必要がない。",
    "tools/gen_sample_3d.py": "3-D サンプル素材の再生成。入力が変わらない限り回す必要がない。",
    "tools/gen_itokawa_turntable.py": "実データのターンテーブル動画。素材が変わらない限り不要。",
    "tools/gen_op_figures.py": ("op ノートの図を描く。★**op を足したら、これを先に回してから "
                                "regen_all を回すこと** —— ノートは図を埋め込むので依存がある。"
                                "逆順でやると test_op_figures 3 本と "
                                "test_opdocs::test_notes_match_generator_no_drift が落ち、"
                                "「両方回したのに落ちる」ので回し忘れと区別がつかない(2026-09-16 に実測)。"
                                "ここから外してあるのは図のバイトが非決定だからだが、実測では "
                                "2,817 本中 44 本しか変わらず、非決定なのは tb_project と dots_image の "
                                "2 本だけだった。"),
    "tools/gen_sample_thumbs.py": "サンプル画像のサムネ。同上(画像)。",
    "tools/build_exhibits.py": ("展示の素材づくり(図の再描画を伴う)。目次側の生成は "
                                "gen_wingpoc_gallery / gen_op_catalog が担う。"),
    # ---- 2026-10-07: 列挙を repo 直下・tools/** 再帰・画像の書き手まで広げて釣れたもの ----
    # (A) 入力が repo に無い(手元にしか無い MVTec のリファレンス表)
    "honest_summary.py": _HALCON_TABLE_REASON + (
        " → 出力 docs/HALCON_PARITY.md。代わりに見出しの数字は "
        "tests/test_derived_headlines_2026_10_07.py が同梱の名前表(halcon_names_data)から"
        "数え直して CI で照合する。"),
    "halcon_coverage.py": _HALCON_TABLE_REASON + " → 出力 docs/HALCON_COVERAGE.md(章ごとの被覆は章の情報が要る)。",
    "gen_halcon_names_data.py": _HALCON_TABLE_REASON + " → 出力 halcon_names_data.py(その表の名前だけの同梱用ミラー)。",
    "graph.py": _HALCON_TABLE_REASON + (" → 出力 data/halcon_graph.json(手元)。同梱の "
                                        "fullseye/data/halcon_graph.json はそれを手で移したもの。"),
    # (B) 出力が「入れてあるライブラリの版」で変わる(CI の pip 最新版と手元で一致する保証が無い)
    "lib_coverage.py": ("docs/LIB_COVERAGE.md。前半の表が『入れてある cv2 / skimage の公開関数の数』"
                        "(dir() の実測)なので、ライブラリの版が変わるだけで出力が変わる —— "
                        "--check に混ぜると repo を触らずに CI が赤になる。registry 由来の表"
                        "(ライブラリ別 op 数・合計)は tests/test_derived_headlines_2026_10_07.py が "
                        "docs/OP_INDEX.json と照合する。"),
    "parity.py": ("docs/PARITY_CROSSBACKEND.md。backend 間の最大差(小数 4 桁)を**実測**して書くので、"
                  "cv2 / skimage / scipy の版で値が動く。手元では 2 回回してバイト一致だが、"
                  "CI の版と一致する保証は無い。op を足したら手で回して差分を読むこと。"),
    "accuracy_bench.py": ("docs/ACCURACY_BENCH.md。進化を全問題で回すベンチ(実測 約 150 秒)。"
                          "手元では 2 回でバイト一致だが、数値はライブラリの版に依存する測定値。"),
    "bench_vs_opencv.py": ("docs/BENCH_VS_OPENCV.md。GPU(CUDA)ベンチの実測値。★出力先が "
                           "絶対パスで書かれており、どの checkout から回しても手元の本線を書き換える。"),
    # (C) 入力が手元の進化結果 / 人の判断を要する再承認
    "champion_to_macro.py": ("data/macro_champions.json + macro_champions_data.py。入力は手元の進化の"
                             "勝者(out/、gitignore)なので CI では作れない。"),
    "recapture_wave0_pins.py": ("data/wave0_pins.json の**再承認**(--write)。門の基準値を自動で"
                                "書き直すと門の意味が無くなるので、人が差分を読んでから回す。"),
    # (D) 実測の台帳(第 2 実装の探針)。手元では決定的・速い(6 本で約 2 分)が、
    #     値は backend の数値(小数 12 桁)で、ノート(opdocs)がこの台帳を契約として引用する。
    #     回し直すと**文書化された契約が変わる**ので、人が差分を読んで承認する。
    "tools/impl2/blank_probe.py": _PROBE_REASON + " 出力 docs/op_blank_frame.json(--all-image --all-region-out)。",
    "tools/impl2/border_probe.py": _PROBE_REASON + (" 出力 docs/op_border.json(--all)/ op_border_region.json"
                                                    "(--all-region)/ op_border_region_out.json(--all-region-out)。"),
    "tools/impl2/connect_probe.py": _PROBE_REASON + " 出力 docs/op_connectivity.json(--all-region)。",
    "tools/impl2/knob_probe.py": _PROBE_REASON + " 出力 docs/op_knob.json(gen_mcp_data が fullseye/data へ複製)。",
    "tools/impl2/norm_probe.py": _PROBE_REASON + " 出力 docs/op_normalisation.json(--all-image)。",
    "tools/impl2/quant_probe.py": _PROBE_REASON + " 出力 docs/op_quantisation.json(--all-image)。",
    "tools/impl2/pilot.py": ("第 2 実装を LLM(手元の Ollama)に書かせる。出力 impl2/c/ と impl2/meta/ は"
                             "モデルの生成物なので再現しない。"),
    "tools/impl2/triage.py": ("pilot の結果(LLM 生成物)を engine ごとに振り分ける(impl2/triage_*.json)。"
                              "入力が LLM の出力で、どの engine を回すかは人が選ぶ。"),
    # (E) 画像・動画の書き手(記事・README・Studio の素材)
    "tools/gen_banner.py": _IMAGE_REASON + (" C:/Windows/Fonts を読む。★帯の文言「731 2-D + 265 3-D」は"
                                            "ソースに直書きで、索引から数えていない(2026-10-07 時点で古い)。"),
    "tools/gen_view2026_thumbs.py": _IMAGE_REASON + (" docs/view2026/thumbs の JPEG/GIF。在ることと"
                                                     " 全展示ぶん揃うことは gen_view2026_pages の検査が見る。"),
    "tools/gen_hero_channels.py": _IMAGE_REASON + " C:/Windows/Fonts を読む。",
    "tools/gen_hero_ct.py": _IMAGE_REASON + " C:/Windows/Fonts を読む。",
    "tools/gen_hero_making_of.py": _IMAGE_REASON + " 手元の作業画像(C:/...)を素材にする。",
    "tools/gen_hero_materials.py": _IMAGE_REASON + " C:/Windows/Fonts を読む。",
    "tools/gen_hero_metals.py": _IMAGE_REASON + " C:/Windows/Fonts を読む。",
    "tools/gen_hero_photometric_stereo.py": _IMAGE_REASON + " C:/Windows/Fonts を読む。",
    "tools/gen_hero_structured_light.py": _IMAGE_REASON + " C:/Windows/Fonts を読む。",
    "tools/gen_hero_gif.py": _IMAGE_REASON + " README / Pages の扉絵 GIF(固定 seed、レンダリングが重い)。",
    "tools/gen_hero_relight.py": _IMAGE_REASON + " 6 灯レンダリング → GIF/MP4(重い)。",
    "tools/gen_still_life_turntable.py": _IMAGE_REASON + " ターンテーブル GIF/MP4(重い)。",
    "tools/gen_showcase_gifs.py": _IMAGE_REASON + " examples_3d/_gallery のショーケース GIF/MP4(重い)。",
    "tools/gen_inspection_gallery.py": _IMAGE_REASON + " C:/Windows/Fonts を読む。",
    "tools/gen_synth_samples.py": _IMAGE_REASON + (" studio_assets/sample_images の合成テクスチャ。手元では 2 回で"
                                                   "バイト一致だが、コミット済みの 4 ファイルと一致しない"
                                                   "(作った環境との差か古いかは未判定)。"),
    "tools/gen_blas_article_figs.py": _IMAGE_REASON + (" BLAS スレッド数の**実測**を図にする。★2026-10-07 まで"
                                                       "出力先が手元の絶対パスで、どの checkout から回しても"
                                                       "本線の図を書き換えていた(今は Path(__file__) から求める)。"),
    "tools/gen_evis_media.py": _IMAGE_REASON + " 入力は手元の evis 実験映像(EVIS_CHOPSTICK_DIR)。",
    "tools/gen_visionlab_video.py": _IMAGE_REASON + " 動画(GIF/MP4)。",
    "tools/gen_studio_screenshots.py": _IMAGE_REASON + " Studio(PySide6)を実際に起動して撮る。CI に画面は無い。",
    "assets/make_icon.py": _IMAGE_REASON + (" assets/fullseye.ico / fullseye_256.png。入力はコードだけなので、"
                                            "make_icon.py を変えない限り古びない。"),
    # (F) スパイクの記録(spikes/out_gallery/ はコミット済みの当時の証跡)
    "spikes/evis_walk_perception.py": _SPIKE_REASON,
    "spikes/studio_app.py": _SPIKE_REASON + " PySide6 の GUI を起動する。",
    "spikes/studio_gallery.py": _SPIKE_REASON,
    "spikes/viewer3d.py": _SPIKE_REASON + " Open3D が要る。",
    "spikes/viewer3d_demo.py": _SPIKE_REASON + " Open3D が要る。",
}

#: **そもそも生成器ではないもの。** `discover_generators()` は「ファイルを書く」
#: という粗い印で拾うので、ベンチ・門・公開スクリプト・実験も一緒に釣れる。
#: それらを黙って無視すると印を緩めることになり、本物の生成器まで漏れる ——
#: だから**釣れたものは全部ここに名前と理由を書いて外す**(印は緩めない)。
_OUT_REASON = "出力は out/(gitignore)で、コミット物を書かない。"
NOT_A_GENERATOR = {
    "tools/algo_gate.py": "門(algo 層の合否を出す)。出力は out/ へ。",
    "tools/bench_ops.py": "ベンチ。実測値なので回すたびに変わる。",
    "tools/bench_realtime.py": "ベンチ(実時間)。",
    "tools/bench_soak.py": "ベンチ(長時間)。",
    "tools/chain_fuzz.py": "ファザー。out/ に結果を落とす。",
    "tools/check_solution_json.py": "外部の採点器(TUM drivability-checker、WSL)を呼んで合否を JSON に書く。生成物は repo の外(FULLSEYE_COMMONROAD_DATA)。",
    "tools/chain_mine.py": "連鎖の探索(実験)。",
    "tools/ci_wheel_check.py": "門(wheel の完全性を配布物の側から数える)。",
    "tools/ledger_contracts.py": "門(型付き台帳の全 op の契約探針)。--write は直して台帳を縮めるときだけ手で回す(新しい違反は門が拒む)。",
    "tools/evolve_loop.py": "進化ループ(実験)。",
    "tools/preflight.py": "門(コミット前の一括確認)。",
    "tools/promote_gate.py": "門(昇格の可否)。",
    "tools/qiita_patch_overview.py": "公開スクリプト(Qiita への PATCH)。",
    "tools/qiita_post_poc.py": "公開スクリプト(Qiita への投稿)。",
    "tools/studio_ui_harness.py": "Studio の UI テスト用ハーネス。",
    "tools/i18n_status.py": "門(非日本語版に黙って混ざる日本語を数える)。",
    "tools/i18n_docs.py": ("門 + スタンプ(散文ドキュメントの訳が日本語から古びて"
                           "いないか)。--stamp が訳ファイルを書くが生成物ではない。"),
    "tools/_dn_merge.py": ("i18n 作業用の一時ヘルパ。DESIGN_NOTES の訳バッチを人が書く"
                           "訳の表 docs/i18n/design_notes.json に merge する(表は入力で"
                           "あって生成物ではない)。生成物は gen_design_notes が作る。"),
    "tools/_dn_verify_merge.py": ("i18n 作業用の一時ヘルパ。Agent が出した訳バッチの字種を"
                                  "検査してから _dn_merge と同じ表へ merge する。同上で"
                                  "生成物ではない。"),
    # ---- 2026-10-07: 列挙を広げて釣れた、生成器ではないもの ----
    "algo_codegen.py": "algo 層の C / Python を吐く道具。%s" % _OUT_REASON,
    "algo_difftest.py": "門(algo 層の差分テスト)。%s" % _OUT_REASON,
    "baseline.py": "S0 の段(進化パイプライン)。出力は work-graph の作業 dir(out/worklog)。",
    "evolve.py": "S1 の段(進化)。出力は work-graph の作業 dir(out/worklog)。",
    "robust.py": "多 seed の勝者選び(進化)。出力は work-graph の作業 dir(out/worklog)。",
    "codegen.py": "S2 の段(勝者からのコード生成)。出力は work-graph の作業 dir(out/worklog)。",
    "difftest.py": "S2 の段(backend 間の差分テスト = 門)。出力は work-graph の作業 dir(out/worklog)。",
    "report.py": "S1 の門(指標)。出力は work-graph の作業 dir(out/worklog)。",
    "graph_seed.py": "work-graph のジョブ定義を吐く。出力は raptor の作業 dir(repo の外)。",
    "sweep.py": "探索 1 周を work-graph に積む。出力は raptor の作業 dir(repo の外)。",
    "vloop_evolve.py": "実験(時間予算つき適応度)。%s" % _OUT_REASON,
    "bin_pick.py": "デモ(物理 + headless GIF)。%s" % _OUT_REASON,
    "pick_render.py": "デモ(物理 + headless GIF)。%s" % _OUT_REASON,
    "walk_physics.py": "デモ(四足歩行の物理)。%s" % _OUT_REASON,
    "world_render.py": "デモ(地形上の歩行 GIF)。%s" % _OUT_REASON,
    "event_camera.py": "センサーシミュのデモ。%s" % _OUT_REASON,
    "focus_stack.py": "センサーシミュのデモ。%s" % _OUT_REASON,
    "lidar_sim.py": "センサーシミュのデモ。%s" % _OUT_REASON,
    "polar_cam.py": "センサーシミュのデモ。%s" % _OUT_REASON,
    "sensor_fusion.py": "センサーシミュのデモ。%s" % _OUT_REASON,
    "stereo_sim.py": "センサーシミュのデモ。%s" % _OUT_REASON,
    "learn_evis.py": "強化学習(方策の学習)。%s" % _OUT_REASON,
    "learn_figure8.py": "強化学習(方策の学習)。%s" % _OUT_REASON,
    "evis_fullseye_bridge.py": "手元の evis 実験データを読むデモ。%s" % _OUT_REASON,
    "gsplat_animate.py": "3DGS パイプライン(torch / CUDA)。出力先は引数で渡す dir。",
    "gsplat_cli.py": "3DGS パイプライン(torch / CUDA)。出力先は引数で渡す dir。",
    "gsplat_sugar.py": "3DGS → メッシュ(torch / CUDA / Open3D)。出力先は引数で渡す dir。",
    "gsplat_train_native.py": "3DGS 学習(gsplat / CUDA)。出力先は引数で渡す dir。",
    "recipe_world_walk.py": "レシピ(unified op の手順)。出力先は引数で渡す dir(既定 world_walk_out/)。",
    "imgforensics.py": "ライブラリ。__main__ は op の一覧を表示するだけ。",
    "projmap.py": "ライブラリ(save_gif は呼び手がパスを渡す)。__main__ は数値の表を表示するだけ。",
    "sim_source.py": "ライブラリ(save_* は呼び手が dir を渡す)。__main__ はカメラ情報を表示するだけ。",
    "studio.py": "GUI アプリ(Studio)。保存は利用者の操作で、指定された場所へ。",
    "verify_auto.py": "門(auto op の機能ゲート)。結果 data/auto_functional_gate.json は gitignore。",
    "halcon_scrape.py": "取得スクリプト(ネットワーク)。出力 data/halcon_operators.json は gitignore の手元キャッシュ。",
    "tools/plateau_fetch.py": "取得スクリプト(HTTP Range で PLATEAU の zip から抜く)。出力先は repo の外。",
    "tools/exhibit_tile.py": "展示づくりの共通部品(ライブラリ)。__main__ は一時 dir に書く自己テスト。",
    "tools/fops_article/fops_lib.py": ("別 repo(onocollo-complete)の記事用の共通部品。★出力先が絶対パスで、"
                                       "import しただけで os.makedirs がその repo に走る。"),
    "tools/fops_article/fops_batch4.py": "別 repo(onocollo-complete)の記事の図。この repo には書かない。",
    "tools/fops_article/fops_eval1.py": "別 repo(onocollo-complete)の記事の図の定量評価。この repo には書かない。",
    "tools/fops_article/build_manifest.py": "別 repo(onocollo-complete)の記事の挿入目録。この repo には書かない。",
    "spikes/unified_api_spike.py": "API スパイク。imwrite は呼び手がパスを渡すメソッドで、__main__ は書かない。",
}

#: 生成器を**ファイルの側から**列挙する。CHAIN と EXCLUDED は人が書く表なので、
#: 放っておけば必ず現実から遅れる —— 実際 `gen_examples3d_doc` が漏れていた。
#: この関数と `unclassified()` を `tests/test_regen_all.py` が呼び、
#: **どちらの表にも無い生成器があればテストが落ちる**。新しい生成器を足した人は、
#: 「CHAIN に入れる」か「理由つきで EXCLUDED に入れる」かを迫られる。
#: どちらでもよいが、**黙って増やすことだけができない**。
#:
#: ★2026-10-07: 印も探す場所も狭すぎた。初版は ``open(..,"w")`` / ``write_text`` /
#: ``savefig`` / ``json.dump`` だけを ``tools/*.py``(直下のみ)で探していたので、
#:
#:   * **repo 直下の生成器が 1 本も見えなかった** —— ``samples.py``(docs/EXAMPLES.md が
#:     「67-op」のまま)、``references.py``(「153 operators」)、``dispositions.py``、
#:     ``lib_coverage.py``(885 op のまま)、``honest_summary.py`` …。``imgevolve.py`` と
#:     ``catalog.py`` だけが手で足されていた —— 手で足す方式は、足し忘れを拾えない。
#:   * **画像の書き手が 1 本も釣れなかった** —— PIL の ``.save``、imageio の
#:     ``mimwrite``、``write_bytes``、Fullseye 自身の ``write_video`` / ``save_gif`` …。
#:     ``gen_banner`` の PNG は「731 2-D + 265 3-D」と書いたまま古びている。
#:   * ``tools/impl2/`` など**下の階層**も見ていなかった(docs/op_*.json の台帳)。
#:
#: 印を広げれば門・デモ・ライブラリも釣れる。それは構わない —— **釣れたものは全部
#: 上の表に理由つきで載せる**(印は緩めない)。
_WRITES = re.compile(
    r'open\([^)]*["\']w["\']|\.write_text\(|\.write_bytes\(|savefig\(|json\.dump\('
    r'|\.save\(|mimwrite\(|mimsave\(|imwrite\(|\.to_csv\(|\bnp\.save(?:z|z_compressed)?\('
    r'|\b(?:write|save)_(?:video|gif|png|image|animation|flipbook|exhibit|mesh|points|volume|wav|ply)\w*\(')
#: 単体で走るスクリプトの印。repo 直下の 470 本の大半はライブラリで、``.save(`` や
#: ``write_text`` を**呼び手がパスを渡す関数**として持つだけ —— ``__main__`` の無い
#: モジュールは単体で走らないので生成器になれない。
_MAIN = re.compile(r'^if __name__ == ["\']__main__["\']', re.M)

#: 再帰的に歩くディレクトリ(中の .py は印だけで拾う)。
#:   * ``tools``  —— 生成器の本拠(``tools/impl2/`` の探針、``tools/fops_article/`` も)
#:   * ``assets`` —— ``make_icon.py`` がコミット済みのアイコンを書く
#:   * ``spikes`` —— ``spikes/out_gallery/`` に**コミット済み**の図を書く
#: **歩かない場所と理由**(どれも「コミット物を書く生成器が無い」ことを確かめてある):
#:   * ``tests/``                 —— テスト(書くのは tmp_path)
#:   * ``examples/`` ``examples_3d/`` —— PoC。図は ``examplefig`` が FULLSEYE_FIGURE_DIR か
#:     gitignore 済みの ``out/figures/`` にだけ書く。展示の図は gen_op_figures /
#:     build_exhibits(EXCLUDED)経由、目次は gen_wingpoc_gallery(CHAIN)
#:   * ``fullseye/``              —— パッケージ本体。__main__ を持つ書き手は ``rag_setup``
#:     (利用者の ~/.claude/skills へ導入)だけ
#:   * ``rust/`` ``build/`` ``.wheelenv/`` —— Python の生成器が無い / ビルド成果物
_RECURSE_DIRS = ("tools", "assets", "spikes")
_SKIP_FILES = {"tools/regen_all.py"}


def _read_src(path: str) -> str:
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def discover_generators() -> list[str]:
    """ファイルを書くスクリプトを**ディレクトリの側から**全部列挙する(repo 相対・``/`` 区切り)。

    * repo 直下: ``_WRITES`` に当たり、**かつ** ``__main__`` を持つ .py
    * ``_RECURSE_DIRS`` の下(再帰): ``_WRITES`` に当たる .py

    順序は名前でソートして固定する(``os.walk`` / ``os.listdir`` の順は環境で違う)。
    """
    found = []
    # ★`tools/` の外にある生成物。`tools/*.py` を歩くだけでは**永久に見つからない**
    #   位置にあり、実際 `docs/OP_INDEX.json` を取りこぼしていた。
    for name in sorted(os.listdir(_ROOT)):
        if name.endswith(".py"):
            src = _read_src(os.path.join(_ROOT, name))
            if _WRITES.search(src) and _MAIN.search(src):
                found.append(name)
    for top in _RECURSE_DIRS:
        base = os.path.join(_ROOT, top)
        if not os.path.isdir(base):
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = sorted(d for d in dirnames if d != "__pycache__")
            for name in sorted(filenames):
                if not name.endswith(".py"):
                    continue
                rel = os.path.relpath(os.path.join(dirpath, name), _ROOT).replace(os.sep, "/")
                if rel in _SKIP_FILES:
                    continue
                if _WRITES.search(_read_src(os.path.join(dirpath, name))):
                    found.append(rel)
    return sorted(found)


def unclassified() -> list[str]:
    """CHAIN にも EXCLUDED にも入っていない生成器。"""
    in_chain = {args[0] for args, _ in CHAIN}
    return [g for g in discover_generators()
            if g not in in_chain and g not in EXCLUDED
            and g not in NOT_A_GENERATOR]


def _run(args: list[str]) -> int:
    return subprocess.run([sys.executable] + args, cwd=_ROOT).returncode


def _dirty() -> list[str]:
    r = subprocess.run(["git", "status", "--porcelain"], cwd=_ROOT,
                       capture_output=True, text=True, errors="replace")
    return [ln for ln in r.stdout.splitlines() if ln.strip()
            # 毎ターン自動で書き換わるので、回し忘れの証拠にはならない。
            and not ln.endswith("docs/SESSION_SUMMARY.md")]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                    help="作り直したあと作業ツリーがきれいでなければ exit 1")
    ap.add_argument("--list", action="store_true", help="順序を見るだけ")
    a = ap.parse_args(argv)

    if a.list:
        for i, (args, what) in enumerate(CHAIN, 1):
            print("%2d. %-42s %s" % (i, " ".join(args), what))
        print("\n--- CHAIN に入れないもの(回さなくてよい、ではなく門にできない) ---")
        for what in sorted(EXCLUDED):
            print("  %-40s %s" % (what, EXCLUDED[what][:70]))
        rest = unclassified()
        if rest:
            print("\n★どちらの表にも無い生成器(分類してください): %s" % ", ".join(rest))
        return 0

    before = _dirty() if a.check else []
    for args, what in CHAIN:
        print("\n=== %s  (%s)" % (" ".join(args), what))
        rc = _run(args)
        if rc != 0:
            print("失敗: %s (exit %d) —— ここで止める" % (" ".join(args), rc))
            return rc

    if not a.check:
        print("\n生成物を作り直した。`git status` で差分を確認すること。")
        return 0

    after = _dirty()
    new = [ln for ln in after if ln not in before]
    if new:
        print("\n★生成物がコミット済みと食い違っていた(= どれかを回し忘れていた):")
        for ln in new[:40]:
            print("   " + ln)
        if len(new) > 40:
            print("   …ほか %d 本" % (len(new) - 40))
        return 1
    print("\n生成物はすべて最新(回し忘れ無し)。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
