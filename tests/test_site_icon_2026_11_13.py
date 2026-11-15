# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""公開サイト(https://furuse.work/、元は docs/)に Fullseye のアイコンを出す配線の門(2026-11-13)。

ユーザーの指摘「fullseye のホームページに fullseye のアイコンが全く出てきてなくないか」。公開中のページの
head に favicon の link が無く、/favicon.ico は 404 で、トップにもロゴが無かった。絵は repo 直下の
assets/ にだけあり、Pages の元の docs/ には無かった。

直し方と、ここで見ること:

* 既定のテーマ(pages-gem v232 の既定 = jekyll-theme-primer 0.6.0)の _layouts/default.html は、head の
  終わりで head-custom.html を読み込む。同じ名前を docs/_includes に置くとテーマの物の代わりに使われる。
  その写しに favicon の 3 行を足した。link の先が docs に在り、sizes の宣言が絵の実寸と合うこと。
* 絵の正本は assets/make_icon.py。docs の 256 px の png は assets の物とバイト一致。
* トップ(docs/README*.md、6 言語)の題のすぐ下にロゴ。ja の版は本文の先頭が題のまま
  (jekyll-titles-from-headings は本文の先頭の見出ししか題にしない。前に何か置くと <title> が落ちる)。

組んだサイトで link の先が実在することは tools/pages_site.py check の門 4 が見る(Jekyll の出力の側)。
ここは repo の側。Pillow が無くても回るように、絵のヘッダは struct で読む。
"""
from __future__ import annotations

import importlib.util
import re
import struct
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
HEAD = DOCS / "_includes" / "head-custom.html"

#: (rel, サイトの根からのパス)。head-custom.html に書く 3 本(この順)。
ICON_LINKS = (
    ("icon", "/favicon.ico"),
    ("icon", "/assets/img/fullseye_256.png"),
    ("apple-touch-icon", "/apple-touch-icon.png"),
)

#: トップの言語版(tests/test_docs_index_reachable.py の LANGS と同じ並び)。
LANGS = ("", "en", "zh", "tw", "ko", "de")

#: トップのロゴの src(docs/README*.md はサイトの根にあるので、この相対パスで /assets/img/… を指す)。
LOGO_SRC = "assets/img/fullseye_256.png"

PNG_SIGNATURE = bytes([0x89]) + b"PNG" + bytes([0x0D, 0x0A, 0x1A, 0x0A])


def _link_tags(text: str) -> list[str]:
    return re.findall(r"<link\b[^>]*>", text)


def _attr(tag: str, name: str) -> str | None:
    m = re.search(r'\b%s="([^"]*)"' % re.escape(name), tag)
    return m.group(1) if m else None


def _png_chunks(data: bytes) -> list[bytes]:
    """PNG のチャンクの型を順に返す(IHDR … IEND)。"""
    assert data[:8] == PNG_SIGNATURE, "PNG でない"
    out, i = [], 8
    while i + 8 <= len(data):
        (n,) = struct.unpack(">I", data[i:i + 4])
        out.append(data[i + 4:i + 8])
        i += 12 + n
    return out


def _png_header(path: Path) -> tuple[int, int, int]:
    """(幅, 高さ, color type)。IHDR を読む。"""
    data = path.read_bytes()
    chunks = _png_chunks(data)
    assert chunks[:1] == [b"IHDR"] and chunks[-1:] == [b"IEND"], "%s の PNG が壊れている: %s" % (path, chunks)
    w, h = struct.unpack(">II", data[16:24])
    return w, h, data[25]


def _ico_sizes(path: Path) -> list[tuple[int, int]]:
    """ICO の ICONDIR を読み、格納しているサイズを返す(0 は 256)。"""
    data = path.read_bytes()
    reserved, kind, count = struct.unpack_from("<HHH", data, 0)
    assert (reserved, kind) == (0, 1), "%s は ICO でない" % path
    assert count >= 1, "%s に絵が 1 枚も無い" % path
    out = []
    for i in range(count):
        w, h = struct.unpack_from("<BB", data, 6 + i * 16)
        out.append((w or 256, h or 256))
    return sorted(out)


def _declared_sizes(tag: str) -> list[tuple[int, int]]:
    sizes = _attr(tag, "sizes")
    assert sizes, "sizes の無い link: %s" % tag
    return sorted(tuple(int(v) for v in s.lower().split("x")) for s in sizes.split())


def _head_tag_for(path: str) -> str:
    tags = [t for t in _link_tags(HEAD.read_text(encoding="utf-8")) if _attr(t, "href") == _liquid_href(path)]
    assert len(tags) == 1, "head-custom.html に %s の link が %d 本" % (path, len(tags))
    return tags[0]


def _liquid_href(path: str) -> str:
    # relative_url を通す(baseurl が付く場合も壊れない。docs/_config.yml は baseurl "")
    return "{{ '%s' | relative_url }}" % path


def test_head_custom_keeps_the_theme_parts_and_links_the_three_icons():
    text = HEAD.read_text(encoding="utf-8")
    # テーマの物の写しなので、テーマの物にある GA の読み込みと前後の印は残す(口を上書きして機能を落とさない)
    for keep in ("<!-- start custom head snippets", "{% include head-custom-google-analytics.html %}",
                 "<!-- end custom head snippets -->"):
        assert keep in text, keep
    got = [(_attr(t, "rel"), _attr(t, "href")) for t in _link_tags(text)]
    assert got == [(rel, _liquid_href(path)) for rel, path in ICON_LINKS], got


@pytest.mark.parametrize("rel,path", ICON_LINKS)
def test_each_icon_link_points_at_a_file_of_the_declared_size(rel, path):
    tag = _head_tag_for(path)
    assert _attr(tag, "rel") == rel
    f = DOCS / path.lstrip("/")
    assert f.is_file(), "%s が docs に無い(Pages で 404 になる)" % f
    declared = _declared_sizes(tag)
    if path.endswith(".ico"):
        assert _ico_sizes(f) == declared, (path, _ico_sizes(f), declared)
    else:
        w, h, _ct = _png_header(f)
        assert [(w, h)] == declared, (path, (w, h), declared)


def test_favicon_ico_has_16_32_48_and_the_site_icons_stay_small():
    assert _ico_sizes(DOCS / "favicon.ico") == [(16, 16), (32, 32), (48, 48)]
    total = sum((DOCS / path.lstrip("/")).stat().st_size for _rel, path in ICON_LINKS)
    assert 1000 < total < 80 * 1024, total


def test_apple_touch_icon_is_opaque():
    """iOS はホーム画面のアイコンの透明な所を黒で埋めるので、不透明にしてある(RGB で tRNS 無し)。"""
    f = DOCS / "apple-touch-icon.png"
    w, h, color_type = _png_header(f)
    assert (w, h) == (180, 180)
    assert color_type == 2, "color type %d(2 = RGB。6 = RGBA は透明を持てる)" % color_type
    assert b"tRNS" not in _png_chunks(f.read_bytes())


def test_site_png_is_the_same_bytes_as_the_assets_png():
    """正本は assets/make_icon.py。docs の 256 px は assets の物と同じ絵を同じ保存のしかたで書く。"""
    a = (ROOT / "assets" / "fullseye_256.png").read_bytes()
    d = (DOCS / LOGO_SRC).read_bytes()
    assert len(d) > 1000
    assert d == a, "docs/%s が assets/fullseye_256.png と違う —— py -3.11 assets/make_icon.py で両方を書き直す" % LOGO_SRC


@pytest.mark.parametrize("lang", LANGS, ids=lambda x: x or "ja")
def test_each_top_page_shows_the_logo_right_under_the_title(lang):
    name = "README.md" if not lang else "README.%s.md" % lang
    lines = (DOCS / name).read_text(encoding="utf-8").splitlines()
    h1 = next(i for i, ln in enumerate(lines) if ln.startswith("# "))
    if not lang:
        assert h1 == 0, "ja のトップの本文の先頭が題でない(jekyll-titles-from-headings が <title> を取れなくなる)"
    after = [ln for ln in lines[h1 + 1:h1 + 4] if ln.strip()]
    assert after, "%s の題の後ろが空" % name
    logo = after[0]
    assert logo.startswith("<img "), "%s の題のすぐ下がロゴでない: %r" % (name, logo)
    assert _attr(logo, "src") == LOGO_SRC
    assert "Fullseye" in (_attr(logo, "alt") or ""), "%s のロゴに alt が無い" % name
    w, h = int(_attr(logo, "width") or 0), int(_attr(logo, "height") or 0)
    assert w == h and 64 <= w <= 96, (name, w, h)
    assert (DOCS / LOGO_SRC).is_file()


def test_the_generator_writes_the_three_site_icons(tmp_path):
    """make_icon.py が docs 側の 3 枚を書くこと(書き先は tmp_path。repo は触らない)。"""
    pytest.importorskip("PIL")
    spec = importlib.util.spec_from_file_location("make_icon", ROOT / "assets" / "make_icon.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    images = {s: mod.render(s) for s in mod.ICON_SIZES}
    written = mod.write_site_icons(images, site_dir=tmp_path)
    rels = sorted(p.relative_to(tmp_path).as_posix() for p in written)
    assert rels == sorted(path.lstrip("/") for _rel, path in ICON_LINKS)
    assert _ico_sizes(tmp_path / "favicon.ico") == [(16, 16), (32, 32), (48, 48)]
    assert _png_header(tmp_path / "apple-touch-icon.png") == (180, 180, 2)
    assert _png_header(tmp_path / LOGO_SRC)[:2] == (256, 256)
