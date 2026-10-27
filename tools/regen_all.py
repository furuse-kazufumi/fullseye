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

**この鎖に入れないもの**: ``tools/build_view2026_viewers.py``(ViEW2026 の「触って見る」7 本)。LiDAR の
実データ(``FULLSEYE_DATA_DIR`` 配下、リポジトリに無い)が要るので、無い環境で ``--check`` が赤になる。
出力(``docs/view2026/viewers/*.html``)を変える回は、手で回して commit する。

``--check`` は**強い不変条件**を見る: 全部作り直したあとの作業ツリーが
きれいであること。個々の drift 検査の総和より広く、「回し忘れ」を 1 つ残らず拾う。
"""
from __future__ import annotations

import argparse
import fnmatch
import functools
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
    # ★`tools/` の外にある唯一の生成物。だから取りこぼしていた ——
    # 生成器を `tools/*.py` で探す限り、これは永久に見つからない。
    # ★2026-10-15: 16 番目から 2 番目へ上げた。入力は registry だけ(他の段の生成物を
    #   読まない)なのに、gen_capabilities_index と gen_trust_block がこれを**先に**読んでいた ——
    #   op を足すマージで索引に本線側を取ると、古い索引に新しい op が無くて止まる
    #   (統合作業で `imgevolve.py index` を手で先に回して回避していた)。順序は
    #   下の OUTPUTS / READS から `order_violations()` が検査する。
    (["imgevolve.py", "index"], "docs/OP_INDEX.json(レジストリの機械可読索引)"),
    (["tools/halcon_compat_profile.py", "--manifest"],
     "HALCON 互換プロファイル + 比較試験 manifest + HALCON_PARITY の H15 節"),
    (["tools/opdocs.py", "all"],
     "op ノート + SAMPLES + TOC + RAG skill のコーパス地図 + Studio help HTML(6 言語)"),
    (["tools/gen_op_catalog.py"], "1 ページの op カタログ"),
    (["tools/gen_capabilities_index.py"], "能力索引(docs/capabilities/*.md から)"),
    (["tools/gen_hardening_index.py"], "堅牢性台帳"),
    # 入力は公開 op のモジュールの原文だけ(他の段の生成物を読まない)。
    (["tools/audit_fallbacks.py"], "失敗と空結果の棚卸し docs/fallback_audit.json(H16、--check で drift)"),
    (["tools/gen_maturity.py"], "成熟度台帳(生成物 + 機械可読 JSON)"),
    # ★展示館より**先**に回す —— 生成器は見出しに収蔵番号を出すので、
    #   未発行の展示が 1 つでもあると BuildError で止まる。
    (["tools/gen_exhibit_numbers.py"], "収蔵番号の発行(追記のみ・既存は動かさない)"),
    (["tools/gen_wingpoc_gallery.py"], "PoC 展示館(総合案内 + 棟、ja/en)"),
    (["tools/gen_examples_readme.py"], "examples/README.md"),
    (["tools/gen_oss_landscape.py"], "既存 OSS の地図(docs/literature/oss_landscape.json → OSS_LANDSCAPE.md)"),
    (["tools/gen_view2026_pages.py"], "docs/view2026/**/index.md(論文の QR の行き先、正本は exhibits.json)"),
    # gen_maturity の後(maturity.json を読む)、索引の後(docs/OP_INDEX.json と照合する)。
    # README*.md は gen_docs_index_ops も書くが、マーカーが別なので互いの中身には触れない
    # (ORDER_EXEMPT)。
    (["tools/gen_trust_block.py"],
     "README.md + docs/README*.md の trust ブロックと docs/OP_COUNT_HISTORY.md(測定データ docs/*.json から)"),
    (["tools/gen_examples3d_doc.py"], "docs/EXAMPLES_3D.md(3-D 例の一覧)"),
    (["tools/gen_sensor_playbook.py"], "センサー playbook"),
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
    # ★2026-10-15: `--md` が無く、**何も書いていなかった**(要約を標準出力に出すだけ)。
    #   docs/CONVERSION_MATRIX.md は 2026-09-02 の「型 59 / 変換ペア 164」のまま古び、
    #   --check は「書かない段」を drift として見られないので 6 週間通っていた。
    #   いまは `trace_problems()` が「宣言した出力に触れもしない段」を拒む。
    (["tools/conversion_matrix.py", "--md", "docs/CONVERSION_MATRIX.md"],
     "docs/CONVERSION_MATRIX.md(表現の変換表)"),
    (["tools/gen_design_notes.py"], "設計判断集(ソースの ★ から 6 言語)"),
    # ★2026-10-15: 13 番目から最後の方へ下げた。docmap が docs/*.md の**題**を読むので、
    #   題を持つ生成物(OPERATORS / REFERENCES / EXAMPLES / EXAMPLES_3D / SENSOR_PLAYBOOK /
    #   CONVERSION_MATRIX / DESIGN_NOTES*)を書く 7 段すべてより後でなければならない ——
    #   以前はその 7 段より前にあり、題が変わると 2 回回さないと揃わなかった。
    # 文献層の本体はコーパスが要る(EXCLUDED)が、「op ノート N 本」の件数は docs/ops を数えれば直せる。
    # docs/ops を書く opdocs の後、題を読む docmap(gen_docs_index_ops)の前。
    (["tools/gen_literature_counts.py"], "docs/literature の件数(op ノートの枚数)を実ファイルから打ち直す"),
    (["tools/gen_docs_index_ops.py"], "docs/README*.md の ops / poc / docmap ブロック"),
    # 手書き部分にある実装由来の数だけを最後に更新する。RAG ガイドの訳は、正本・訳の
    # 差分が数値だけだと確認できた場合に限り source-sha も更新する。
    (["tools/gen_doc_counts.py"], "README の registry 件数 + AI_RAG_GUIDE の op ノート件数"),
    # 索引と op ノートの後(複製するので)。
    (["tools/gen_mcp_data.py"], "fullseye/data/OP_INDEX.json + OP_NOTES.json(MCP が wheel から読む複製)"),
]

