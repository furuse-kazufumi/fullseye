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
import subprocess
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: 回す順。**順序が意味を持つ** —— 上流(op ノート)が下流(索引・カタログ)の
#: 入力になる。足したら、ここに 1 行足す。
CHAIN = [
    (["tools/opdocs.py", "all"],
     "op ノート + SAMPLES + TOC + RAG skill のコーパス地図 + Studio help HTML(6 言語)"),
    (["tools/gen_op_catalog.py"], "1 ページの op カタログ"),
    (["tools/gen_capabilities_index.py"], "能力索引(docs/capabilities/*.md から)"),
    (["tools/gen_hardening_index.py"], "堅牢性台帳"),
    (["tools/gen_maturity.py"], "成熟度台帳(生成物 + 機械可読 JSON)"),
    (["tools/gen_wingpoc_gallery.py"], "PoC 展示館(ja/en)"),
    (["tools/gen_examples_readme.py"], "examples/README.md"),
    (["tools/gen_docs_index_ops.py"], "docs/README*.md の ops / poc / docmap ブロック"),
    (["tools/gen_examples3d_doc.py"], "docs/EXAMPLES_3D.md(3-D 例の一覧)"),
    (["tools/gen_sensor_playbook.py"], "センサー playbook"),
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
EXCLUDED = [
    ("tools/gen_wing*_gallery.py(wingpoc を除く 10 本)",
     "図・GIF を描き直し、ベンチ実測値を書き込み、画像リンクを相対パスに戻す"),
    ("tools/gen_academic_gallery.py / gen_industrial_gallery.py / gen_science_gallery.py",
     "同上(記事片の生成。図の再描画を伴う)"),
    ("tools/gen_sample_images.py / gen_itokawa_turntable.py",
     "サンプル素材の再生成。入力が変わらない限り回す必要がない"),
    ("imgevolve.py index(docs/OP_INDEX.json)",
     "tools/ の外にあるので取りこぼしやすい。現状はレジストリと一致(実測 916)"),
]


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
