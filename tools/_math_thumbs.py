# -*- coding: utf-8 -*-
"""数学記事に**サムネイル層**を入れる(展示館と同じ出し方に揃える)。

なぜ要るか
==========
展示館は `[![alt](x_720.jpg)](x.png)` で**軽い JPG を表示し、原寸 PNG はクリック先**に
置いている。ところが手書きの数学記事はこれをやっておらず、**原寸 PNG を 84 枚そのまま
表示**していた —— 初回転送 15.5 MB。同じ絵を、同じ道具で、同じように出せばよいだけである。

★**動く図(.gif)は触らない。** `tools/gen_wingpoc_gallery.py` の `_thumb()` に
2026-09-09 の判断が書いてある —— 動く図を JPEG に落とすと「クリックしないと動かない絵」に
なり、動きが主題の展示では意味が消える。ここでも同じ規律に従う。

★**`?v=N`(imgix のキャッシュ破り)はそのまま引き継ぐ。** 剥がすと、あとで図を差し替えた
ときにサムネだけ古いまま出る。剥がし忘れで数字を 1 度外したので、扱いを明示しておく。

冪等 —— 既に `[![...](..._720.jpg...)](...)` になっている行は素通りする。
"""
from __future__ import annotations

import re

#: `![alt](<base>/<poc>/<file>.png<?query>)` の裸の画像だけを捕まえる。
#: 直前が `[` のもの(= 既にリンクで包まれている)は除く。
_BARE = re.compile(
    r"(?<!\[)!\[([^\]]*)\]\((https://raw\.githubusercontent\.com/[^\)\s]+?"
    r"/assets/poc/[^/\)\s]+/[^/\)\s]+?\.png)(\?[^\)\s]*)?\)")


def rewrite(text: str) -> tuple[str, int]:
    """裸の PNG をサムネ + リンクに包む。``(新しい本文, 包んだ枚数)``。"""
    n = 0

    def sub(m):
        nonlocal n
        alt, url, q = m.group(1), m.group(2), m.group(3) or ""
        thumb = url[:-4] + "_720.jpg"
        n += 1
        return "[![%s](%s%s)](%s%s)" % (alt, thumb, q, url, q)

    return _BARE.sub(sub, text), n


def thumbs_needed(text: str) -> list:
    """作る必要のあるサムネの ``(poc_id, 元のファイル名)`` を重複なしで返す。"""
    out, seen = [], set()
    for m in _BARE.finditer(text):
        p = re.search(r"/assets/poc/([^/]+)/([^/?]+\.png)$", m.group(2))
        if p and p.groups() not in seen:
            seen.add(p.groups())
            out.append(p.groups())
    return out