#: ---- 段の依存表(2026-10-15)------------------------------------------------------
#:
#: **順序の穴**: `gen_capabilities_index`(4 番目)が、16 番目でやっと作り直される
#: `docs/OP_INDEX.json` を先に読んでいた。op を足すマージで索引に本線側を取ると止まる。
#: 洗い出すと同じ型の逆順が他に 2 つ(`gen_trust_block` ← 索引、`gen_docs_index_ops` ←
#: 後ろの 7 段)と、何も書かない段が 1 つ(`conversion_matrix`)あった。
#: 「順序が意味を持つ」とコメントに書いてあっても、**何を読むかが表に無ければ順序は検査できない**。
#:
#: そこで各段の「書くもの」「読む(他の段の)生成物」を表にし、
#:
#:   * `order_violations()` —— 読む生成物を書く段が**後ろ**にあれば違反(静的。
#:     tests/test_regen_all.py が毎回見る)
#:   * `trace_problems()`   —— 鎖を回すたびに各段を audit hook の下で走らせ、実際に
#:     open したパスと表を突き合わせる(表に無い読み書き / 読まなくなった宣言 /
#:     宣言した出力に触れもしない段 を拒む)。CI の `regen_all --check` で効く。
#:
#: 表は手で書くが、**実コードとずれれば次の regen_all が赤になる**。
#: パターンは fnmatch(`*` は `/` も跨ぐ)。repo 相対・`/` 区切り。
OUTPUTS = {
    "gen_auto_specs_data.py": ["auto_specs_data.py"],
    "imgevolve.py": ["docs/OP_INDEX.json"],
    "tools/halcon_compat_profile.py": ["docs/halcon_compat_profile.json",
                                        "docs/halcon_comparison_manifest.json",
                                        "docs/HALCON_PARITY.md"],
    "tools/opdocs.py": ["docs/ops/*", "studio_assets/op_help/*", "docs/i18n/help_coverage.json",
                        "fullseye/skill_template/SKILL.md", "skills/fullseye-ops/SKILL.md"],
    "tools/gen_op_catalog.py": ["docs/OP_CATALOG.md", "fullseye/OP_CATALOG.md"],
    "tools/gen_capabilities_index.py": ["docs/CAPABILITIES.md", "docs/CAPABILITIES.*.md"],
    "tools/gen_hardening_index.py": ["docs/HARDENING.md", "docs/HARDENING.*.md"],
    "tools/audit_fallbacks.py": ["docs/fallback_audit.json"],
    "tools/gen_maturity.py": ["docs/MATURITY.md", "docs/maturity.json"],
    "tools/gen_exhibit_numbers.py": ["docs/articles/exhibits/exhibit_numbers.json"],
    "tools/gen_wingpoc_gallery.py": ["docs/articles/exhibits/wingpoc.*.md",
                                     "docs/articles/fullseye_poc_museum_qiita_*.md",
                                     # 棟ごとの記事(fullseye_poc_museum_<棟>_qiita_<言語>.md)も同じ段が書く
                                     "docs/articles/fullseye_poc_museum_*_qiita_*.md",
                                     "docs/articles/assets/poc/_hero_montage.jpg"],
    "tools/gen_examples_readme.py": ["examples/README.md"],
    "tools/gen_oss_landscape.py": ["docs/literature/OSS_LANDSCAPE.md"],
    "tools/gen_view2026_pages.py": ["docs/view2026/index.md", "docs/view2026/*/index.md"],
    "tools/gen_trust_block.py": ["README.md", "docs/README.md", "docs/README.*.md",
                                 "docs/OP_COUNT_HISTORY.md"],
    "tools/gen_examples3d_doc.py": ["docs/EXAMPLES_3D.md"],
    "tools/gen_sensor_playbook.py": ["docs/SENSOR_PLAYBOOK.md", "fullseye/SENSOR_PLAYBOOK.md"],
    "catalog.py": ["docs/OPERATORS.md"],
    "dispositions.py": ["docs/OP_DISPOSITION.json"],
    "references.py": ["docs/REFERENCES.md"],
    "samples.py": ["docs/EXAMPLES.md"],
    "tools/conversion_matrix.py": ["docs/CONVERSION_MATRIX.md"],
    "tools/gen_design_notes.py": ["docs/DESIGN_NOTES.md", "docs/DESIGN_NOTES.*.md", "docs/design_notes.json"],
    "tools/gen_docs_index_ops.py": ["docs/README.md", "docs/README.*.md", "docs/articles/README.md"],
    "tools/gen_doc_counts.py": ["docs/README.md", "docs/README.*.md",
                                 "docs/AI_RAG_GUIDE.md", "docs/AI_RAG_GUIDE.*.md"],
    "tools/gen_mcp_data.py": ["fullseye/data/OP_INDEX.json", "fullseye/data/OP_NOTES.json",
                              "fullseye/data/OP_SEARCH.json", "fullseye/data/op_knob.json"],
    # 2026-10-23: 手で列挙していて #116 の文献 4 本が漏れ、regen が exit 1(--check は緑)だった。
    #   件数を打ち直す文献ノートの実ファイルと合わせる(OSS_LANDSCAPE.md は gen_oss_landscape.py の生成物、
    #   oss_landscape_notes.md は手書きの注で、どちらもこの段は書かない)。
    "tools/gen_literature_counts.py": ["docs/literature/INDEX.md",
                                       "docs/literature/convergent_numerics_light_transport.md",
                                       "docs/literature/driving_simulation.md",
                                       "docs/literature/electron_microscopy.md",
                                       "docs/literature/industrial_optical_sensing.md",
                                       "docs/literature/manufacturing_processes.md",
                                       "docs/literature/mech_design.md",
                                       "docs/literature/mechatronics_parts.md",
                                       "docs/literature/optical_metrology.md",
                                       "docs/literature/sensitivity_uq_calibration.md",
                                       "docs/literature/sensor_simulation.md"],
}

#: ---- 書く**かもしれない**出力(2026-10-18)--------------------------------------------
#:
#: OUTPUTS は「この段が必ず触れる」宣言で、`trace_problems()` は触れもしない宣言を拒む。ところが
#: **差分があるときだけ書く**出力がある —— `gen_wingpoc_gallery` は図の PNG より古いときだけ
#: `<図>_720.jpg` のサムネを書き直す。統合で 2 回続けて同じ症状を踏んだ: 新しい PoC の図を初めて
#: 載せる / 図を差し替えると「OUTPUTS に無いファイルを書いた」で止まり、OUTPUTS に足すと次の回は
#: 「触れもしない」で止まる(2 回目の regen でやっと通る)。
#:
#: ここに挙げたパターンは**書いてもよいが、書かなくてもよい**(0 件を許す)。書き込みの許可と
#: 順序の検査(`order_violations`)には効くが、「触れもしない」の検査と「追跡ファイルに当たる」の
#: 検査には使わない。抜け道にしないよう、パターンごとに理由を書き(`table_problems` が短い理由・
#: 鎖に無い段・ファイル名の部分が `*` だけのパターン・自分の OUTPUTS と重なるパターンを拒む)、
#: tests/test_regen_all.py が「消すと 1 回目の regen が止まる」ことを探針で見る。
MAY_OUTPUTS = {
    "tools/gen_wingpoc_gallery.py": {
        "docs/articles/assets/poc/*_720.jpg":
            ("幅 720 px の JPEG サムネ。元の図(PNG)より古いか無いときだけ書く(_thumb)ので、"
             "図を初めて載せた回・差し替えた回にしか書き込みが起きない。"),
    },
}


