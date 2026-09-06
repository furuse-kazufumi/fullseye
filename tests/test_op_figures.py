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

# ★op 集合は環境で変わる(Linux CI は torch/kornia/mahotas/xfeatures2d が無く
# 859 op、手元は 885)。手元で生成した文書と**生きたレジストリ**を比べる検査は
# 満杯の環境でだけ意味を持つ —— test_opdocs と同じ規約で、揃っていなければ
# skip(理由に欠けている backend 名が出る)。2026-09-07 の CI で 22 件が
# これで落ちた。環境に依らない検査(ファイルの実在・中身の量・図の実在)は
# そのまま走る。
from conftest import requires_full_registry

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "docs" / "ops" / "_fig"
HELP = ROOT / "studio_assets" / "op_help"
MANIFEST = FIG / "figures.json"

#: 2026-09-06 の実測。**下回ったら落ちる**(上げるのは自由)。
_OK_FLOOR = 892


def _manifest() -> dict:
    assert MANIFEST.is_file(), ("docs/ops/_fig/figures.json が無い —— "
                                "`py -3.11 tools/gen_op_figures.py`")
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def _by_status(m):
    out = {"ok": [], "unreachable": [], "failed": [], "domain": [], "empty": []}
    for name, r in m["ops"].items():
        out[r["status"]].append(name)
    return out


def test_every_2d_op_has_a_verdict_and_none_failed():
    """全 op が manifest に居て、「走ったが落ちた」が 0 本であること。"""
    sys.path.insert(0, str(ROOT))
    import ops

    m = _manifest()
    st = _by_status(m)
    # 環境に依らない部分を先に(落ちた 0 本・床)
    assert not st["failed"], (
        "走らせて落ちた op が %d 本: %s —— 描画側の問題なら生成器を直し、op 側の"
        "問題なら KNOWN_ISSUES に書く" % (len(st["failed"]), st["failed"][:8]))
    assert len(st["ok"]) >= _OK_FLOOR, (
        "図のある op が %d 本に減った(床 %d)" % (len(st["ok"]), _OK_FLOOR))
    requires_full_registry()
    names = {o.name for o in ops.REGISTRY}
    assert set(m["ops"]) == names, (
        "manifest と登録簿がずれている(manifest のみ %s / 登録のみ %s) —— "
        "`py -3.11 tools/gen_op_figures.py`"
        % (sorted(set(m["ops"]) - names)[:5], sorted(names - set(m["ops"]))[:5]))


def test_unreachable_is_exactly_what_the_type_graph_says():
    """「型が届かない」は言い訳ではなく計算結果であること。

    2026-09-07 に入口 op(backends_bridge)を足してからは、**登録されている全
    in_sort に PREFIX の鎖がある**のが正常(unreachable は空)。新しい sort を
    入力に取る op が登録されたら、この門が落ちて PREFIX を伸ばす番になる。
    """
    requires_full_registry()
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
    # 2026-09-07: 入口 op を足したので、登録簿の全 in_sort に鎖がある
    missing = sorted({o.in_sort for o in ops.REGISTRY} - set(G.PREFIX))
    assert not missing, ("PREFIX に鎖の無い in_sort がある: %s —— backends_bridge に"
                         "入口 op を足す" % missing)


