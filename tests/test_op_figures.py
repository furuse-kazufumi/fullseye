# -*- coding: utf-8 -*-
"""★op の「入力 → 出力」の図と Studio で走るプログラムが、**本当に載っている**か。

## なぜ要るか(2026-09-06)

Studio のヘルプ 11,854 ページを実際に読んだら、画像が **0 枚**だった。同じ日に
手書きヘルプ 3 本と機械生成 902 本を並べて数えたところ、機械生成に足りないのは
「その場で動く `sample:` パイプライン」だけで(3/3 対 0/902)、それは機械にも
作れる。`tools/gen_op_figures.py` が各 op を**実際に走らせ**、通ったものだけ
図と `sample:` を出す。

ここで守るのは 3 つ:

1. **生成物が中身か** —— 図のファイルが在り、ノートとヘルプ HTML がそれを
   実際に参照していること(「一致」だけ見る門は両方が空でも緑になる)。
2. **数の正直さ** —— 「型が届かない」161 本は、登録簿から計算した到達性と
   一致すること(理由を書くなら、その理由が本当であること)。
3. **後戻りしない** —— 図のある op 数の床。

図の中の文字は**短い英語だけ**(ヘルプは 6 言語、図は 1 枚)。
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "docs" / "ops" / "_fig"
HELP = ROOT / "studio_assets" / "op_help"
MANIFEST = FIG / "figures.json"

#: 2026-09-06 の実測。**下回ったら落ちる**(上げるのは自由)。
_OK_FLOOR = 724


def _manifest() -> dict:
    assert MANIFEST.is_file(), ("docs/ops/_fig/figures.json が無い —— "
                                "`py -3.11 tools/gen_op_figures.py`")
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def _by_status(m):
    out = {"ok": [], "unreachable": [], "failed": []}
    for name, r in m["ops"].items():
        out[r["status"]].append(name)
    return out


def test_every_2d_op_has_a_verdict_and_none_failed():
    """全 op が manifest に居て、「走ったが落ちた」が 0 本であること。"""
    sys.path.insert(0, str(ROOT))
    import ops

    m = _manifest()
    names = {o.name for o in ops.REGISTRY}
    assert set(m["ops"]) == names, (
        "manifest と登録簿がずれている(manifest のみ %s / 登録のみ %s) —— "
        "`py -3.11 tools/gen_op_figures.py`"
        % (sorted(set(m["ops"]) - names)[:5], sorted(names - set(m["ops"]))[:5]))
    st = _by_status(m)
    assert not st["failed"], (
        "走らせて落ちた op が %d 本: %s —— 描画側の問題なら生成器を直し、op 側の"
        "問題なら KNOWN_ISSUES に書く" % (len(st["failed"]), st["failed"][:8]))
    assert len(st["ok"]) >= _OK_FLOOR, (
        "図のある op が %d 本に減った(床 %d)" % (len(st["ok"]), _OK_FLOOR))


def test_unreachable_is_exactly_what_the_type_graph_says():
    """「型が届かない」は言い訳ではなく計算結果であること。

    画像から始めて登録 op だけで作れる sort は、いま `PREFIX` に書いた 5 つ
    (image / any / region / contour / color)。登録簿にそれ以外へ渡る op が
    増えたら(例: image → points)、この門が落ちて PREFIX を伸ばす番になる。
    """
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "tools"))
    import gen_op_figures as G
    import ops

    m = _manifest()
    st = _by_status(m)
    want = sorted(o.name for o in ops.REGISTRY if o.in_sort not in G.PREFIX)
    assert sorted(st["unreachable"]) == want, (
        "unreachable の集合が型グラフと違う(manifest のみ %s / 計算のみ %s)"
        % (sorted(set(st["unreachable"]) - set(want))[:5],
           sorted(set(want) - set(st["unreachable"]))[:5]))
    # 「image から届く sort」が増えていないか —— 増えたら PREFIX を伸ばせる
    reach = {"image"}
    grew = True
    while grew:
        grew = False
        for o in ops.REGISTRY:
            if o.in_sort in reach and o.out_sort not in reach and o.out_sort != "any":
                reach.add(o.out_sort)
                grew = True
    assert reach - {"feature", "match"} <= set(G.PREFIX), (
        "image から新しい sort へ届く op が登録された: %s —— "
        "tools/gen_op_figures.py の PREFIX に前置きを足せば図が増やせる"
        % sorted(reach - set(G.PREFIX)))


def test_every_ok_op_has_its_png_in_both_places():
    """図のファイルが docs 側(Pages)と studio_assets 側(wheel)の両方に在ること。"""
    st = _by_status(_manifest())
    miss_docs = [n for n in st["ok"] if not (FIG / ("%s.png" % n)).is_file()]
    miss_help = [n for n in st["ok"] if not (HELP / "fig" / ("%s.png" % n)).is_file()]
    assert not miss_docs, "docs/ops/_fig に無い図: %s" % miss_docs[:8]
    assert not miss_help, ("studio_assets/op_help/fig に無い図: %s —— "
                           "`py -3.11 tools/opdocs.py html`" % miss_help[:8])
    # 中身が空でないこと(0 バイトの png を「在る」と数えない)
    small = [n for n in st["ok"] if (FIG / ("%s.png" % n)).stat().st_size < 800]
    assert not small, "小さすぎる図(壊れている?): %s" % small[:8]


def test_every_ok_op_note_embeds_its_figure_and_program():
    """★ノート(RAG が読む側)が図と Studio プログラムを**実際に載せている**こと。"""
    sys.path.insert(0, str(ROOT / "tools"))
    sys.path.insert(0, str(ROOT))
    import opdocs as OD

    m = _manifest()
    st = _by_status(m)
    recs, _i, _o, _f = OD._records()
    path_of = {r["name"]: OD._op_path(r) for r in recs if r["dim"] == "2d"}
    bad = []
    for n in st["ok"]:
        md = Path(path_of[n]).read_text(encoding="utf-8")
        if "_fig/%s.png)" % n not in md:
            bad.append("%s: 図の埋め込みが無い" % n)
        elif "```program" not in md:
            bad.append("%s: Studio プログラムが無い" % n)
        elif m["ops"][n]["program"].splitlines()[-1] not in md:
            bad.append("%s: プログラムの中身が manifest と違う" % n)
    for n in st["unreachable"]:
        md = Path(path_of[n]).read_text(encoding="utf-8")
        if "図なし" not in md:
            bad.append("%s: 図が無い理由が書かれていない" % n)
    assert not bad, ("ノートに載っていない: %d 本 —— `py -3.11 tools/opdocs.py md`\n  %s"
                     % (len(bad), "\n  ".join(bad[:10])))


def test_every_ok_op_help_page_shows_the_figure_and_the_buttons():
    """★Studio のヘルプ HTML(人が開く側)。6 言語すべてで図とボタンが出ること。"""
    if not HELP.is_dir():
        pytest.skip("studio_assets/op_help が無い")
    st = _by_status(_manifest())
    hand = {"gaussian", "otsu", "sobel_mag"}       # 手書き。自前の sample: を持つ
    bad = []
    for n in st["ok"]:
        if n in hand:
            continue
        for lang in ("", "en", "zh", "tw", "ko", "de"):
            p = HELP / ("%s.html" % n if not lang else "%s.%s.html" % (n, lang))
            if not p.is_file():
                continue                                  # 言語版の有無は test_opdocs が見る
            h = p.read_text(encoding="utf-8", errors="replace")
            if 'src="fig/%s.png"' % n not in h:
                bad.append("%s%s: <img> が無い" % (n, "." + lang if lang else ""))
            elif 'href="sample:' not in h or 'href="run:' not in h:
                bad.append("%s%s: sample:/run: ボタンが無い" % (n, "." + lang if lang else ""))
    assert not bad, ("ヘルプに載っていない: %d 件 —— `py -3.11 tools/opdocs.py html`\n  %s"
                     % (len(bad), "\n  ".join(bad[:10])))


def test_the_sample_program_in_the_help_round_trips_and_runs():
    """ヘルプの `sample:` を復号すると manifest のプログラムに戻り、**実際に走る**。"""
    import urllib.parse as up

    sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
    import fullseye as fs
    import gen_op_figures as G

    m = _manifest()
    st = _by_status(m)
    picks = [n for n in st["ok"] if n not in ("gaussian", "otsu", "sobel_mag")]
    picks = picks[::97][:8]                                # 8 本を抜き取り
    img = G.canonical_image()
    for n in picks:
        h = (HELP / ("%s.html" % n)).read_text(encoding="utf-8")
        enc = re.search(r'href="sample:([^"]+)"', h).group(1)
        prog = up.unquote(enc)
        assert prog == m["ops"][n]["program"], n
        v = img
        for line in prog.splitlines():
            name, a, b = line.split()
            v = fs.apply(v, name, float(a), float(b), on_error="raise")


def test_the_figures_are_deterministic():
    """同じ入力から同じバイト列。図を commit する以上、再生成でずれてはいけない。"""
    import subprocess
    import tempfile

    st = _by_status(_manifest())
    with tempfile.TemporaryDirectory() as td:
        r = subprocess.run([sys.executable, str(ROOT / "tools" / "gen_op_figures.py"),
                            "--limit", "12", "--out", td],
                           capture_output=True, text=True, cwd=str(ROOT))
        assert r.returncode == 0, r.stderr[-800:]
        made = sorted(f for f in os.listdir(td) if f.endswith(".png"))
        assert made, "12 本で 1 枚も出ない"
        diff = [f for f in made
                if (Path(td) / f).read_bytes() != (FIG / f).read_bytes()]
        assert not diff, ("再生成で図が変わる(非決定的): %s —— 入力画像か描画に乱数/"
                          "環境依存が混じっている" % diff)


def test_the_wheel_declares_the_figures():
    """`op_help/fig/*.png` が package-data に在ること(HTML だけ配って図が空白、を防ぐ)。"""
    s = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert '"op_help/fig/*.png"' in s, "pyproject.toml の studio_assets に op_help/fig/*.png が無い"