#: 各段が読む、**他の段の**生成物(自分の出力を読み比べるのは書かなくてよい)。
#: 2026-10-15 に audit hook の実測(全 23 段)から起こした。
READS = {
    "imgevolve.py": ["fullseye/data/OP_INDEX.json", "fullseye/data/op_knob.json"],
    "tools/halcon_compat_profile.py": ["docs/OP_INDEX.json"],
    "tools/gen_capabilities_index.py": ["docs/OP_INDEX.json"],
    "tools/gen_wingpoc_gallery.py": ["docs/articles/exhibits/exhibit_numbers.json"],
    "tools/gen_trust_block.py": ["docs/OP_INDEX.json", "docs/maturity.json",
                                 "docs/README.md", "docs/README.*.md"],
    "tools/gen_design_notes.py": ["auto_specs_data.py"],
    "tools/gen_docs_index_ops.py": [
        "docs/ops/*", "docs/OP_CATALOG.md", "docs/CAPABILITIES.md", "docs/CAPABILITIES.*.md",
        "docs/HARDENING.md", "docs/HARDENING.*.md", "docs/MATURITY.md",
        "docs/articles/exhibits/wingpoc.*.md", "docs/articles/fullseye_poc_museum_qiita_*.md", "docs/articles/fullseye_poc_museum_*_qiita_*.md",
        "docs/literature/*.md",                       # 文献ノート全部(2026-10-23: 列挙だと増えた分が READS から漏れる)
        "docs/README.md", "docs/README.*.md", "docs/OP_COUNT_HISTORY.md",
        "docs/EXAMPLES_3D.md", "docs/SENSOR_PLAYBOOK.md", "docs/OPERATORS.md",
        "docs/REFERENCES.md", "docs/EXAMPLES.md", "docs/CONVERSION_MATRIX.md",
        "docs/HALCON_PARITY.md",
        "docs/DESIGN_NOTES.md", "docs/DESIGN_NOTES.*.md",
        "docs/AI_RAG_GUIDE.md", "docs/AI_RAG_GUIDE.*.md"],
    "tools/gen_mcp_data.py": ["docs/OP_INDEX.json", "docs/ops/*"],
    "tools/gen_literature_counts.py": ["docs/ops/*"],
    "tools/gen_doc_counts.py": ["docs/README.md", "docs/README.*.md"],
}

#: 順序の例外 —— 読むが、後ろの段が書いてもよいもの。(段, READS のパターン) → 理由。
_SHARED_README = ("README*.md は gen_trust_block(trust ブロック)と gen_docs_index_ops(ops / poc / "
                  "docmap ブロック)が同じファイルの**別のマーカー区間**を読み替える。自分の区間しか"
                  "書き換えないので、どちらが先でも 1 回で揃う。gen_docs_index_ops は "
                  "OP_COUNT_HISTORY.md を読むので trust が先。")
_SHIPPED_DIAG = ("同梱の複製は `imgevolve.py index` の**標準出力の診断**(この環境と同梱索引の差)に"
                 "だけ使い、docs/OP_INDEX.json の中身には入らない。複製を作る gen_mcp_data は"
                 "索引を読むので後ろでなければならず、ここは構造的に循環する。")
_DOCMAP_COUNT = ("gen_docs_index_ops は文書地図に載せるため AI_RAG_GUIDE の題だけを読む。"
                 "gen_doc_counts が後で変更するのは本文中の件数だけなので、地図の生成結果には影響しない。")