def test_empty_verdicts_are_really_empty_and_ok_verdicts_are_not():
    """★「走った」と「意味のある出力」を分ける(2026-09-07、「out が真っ黒」)。

    manifest が empty と言う op は本当に空配列を返し、ok と言う op は空でないこと。
    """
    requires_full_registry()
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "tools"))
    import gen_op_figures as G
    import ops
    import fullseye as fs
    import numpy as np

    m = _manifest()
    st = _by_status(m)
    base = G.canonical_image()

    def _run(name):
        op = ops._BY_NAME[name]
        v = base
        for nm, ka, kb in G.PREFIX_OP.get(name, G.PREFIX[op.in_sort]):
            v = fs.apply(v, nm, ka, kb, on_error="raise")
        return fs.apply(v, name, *G._knobs(op), on_error="raise")

    wrong = [n for n in st["empty"] if not (isinstance(_run(n), np.ndarray) and _run(n).size == 0)]
    assert not wrong, "empty と記録されているのに空でない: %s —— 図を作り直す" % wrong
    # ok 側は全数だと 30 秒かかるので、配列を返す op から決定的に 40 本を抜く
    picks = sorted(st["ok"])[::max(1, len(st["ok"]) // 40)]
    hollow = [n for n in picks if isinstance(_run(n), np.ndarray) and _run(n).size == 0]
    assert not hollow, "ok と記録されているのに空を返す: %s" % hollow


#: 2026-09-07 の実測。下回ったら落ちる(上げるのは自由)。
_SWEEP_FLOOR = 600
_GIF_FLOOR = 30
_INPUTS_FLOOR = 600


def test_extra_figures_exist_and_are_counted():
    """つまみの段階図・段階(chain)図・GIF が manifest どおりに在り、量が減っていないこと。

    「a は出力を変えない」と記録された op は、本当に 3 点で同一かも抜き取りで確かめる
    (効かないつまみは liveness の信号でもある)。
    """
    m = _manifest()
    st = _by_status(m)
    n_sw = n_gif = 0
    missing = []
    for n in st["ok"]:
        r = m["ops"][n]
        for k, rel in (r.get("extra") or {}).items():
            if not (FIG / rel).is_file():
                missing.append(rel)
            # JPEG(段階図・複数入力)は docs だけ。wheel には主図 PNG と GIF を同梱する
            if not rel.endswith(".jpg") and not (HELP / "fig" / rel).is_file():
                missing.append("op_help/fig/" + rel)
            if k in ("a", "b"):
                n_sw += 1
            if k == "gif":
                n_gif += 1
                from PIL import Image
                with Image.open(FIG / rel) as im:
                    assert getattr(im, "n_frames", 1) > 1, "%s: GIF が 1 コマ" % rel
    assert not missing, "manifest にあるのに無い図: %s" % missing[:8]
    assert n_sw >= _SWEEP_FLOOR, "つまみの段階図が %d 組に減った(床 %d)" % (n_sw, _SWEEP_FLOOR)
    assert n_gif >= _GIF_FLOOR, "GIF が %d 本に減った(床 %d)" % (n_gif, _GIF_FLOOR)
    n_in = sum(1 for n in st["ok"] if "inputs" in (m["ops"][n].get("extra") or {}))
    assert n_in >= _INPUTS_FLOOR, "複数入力の図が %d 本に減った(床 %d)" % (n_in, _INPUTS_FLOOR)


def test_dead_knobs_are_really_dead():
    requires_full_registry()
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "tools"))
    import gen_op_figures as G
    import ops
    import fullseye as fs
    import numpy as np

    m = _manifest()
    base = G.canonical_image()
    dead = [(n, k) for n, r in m["ops"].items() if r["status"] == "ok" for k in r.get("knob_dead", [])]
    picks = dead[::max(1, len(dead) // 30)]
    wrong = []
    for n, k in picks:
        op = ops._BY_NAME[n]
        v = base
        for nm, ka, kb in G.PREFIX_OP.get(n, G.PREFIX[op.in_sort]):
            v = fs.apply(v, nm, ka, kb, on_error="raise")
        ka, kb = G._knobs(op)
        outs = [fs.apply(v, n, (t if k == "a" else ka), (kb if k == "a" else t), on_error="raise")
                for t in G.SWEEP]
        if not all(G._same(outs[0], o) for o in outs[1:]):
            wrong.append((n, k))
    assert not wrong, "「効かない」と記録されたつまみが効いている: %s" % wrong[:6]


def test_domain_mismatch_ledger_is_still_true():
    """★免除台帳(DOMAIN_MISMATCH)が腐っていないこと。

    「型は届くが定義域が合わない」と記録した op は、**本当にまだ拒否される**
    ことを実際に走らせて確かめる。通るようになっていたら表から外して図を作る番。
    逆に、表に無い op が unreachable/failed に混じっていないことは上の門が見る。
    """
    requires_full_registry()
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "tools"))
    import gen_op_figures as G
    import ops
    import fullseye as fs

    m = _manifest()
    st = _by_status(m)
    assert sorted(st["domain"]) == sorted(G.DOMAIN_MISMATCH), (
        "manifest の domain と表が違う: %s / %s" % (sorted(st["domain"]), sorted(G.DOMAIN_MISMATCH)))
    base = G.canonical_image()
    passed = []
    for name in sorted(G.DOMAIN_MISMATCH):
        op = ops._BY_NAME[name]
        v = base
        try:
            for nm, ka, kb in G.PREFIX_OP.get(name, G.PREFIX[op.in_sort]):
                v = fs.apply(v, nm, ka, kb, on_error="raise")
            fs.apply(v, name, *G._knobs(op), on_error="raise")
            passed.append(name)
        except Exception:                                 # noqa: BLE001
            pass
    assert not passed, ("DOMAIN_MISMATCH に載っているのに通る op: %s —— 表から外して"
                        "図を作る(`py -3.11 tools/gen_op_figures.py`)" % passed)


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
    m = _manifest()
    st = _by_status(m)
    # ノートの場所は**ファイルから**引く(レジストリからだと、この環境に無い
    # optional backend の op で KeyError になる)。2-D のノートは docs/ops/2d/<cat>/<op>.md。
    path_of = {p.stem: p for p in (ROOT / "docs" / "ops" / "2d").rglob("*.md")
               if p.name != "INDEX.md" and "guides" not in p.parts}
    missing = [n for n in st["ok"] + st["unreachable"] + st["domain"] + st["empty"] if n not in path_of]
    assert not missing, "manifest にあるのにノートが無い op: %s" % missing[:8]
    bad = []
    for n in st["ok"]:
        md = Path(path_of[n]).read_text(encoding="utf-8")
        if "_fig/%s.png)" % n not in md:
            bad.append("%s: 図の埋め込みが無い" % n)
        elif "```program" not in md:
            bad.append("%s: Studio プログラムが無い" % n)
        elif m["ops"][n]["program"].splitlines()[-1] not in md:
            bad.append("%s: プログラムの中身が manifest と違う" % n)
    for n in st["unreachable"] + st["domain"] + st["empty"]:
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

    import ops

    m = _manifest()
    st = _by_status(m)
    here = {o.name for o in ops.REGISTRY}                   # この環境に居る op だけ走らせる
    picks = [n for n in st["ok"] if n not in ("gaussian", "otsu", "sobel_mag")
             and n in here
             and all(l.split()[0] in here for l in m["ops"][n]["program"].splitlines())]
    picks = picks[::97][:8]                                # 8 本を抜き取り
    assert len(picks) >= 4, "抜き取れる op が %d 本しか無い" % len(picks)
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
    """同じ環境で 2 回生成して同じバイト列。

    ★commit 済みとの比較は**しない**(2026-09-07 の CI で学んだ): 文字の
    アンチエイリアスと PNG の量子化は OS / PIL / フォントで数バイト変わるので、
    Windows で作った図は Linux では `identity.png` ですらバイト一致しない。
    ここで守るのは「乱数や実行順が混じっていない」ことだけ —— それは同じ
    環境で 2 回作って比べれば分かる。環境をまたぐ見た目の一致は、図を
    生成した環境(手元 Windows)で `--limit 12` を回して目で見る。
    """
    import subprocess
    import tempfile

    outs = []
    for _ in range(2):
        td = tempfile.mkdtemp()
        r = subprocess.run([sys.executable, str(ROOT / "tools" / "gen_op_figures.py"),
                            "--limit", "12", "--out", td],
                           capture_output=True, text=True, cwd=str(ROOT))
        assert r.returncode == 0, r.stderr[-800:]
        outs.append(Path(td))
    made = sorted(f for f in os.listdir(outs[0]) if f.endswith(".png"))
    assert made, "12 本で 1 枚も出ない"
    diff = [f for f in made
            if (outs[0] / f).read_bytes() != (outs[1] / f).read_bytes()]
    assert not diff, ("同じ環境で 2 回作って図が変わる(非決定的): %s —— "
                      "入力画像か描画に乱数/実行順依存が混じっている" % diff)
    # manifest も同一(status / program が揺れない)
    m0 = json.loads((outs[0] / "figures.json").read_text(encoding="utf-8"))
    m1 = json.loads((outs[1] / "figures.json").read_text(encoding="utf-8"))
    assert m0 == m1


def test_the_wheel_declares_the_figures():
    """`op_help/fig/*.png` が package-data に在ること(HTML だけ配って図が空白、を防ぐ)。"""
    s = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert '"op_help/fig/*.png"' in s, "pyproject.toml の studio_assets に op_help/fig/*.png が無い"