ORDER_EXEMPT = {
    ("tools/gen_trust_block.py", "docs/README.md"): _SHARED_README,
    ("tools/gen_trust_block.py", "docs/README.*.md"): _SHARED_README,
    ("imgevolve.py", "fullseye/data/OP_INDEX.json"): _SHIPPED_DIAG,
    ("imgevolve.py", "fullseye/data/op_knob.json"): _SHIPPED_DIAG,
    # gen_doc_counts は gen_docs_index_ops が自分のマーカー区間を更新した後、同じ
    # README の手書き冒頭にある registry 件数だけを更新する。
    ("tools/gen_docs_index_ops.py", "docs/README.md"): _SHARED_README,
    ("tools/gen_docs_index_ops.py", "docs/README.*.md"): _SHARED_README,
    ("tools/gen_docs_index_ops.py", "docs/AI_RAG_GUIDE.md"): _DOCMAP_COUNT,
    ("tools/gen_docs_index_ops.py", "docs/AI_RAG_GUIDE.*.md"): _DOCMAP_COUNT,
}

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
    "tools/build_pulseox_anim3d.py": ("パルスオキシメータの二波長吸収の動く 3-D 教材(docs/view2026/anim3d/pulseox_anim3d.html)。"
                                       "`py -3.11 tools/anim3d_i18n.py --build build_pulseox_anim3d --out docs/view2026/anim3d/pulseox_anim3d.html` で書く"
                                       "(翻訳表 tools/anim3d_i18n_tables/build_pulseox_anim3d.json)。門は tests/test_anim3d_pulseox_2026_10_26.py。"),
    "tools/check_page_overflow.py": ("門(生成器ではない): pocviewer のページを幅 390 px の iframe に入れて headless Chrome で開き、全タブ × 全言語の"
                                     "横はみ出しを測る。書くのは一時フォルダの計測用の写しだけで、repo には何も書かない。Chrome が要るので手で回す"
                                     "(tests/test_itokawa_page_overflow_2026_10_25.py、Chrome が無ければ skip)。"),
    "tools/build_itokawa_anim3d.py": ("小惑星イトカワの重力の動く 3-D の教材(docs/anim3d/itokawa_gravity.html)。"
                                      "pocviewer.write_viewer で書く手回しの生成物で、polyhedron_gravity を頂点 2.5 万個 × 面 4.9 万枚で"
                                      "回すので数分かかる(結果は out/ に入力のハッシュで保存)。commit するページは 8 言語版で、"
                                      "`py -3.11 tools/anim3d_i18n.py --build build_itokawa_anim3d --out docs/anim3d/itokawa_gravity.html` で書く"
                                      "(翻訳表 tools/anim3d_i18n_tables/build_itokawa_anim3d.json)。門は tests/test_itokawa_anim3d.py と "
                                      "tests/test_anim3d_i18n_itokawa_2026_10_25.py。"),
    "tools/import_itokawa_shape.py": ("イトカワの形状モデル(NASA PDS SBN の Gaskell Q = 64、CC0 1.0)の取り込み。入力の原本 ver64q.tab は"
                                      "repo の外で手で取得する(取得物は untrusted として専用の空ディレクトリに置く)ので CI では作れない —— "
                                      "SHA-256 を照合して data/itokawa_shape/gaskell_q64.npz を書き、出典と改変は同じ場所の README.md に書く。"),
    "tools/gen_plateau_venue.py": "ViEW2026 会場の建物の npz(国土交通省 PLATEAU 横浜市 2020 の CityGML LOD2、PDL1.0 / CC BY 4.0 互換)。入力の原本(タイル 2 枚、計 46 MB)は repo の外で手で取得し、信頼しないデータとして -I で読むので CI では作れない —— 小さな npz を data/plateau_yokohama/ に commit し、出典・加工の内容は同じ場所の README.md に書く。門(measuredHeight と生の座標の箱)は道具の中で回り、外れたら書かない。",
    "tools/build_gaussbonnet_anim3d.py": ("離散 Gauss–Bonnet の動く 3-D の教材(docs/anim3d/gauss_bonnet.html)。pocviewer.write_viewer で書く手回しの"
                                          "生成物(3 MB)。commit するページは 8 言語版で、`py -3.11 tools/anim3d_i18n.py --build build_gaussbonnet_anim3d"
                                          " --out docs/anim3d/gauss_bonnet.html` で書く(翻訳表 tools/anim3d_i18n_tables/build_gaussbonnet_anim3d.json)。"
                                          "門は tests/test_anim3d_gaussbonnet_2026_10_26.py と tests/test_anim3d_i18n_gaussbonnet_2026_10_26.py。"),
    "tools/import_gaussbonnet_meshes.py": ("離散 Gauss–Bonnet の教材が読むメッシュの取り込み(data/gaussbonnet/*.npz)。穴 2 つ・3 つの合成は marching cubes"
                                           "(scikit-image、任意の依存)、恐竜の骨格の走査(CC0)の原本 GLB は repo の外で手で取得する(SHA-256 を照合)"
                                           "ので CI では作れない。出典と改変は data/gaussbonnet/README.md。"),
    "tools/build_organvol_anim3d.py": ("臓器の体積と球形度の動く 3-D の教材(docs/anim3d/organ_volume.html)。"
                                       "`py -3.11 tools/anim3d_i18n.py --build build_organvol_anim3d --out docs/anim3d/organ_volume.html` で書く"
                                       "(翻訳表 tools/anim3d_i18n_tables/build_organvol_anim3d.json)。門は tests/test_anim3d_organvol_2026_10_26.py と "
                                       "tests/test_anim3d_i18n_organvol_2026_10_26.py。"),
    "tools/import_bodyparts3d_organs.py": ("BodyParts3D 4.0(99 % 削減版、CC BY 4.0)の 6 臓器の取り込み。原本の zip は配布しないので"
                                           "回せない。縫い目の頂点を溶接して data/bodyparts3d/*.npz を書き、出典と改変は同じ場所の README.md に書く。"),
    "tools/build_satgsd_anim3d.py": ("衛星の地上分解能と回折の動く 3-D の教材(docs/view2026/anim3d/satellite_gsd_anim3d.html)。"
                                     "`py -3.11 tools/anim3d_i18n.py --build build_satgsd_anim3d --out docs/view2026/anim3d/satellite_gsd_anim3d.html` で書く"
                                     "(翻訳表 tools/anim3d_i18n_tables/build_satgsd_anim3d.json)。門は tests/test_anim3d_satgsd_2026_10_26.py。"),
    "tools/build_ship_anim3d.py": ("排水量・浮心・メタセンタ高さの動く 3-D 教材(docs/view2026/anim3d/ship_stability_anim3d.html)。"
                                  "`py -3.11 tools/anim3d_i18n.py --build build_ship_anim3d --out docs/view2026/anim3d/ship_stability_anim3d.html` で書く"
                                  "(翻訳表 tools/anim3d_i18n_tables/build_ship_anim3d.json)。門は tests/test_anim3d_ship_2026_10_27.py。"),
    "tools/build_startrk_anim3d.py": ("合成星野から衛星姿勢を推定する動く 3-D の教材(docs/view2026/anim3d/star_tracker_anim3d.html)。"
                                     "`py -3.11 tools/anim3d_i18n.py --build build_startrk_anim3d --out docs/view2026/anim3d/star_tracker_anim3d.html` で書く"
                                     "(翻訳表 tools/anim3d_i18n_tables/build_startrk_anim3d.json)。門は tests/test_anim3d_startrk_2026_10_26.py。"),
    "tools/build_shadow_anim3d.py": ("冬至の会場周辺の日影を追う動く 3-D 教材(docs/view2026/anim3d/venue_shadow_anim3d.html)。"
                                     "`py -3.11 tools/anim3d_i18n.py --build build_shadow_anim3d --out docs/view2026/anim3d/venue_shadow_anim3d.html` で書く"
                                     "(翻訳表 tools/anim3d_i18n_tables/build_shadow_anim3d.json)。門は tests/test_anim3d_shadow_2026_10_27.py。"),
    "tools/build_rail_anim3d.py": ("レールの頭頂摩耗と軌間を光切断で測る動く 3-D 教材(docs/view2026/anim3d/rail_light_section_anim3d.html)。"
                                   "`py -3.11 tools/anim3d_i18n.py --build build_rail_anim3d --out docs/view2026/anim3d/rail_light_section_anim3d.html` で書く"
                                   "(翻訳表 tools/anim3d_i18n_tables/build_rail_anim3d.json)。門は tests/test_anim3d_rail_2026_10_26.py。"),
    "tools/build_tablet_anim3d.py": ("合成錠剤の外観検査の動く 3-D 教材(docs/view2026/anim3d/tablet_inspection_anim3d.html)。"
                                     "`py -3.11 tools/anim3d_i18n.py --build build_tablet_anim3d --out docs/view2026/anim3d/tablet_inspection_anim3d.html` で書く"
                                     "(翻訳表 tools/anim3d_i18n_tables/build_tablet_anim3d.json)。門は tests/test_anim3d_tablet_2026_10_26.py。"),
    "tools/build_gsplat_pages.py": ("docs/gsplat/ の 3DGS の商品ビューアとカタログ(examples/gsplat_product_viewer.py の build)。"
                                    "marching cubes に scikit-image(任意の依存)が要り、5 品の 3DGS 化とサムネイルの numpy 描画で"
                                    "1 分ほどかかり、出力は 1 本数 MB —— 鎖に入れず、ページを変える回は手で回して commit する。"),
    "tools/build_saltxrd_anim3d.py": ("塩の結晶の粉末 X 線回折の動く 3-D の教科書(docs/view2026/anim3d/salt_xrd_anim3d.html)。"
                                        "pocviewer.write_viewer で書く手回しの生成物(2.5 MB、pxrd の op を 4 題材ぶん回す)。"
                                        "出力を変えたら手で回して commit する。門は tests/test_anim3d_saltxrd_2026_10_26.py。"
                                        "ページは 8 言語版で、`py -3.11 tools/anim3d_i18n.py --build build_saltxrd_anim3d"
                                        " --out docs/view2026/anim3d/salt_xrd_anim3d.html` で書く(生成器を直接回すと ja/en だけに戻る)。"
                                        "表は tools/anim3d_i18n_tables/、一致は同じテストが見る。"),
    "tools/anim3d_i18n.py": ("動く 3-D の作例を 8 言語にする翻訳の層。作例の main() を走らせて仕様を横取りするので"
                             "1 本 10 秒前後かかり、作例(枝ごとに 15 本ほど)が増えるほど長くなる —— 鎖に入れず、"
                             "docs/view2026/anim3d/*.html は `--build <作例> --out ...` を手で回して commit する。"
                             "8 言語そろうことは gen_view2026_pages の検査、翻訳表が今の作例の文字列と合うことは"
                             " tests/test_anim3d_i18n_2026_10_25.py が見る。--missing の JSON は訳す作業用で repo の外へ。"),
    "tools/build_view2026_viewers.py": ("ViEW2026 の「触って見る」ビューア 7 本(docs/view2026/viewers/*.html)。"
                                        "LiDAR の実データ(FULLSEYE_DATA_DIR、repo の外)が要り、無い CI では作れない"
                                        " —— 手で回して commit し、`--check` で命令と配列の健全さを見る(本体の docstring にも明記)。"
                                        "2026-10-25 まで _WRITES が write_viewer( を拾えず、どの表にも載っていなかった。"),
    "tools/fops_article/gen_ai_inputs.py": ("記事用の入力写真を Gemini で作る(GEMINI_API_KEY を読み、外部 API を呼ぶ)。"
                                            "出力は tools/fops_article/sample_sources_ai/ —— 生成のたびに絵が変わるので CI では回さない。"
                                            "2026-10-25 まで open(.., \"wb\") を拾えず、どの表にも載っていなかった。"),
    "tools/audit_nan_inputs.py": ("全登録 op を別プロセスで基準、NaN、+inf の順に実測し、"
                                  "3 分を大きく超えるため通常の再生成鎖には入れない。"
                                  "docs/nan_input_audit.json と docs/NAN_INPUT_AUDIT.md は手動で更新する。"),
    "tools/merge_test_durations.py": "CI の片割りの重み(.test_durations)。入力は CI の run が残す所要時間の artifact(repo の外)なので手元では作れない —— 取ってきた artifact を合流して commit する。中身は実測値で、回すたびに変わる。",
    "tools/seed_test_durations.py": "同じ .test_durations の初回の穴埋め(未計測の試験を平均値で仮置き)。最初の 1 回だけの道具で、以後は merge_test_durations.py の実測が置き換える。",
    "tools/gen_thin_film_real.py": "薄膜 PoC の実測データ(Zenodo 13753754・figshare 23285603、どちらも CC BY 4.0)の抜き出し。入力の原本(xlsx・写真、計 60 MB)は repo の外で手で取得するので CI では作れない —— 抜き出した小さな表と縮小写真を data/thin_film_real/ に commit し、出典と改変は同じ場所の README.md に書く。",
    "tools/gen_oct_real.py": "工業用 OCT の PoC の実測データ(Liverpool Research Data Catalogue 126、CC BY 4.0)の抜き出し。入力の原本(.mat の zip、61 MB)は repo の外で手で取得するので CI では作れない —— A ラインを等間隔に 100 本ずつ抜いた小さな npz を data/oct_real/ に commit し、出典と改変は同じ場所の README.md に書く。",
    "tools/gen_xray_tables.py": "材料表の X 線の列(materials_xray_data.py)。入力は NIST SRD 126(Hubbell & Seltzer)の公開ページを手で保存したもの(repo の外、著作権の表示があるので部分集合だけを同梱)で CI では作れない —— 生成物を commit し、手元では `--nist <dir> --check` が drift を見る。tests/test_dualxray.py が NIST の公表値と化合物の表で中身を守る。",
    "tools/gen_pmd_real.py": "デフレクトメトリの PoC の実データ(DataverseNO doi:10.18710/TKS7SI、CC0 1.0)の抜き出しと全解析の記録。入力の原本(16 bit TIFF 280 枚、110 MB)は repo の外で手で取得するので CI では作れない —— 3 枚の切り出しと解析の記録の小さな npz を data/pmd_real/ に commit し、出典と改変は同じ場所の README.md に書く。PoC は FULLSEYE_PMD_HAMMER_DATA があるとき原本から解析し直して記録との差を門で見る。",
    "tools/gen_material_tables.py": "材料表(materials_data.py)。入力の refractiveindex.info database(CC0、71 MB)は repo の外にあるので CI では作れない —— 生成物を commit し、手元では `--rii <database dir> --check` が drift を見る。tests/test_materials.py がカタログ公表値(n_d / V_d)と一次文献の点で中身を守る。",
    "tools/build_lens_system_anim3d.py": ("教科書の光学「レンズ 1 枚から光学系へ」の動く 3-D(docs/anim3d/textbook_lens_system.html、"
                                         "約 3 MB)。pocviewer の kind anim3d(枝 feat/pocviewer-anim3d)が固まるまでは形が動くので、"
                                         "手で回して commit する(build_view2026_viewers と同じ扱い)。中身は "
                                         "tests/test_lens_system_anim3d.py が理論の式と独立経路で守る。8 言語版は "
                                         "`py -3.11 tools/anim3d_i18n.py --build build_lens_system_anim3d --out "
                                         "docs/anim3d/textbook_lens_system.html` で書く(生成器を直接回すと ja/en に戻る。"
                                         "門は tests/test_anim3d_i18n_lens_system_2026_10_25.py)。"),
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
    "tools/gen_fa_samples.py": _IMAGE_REASON + (" studio_assets/sample_images の FA(外観検査)サンプル"
                                                "5 枚と真値マスク。手元では 2 回でバイト一致(2026-10-12 実測)。"
                                                "画素の中身は tests/test_fa_samples.py が真値と処理列で守る。"),
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
    "tools/gen_simcal_article_figs.py": _IMAGE_REASON + (" Qiita の sim-to-real 較正シリーズの図"
                                                        "(docs/articles/assets/qiita_simcal_series/)。本文の数字は同じ場所の"
                                                        "numbers.json と examples の simcal ツアー 2 本の印字に合わせ、ずれたら"
                                                        "図を書かずに止まる(assert)。第 2 回の図は実写の PoC 4 本"
                                                        "(薄膜・テレセン・ピクセルシフト・相互反射)の章を呼ぶので、"
                                                        "公開画像の取得(ネット)と 10 分前後の CPU が要る。"),
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
    # ---- 2026-10-25: Studio をブラウザで動かす可否の探針(tools/probe_studio_web/、製品ではない) ----
    "tools/probe_studio_web/op_inventory.py": "探針。全 op を実装モジュールの import で分類し、結果 JSON は --out(repo の外)へ書く。",
    "tools/probe_studio_web/bench_body.py": "探針のベンチ本体(CPython と Pyodide で同じファイルを読む)。実測値なので回すたびに変わる。",
    "tools/probe_studio_web/verify_ops_body.py": "探針。image / region 入力の全 op を実際に走らせ、結果の npz と JSON を引数の出力先(repo の外)へ書く。",
    "tools/probe_studio_web/compare_outputs.py": "探針の照合。2 つの実行の出力を ULP で比べ、結果は引数の出力先へ。--ops-json で studio_lite/ops_subset.json(実測の台帳)を書くが、それは手で回して commit する(node + Pyodide が要り CI では作れない)。",
    "tools/probe_studio_web/build_proof.py": ("探針の証明ページを --out(repo の外)に組む(Pyodide 本体の複製 + repo 内モジュールの zip)。"
                                               "dist は repo に入れない。"),
    "tools/check_fallback_parity.py": "門の実測(min 構成 = cv2/skimage/PIL なしで op が別の答えを返さないか、full と ULP 照合)。出力は一時 dir か --out の指定先で、repo の生成物は無い。",
    "tools/algo_gate.py": "門(algo 層の合否を出す)。出力は out/ へ。", "tools/mutation_probe.py": "門の実測。出力は指定先、一時変更は復元。",
    "gsviewer.py": "ライブラリ + CLI(fs.gs_viewer_html / gs_catalog_html)。呼び出し側が指定した出力先へ 1 つの HTML を書く道具で、repo の生成物ではない(公開ページの生成器は tools/build_gsplat_pages.py)。",
    "pocviewer.py": "ライブラリ(fs.write_viewer)。呼び出し側が指定した出力先へ 1 つの HTML を書く道具で、repo の生成物ではない(ビューアの生成器は tools/build_view2026_viewers.py)。",
    "tools/bench_ops.py": "ベンチ。実測値なので回すたびに変わる。",
    "tools/update_fullseye.py": ("安全アップデータ(git pull --ff-only と、導入済みの RAG スキルの更新)。"
                                 "shutil.copytree は利用者の ~/.claude/skills のバックアップで、repo の生成物は書かない。"),
    "tools/bench_realtime.py": "ベンチ(実時間)。",
    "tools/bench_soak.py": "ベンチ(長時間)。",
    "tools/chain_fuzz.py": "ファザー。out/ に結果を落とす。",
    "tools/check_solution_json.py": "外部の採点器(TUM drivability-checker、WSL)を呼んで合否を JSON に書く。生成物は repo の外(FULLSEYE_COMMONROAD_DATA)。",
    "tools/chain_mine.py": "連鎖の探索(実験)。",
    "tools/ci_wheel_check.py": "門(wheel の完全性を配布物の側から数える)。",
    "tools/pip_audit_gate.py": "門(利用者に入る依存の既知脆弱性を OSV で監査し、見つかれば落とす)。解決の report は一時ディレクトリへ書いて捨て、repo の生成物は無い。ネットワークが要るので CI の lint 行で回す。",
    "tools/ledger_gaps.py": "門(説明・空入力・効かないノブの探針)。--write は直して台帳を縮めるときだけ手で回す(新しい欠けは門が拒む)。",
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
#:
#: ★2026-10-25: まだ狭かった。``pv.write_viewer(`` / ``fs.write_viewer(`` で HTML を書く生成器
#: (``tools/build_view2026_viewers.py``、題材の枝の ``tools/build_*_anim3d.py``)がどの表にも
#: 載っていなかった。同じ洗い出しで ``open(.., "wb")``(``"w"`` しか見ていなかった)と
#: ``shutil.copy*`` / ``copytree`` / ``move`` も足した。印ごとに「その印でしか釣れない実在の
#: 生成器」を ``tests/test_regen_all.py`` が要求する(印を消せば落ちる)。
_WRITES = re.compile(
    r'open\([^)]*,\s*(?:mode\s*=\s*)?["\'](?:w|wb|w\+|wb\+|a|ab|x|xb)["\']|\.write_text\(|\.write_bytes\(|savefig\(|json\.dump\('
    r'|\.save\(|mimwrite\(|mimsave\(|imwrite\(|\.to_csv\(|\bnp\.save(?:z|z_compressed)?\('
    r'|\b(?:write|save)_(?:video|gif|png|image|animation|flipbook|exhibit|mesh|points|volume|wav|ply)\w*\('
    r'|\bwrite_viewer\(|\bshutil\.(?:copy|copy2|copyfile|copytree|move)\(')
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


def _match(path: str, pat: str) -> bool:
    return fnmatch.fnmatchcase(path, pat)


@functools.lru_cache(maxsize=1)
def _tracked_files() -> tuple:
    """git の追跡ファイル(repo 相対・``/`` 区切り)。git が無ければ空(そのときは文字列比較だけ)。"""
    try:
        r = subprocess.run(["git", "ls-files", "-z"], cwd=_ROOT, capture_output=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return ()
    return tuple(p for p in r.stdout.decode("utf-8", "replace").split("\0") if p)


@functools.lru_cache(maxsize=None)
def _expand(pat: str) -> frozenset:
    rx = re.compile(fnmatch.translate(pat))
    return frozenset(p for p in _tracked_files() if rx.match(p))


def _overlap(a: str, b: str) -> bool:
    """2 つのパターンが同じファイルを指しうるか(片方がもう片方に当たる / 追跡ファイルを共有する)。"""
    return a == b or _match(a, b) or _match(b, a) or bool(_expand(a) & _expand(b))


def _all_outputs(stage: str) -> list:
    """その段が書きうる全パターン(必ず書く OUTPUTS + 書くかもしれない MAY_OUTPUTS)。"""
    return list(OUTPUTS.get(stage, ())) + list(MAY_OUTPUTS.get(stage, {}))


def _chain_scripts(chain=None) -> list:
    return [args[0] for args, _ in (CHAIN if chain is None else chain)]


def order_violations(order=None) -> list:
    """読む生成物を、それを書く段が**後ろ**で作り直す組を全部返す。

    ``order`` は段のスクリプト名の並び(既定は CHAIN)。戻り値は
    ``(読む段, 読むパターン, 後ろで書く段, 書くパターン)`` のリスト。``ORDER_EXEMPT`` は除く。
    """
    order = _chain_scripts() if order is None else list(order)
    bad = []
    for i, reader in enumerate(order):
        for rp in READS.get(reader, ()):
            if (reader, rp) in ORDER_EXEMPT:
                continue
            for writer in order[i + 1:]:
                for wp in _all_outputs(writer):
                    if _overlap(rp, wp):
                        bad.append((reader, rp, writer, wp))
    return bad


def table_problems() -> list:
    """依存表そのものの健全性(静的)。空なら健全。"""
    probs = []
    scripts = _chain_scripts()
    if set(OUTPUTS) != set(scripts):
        probs.append("OUTPUTS のキーと CHAIN の段が食い違う: 表だけ %s / 鎖だけ %s"
                     % (sorted(set(OUTPUTS) - set(scripts)), sorted(set(scripts) - set(OUTPUTS))))
    for s in READS:
        if s not in scripts:
            probs.append("READS に鎖に無い段: %s" % s)
    for s, pats in READS.items():
        for rp in pats:
            if not any(_overlap(rp, wp) for w, wps in OUTPUTS.items() if w != s for wp in wps):
                probs.append("%s の READS %r は、どの(他の)段の出力でもない" % (s, rp))
    for s, pats in OUTPUTS.items():
        if not pats:
            probs.append("%s の OUTPUTS が空" % s)
        for wp in pats:
            if _tracked_files() and not _expand(wp):
                probs.append("%s の OUTPUTS %r に当たる追跡ファイルが 1 本も無い" % (s, wp))
    for s, pats in MAY_OUTPUTS.items():
        if s not in scripts:
            probs.append("MAY_OUTPUTS に鎖に無い段: %s" % s)
        if not pats:
            probs.append("%s の MAY_OUTPUTS が空" % s)
        for wp, why in pats.items():
            if len((why or "").strip()) < 15:
                probs.append("%s の MAY_OUTPUTS %r の理由が短すぎる" % (s, wp))
            if wp.rsplit("/", 1)[-1].strip("*") == "":
                probs.append("%s の MAY_OUTPUTS %r はファイル名が * だけ(何でも書ける抜け道)" % (s, wp))
            if any(_overlap(wp, op) for op in OUTPUTS.get(s, ())):
                probs.append("%s の MAY_OUTPUTS %r が自分の OUTPUTS と重なる(どちらか一方に)" % (s, wp))
    for (s, rp), why in ORDER_EXEMPT.items():
        if rp not in READS.get(s, ()):
            probs.append("ORDER_EXEMPT の (%s, %r) が READS に無い(幽霊)" % (s, rp))
        if len(why.strip()) < 15:
            probs.append("ORDER_EXEMPT の (%s, %r) の理由が短すぎる" % (s, rp))
    return probs


def trace_problems(traces: dict) -> list:
    """各段の**実測**の読み書き(``{段: {"r": [...], "w": [...]}}``)と表を突き合わせる。

    * 宣言に無い書き込み(OUTPUTS に足す。差分があるときだけ書くものは MAY_OUTPUTS に)
    * 他の段の生成物を宣言なしに読んだ(READS に足す —— 足すと order_violations が順序を見る)
    * 宣言した READS を 1 本も読んでいない(表が古い)
    * 宣言した OUTPUTS のどれにも触れていない(**書いていない段** —— conversion_matrix が
      `--md` 無しで 6 週間そうだった。書き換えずに読み比べるだけの段は読みで触れる)
    """
    probs = []
    for s in _chain_scripts():
        t = traces.get(s)
        if t is None:
            probs.append("%s: 実測が無い" % s)
            continue
        rd, wr = set(t.get("r", ())), set(t.get("w", ()))
        own = OUTPUTS.get(s, [])
        may = _all_outputs(s)      # 書いてよい = 必ず書く + 書くかもしれない
        for p in sorted(wr):
            if not any(_match(p, wp) for wp in may):
                probs.append("%s: OUTPUTS に無いファイルを書いた: %s" % (s, p))
        decl = READS.get(s, [])
        for p in sorted(rd):
            producers = [w for w in _chain_scripts() if w != s and any(_match(p, wp) for wp in _all_outputs(w))]
            if producers and not any(_match(p, rp) for rp in decl):
                probs.append("%s: READS に無い生成物を読んだ: %s(書く段: %s)"
                             % (s, p, ", ".join(producers)))
        for rp in decl:
            if not any(_match(p, rp) for p in rd):
                probs.append("%s: READS の %r を 1 本も読んでいない(表が古い)" % (s, rp))
        touched = rd | wr
        for wp in own:
            if not any(_match(p, wp) for p in touched):
                probs.append("%s: OUTPUTS の %r に触れもしない(書いていない)" % (s, wp))
    return probs


def _rel_in_root(p) -> str | None:
    """audit の open のパスを repo 相対(``/`` 区切り)に。repo の外は None。
    ``__pycache__/X.cpython-*.pyc`` は ``X.py`` として数える(import は .pyc を開くので)。"""
    if isinstance(p, int):
        return None
    try:
        p = os.fspath(p)
    except TypeError:
        return None
    if isinstance(p, bytes):
        p = p.decode("utf-8", "replace")
    ap = os.path.abspath(p)
    root = os.path.abspath(_ROOT)
    if os.path.normcase(ap) != os.path.normcase(root) and \
            not os.path.normcase(ap).startswith(os.path.normcase(root) + os.sep):
        return None
    rel = os.path.relpath(ap, root).replace(os.sep, "/")
    m = re.match(r"^(.*?)(?:^|/)__pycache__/([^/.]+)\.[^/]*\.pyc$", rel)
    if m:
        rel = (m.group(1) + "/" if m.group(1) else "") + m.group(2) + ".py"
    return rel


def _trace_one(argv) -> int:
    """``regen_all.py --_trace OUT.json script [args...]``: 1 段を audit hook の下で走らせ、
    repo 内で開いた/書いたパスを OUT.json に落とす。子プロセスは追わない(鎖の段は使わない)。"""
    import json
    import runpy
    out, script, rest = argv[0], argv[1], argv[2:]
    rd, wr = set(), set()
    _W = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_APPEND | os.O_TRUNC

    def hook(ev, args):
        if ev == "open":
            rel = _rel_in_root(args[0])
            if rel is None:
                return
            mode, flags = args[1], args[2] if len(args) > 2 else 0
            if mode is None:
                writing = bool((flags or 0) & _W)
            else:
                writing = any(c in str(mode) for c in "wax+")
            if writing and "__pycache__" in str(args[0]):
                return   # ★import が .pyc を書くのは段の出力ではない(新しい .py を足した直後の初回だけ X.py を「書いた」と誤検出した)
            (wr if writing else rd).add(rel)
        elif ev == "os.rename":
            if "__pycache__" in str(args[1]):
                return   # .pyc の原子的な置き換え(os.replace)も同じく出力ではない
            src, dst = _rel_in_root(args[0]), _rel_in_root(args[1])
            wr.discard(src)
            if dst is not None:
                wr.add(dst)

    def dump(rc):
        with open(out, "w", encoding="utf-8") as f:
            json.dump({"script": script, "rc": rc, "r": sorted(rd), "w": sorted(wr)}, f,
                      ensure_ascii=False)

    real_exit = os._exit

    def _exit(code=0):   # opdocs は flush 後に os._exit で確定させる —— その前に記録を落とす
        dump(code)
        sys.stdout.flush()
        real_exit(code)

    os._exit = _exit
    path = os.path.join(_ROOT, script)
    sys.argv = [path] + list(rest)
    sys.path[0] = os.path.dirname(path)
    sys.addaudithook(hook)
    rc = 0
    try:
        runpy.run_path(path, run_name="__main__")
    except SystemExit as e:
        rc = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
    dump(rc)
    return rc


def _run(args: list[str], traces: dict | None = None) -> int:
    if traces is None:
        return subprocess.run([sys.executable] + args, cwd=_ROOT).returncode
    import json
    import tempfile
    fd, tmp = tempfile.mkstemp(prefix="regen_trace_", suffix=".json")
    os.close(fd)
    try:
        rc = subprocess.run([sys.executable, os.path.abspath(__file__), "--_trace", tmp] + args,
                            cwd=_ROOT).returncode
        try:
            with open(tmp, encoding="utf-8") as f:
                traces[args[0]] = json.load(f)
        except (OSError, ValueError):
            pass
        return rc
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass


def _content_changed(path: str) -> bool:
    """追跡済みファイルの中身が本当に変わっているか(`git diff --quiet` の exit code)。"""
    r = subprocess.run(["git", "diff", "--quiet", "--", path], cwd=_ROOT,
                       capture_output=True)
    return r.returncode != 0


def _dirty() -> list[str]:
    # Windows では改行コードだけが違う(中身は同じ)再生成物が `git status` に
    # 「変更」として出て、--check が偽の食い違いを報告した(2026-10-19 に 28 本、
    # `git diff` は空)。stat キャッシュを更新してから読み、さらに追跡済みで
    # `git diff --quiet` が 0 のもの(=中身が同じ)は落とす。未追跡 `??` と
    # 本当の内容変更は残す。
    subprocess.run(["git", "update-index", "-q", "--refresh"], cwd=_ROOT,
                   capture_output=True)
    r = subprocess.run(["git", "status", "--porcelain"], cwd=_ROOT,
                       capture_output=True, text=True, errors="replace")
    out = []
    for ln in r.stdout.splitlines():
        if not ln.strip():
            continue
        # 毎ターン自動で書き換わるので、回し忘れの証拠にはならない。
        if ln.endswith("docs/SESSION_SUMMARY.md"):
            continue
        if not ln.startswith("??") and ln[:2].strip() in ("M", "MM", "AM", "TM")                 and " -> " not in ln and not _content_changed(ln[3:].strip().strip('"')):
            continue
        out.append(ln)
    return out


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else list(argv)
    if argv[:1] == ["--_trace"]:
        return _trace_one(argv[1:])
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
        bad = order_violations()
        print("\n--- 順序の検査(READS / OUTPUTS から): %s ---"
              % ("違反なし" if not bad else "★違反 %d 件" % len(bad)))
        for r, rp, w, wp in bad:
            print("  %s が %s を読むが、後ろの %s が書く(%s)" % (r, rp, w, wp))
        return 0

    # 回す前に順序を見る —— 逆順のまま回すと、古い入力から作った生成物が書かれてしまう。
    pre = ["%s が %s を読むが、後ろの %s が書く(%s)" % v for v in order_violations()] + table_problems()
    if pre:
        print("★鎖の順序 / 依存表が壊れている —— 回さずに止める:")
        for ln in pre:
            print("   " + ln)
        return 1

    before = _dirty() if a.check else []
    traces: dict = {}
    for args, what in CHAIN:
        print("\n=== %s  (%s)" % (" ".join(args), what))
        rc = _run(args, traces)
        if rc != 0:
            print("失敗: %s (exit %d) —— ここで止める" % (" ".join(args), rc))
            return rc

    # 実測の読み書きと表を突き合わせる(表が実コードから遅れたら、ここで赤)。
    tp = trace_problems(traces)
    if tp:
        print("\n★依存表(OUTPUTS / READS)が実測の読み書きと食い違う —— tools/regen_all.py の表を直すこと:")
        for ln in tp:
            print("   " + ln)
        return 1

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
