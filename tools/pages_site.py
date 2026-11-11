"""組んだ GitHub Pages のサイト(Jekyll の ``_site``)から、どのページからも参照されていない
``articles/assets/**`` を外し、外した後のサイトを別の読み方で検める道具(stdlib だけ)。

なぜ要るか(2026-11-11): legacy 方式(``master`` の ``/docs`` を GitHub が Jekyll で組む)の配備物が
1.54 GB になり、上限 1 GB を超えて ``deploy`` が 10 分のタイムアウトで時々落ちた。
``actions/deploy-pages`` の timeout は 600000 ms が上限で延ばせないので、配備物を小さくするしかない。
``docs/articles/assets`` の大半は Qiita の記事が raw URL で読むためにあり、Pages からは参照されない。
repo からは消さない(Qiita が読む)。配備物からだけ外す。

二つの働きを、**別々の読み方**で実装する(同じ読み方で消して同じ読み方で検めると検算にならない)。

``prune``(緩い字句の読み方)
    サイトの下の全テキスト(html/css/js/json/svg/xml/txt/md …)を字句に切り、相対・ルート相対・
    絶対(``https://furuse.work/…`` など)の参照の候補を作る。URL エンコード・``?query``・``#fragment``・
    HTML の実体参照を外した形も候補にし、ページの場所からとサイトの根からの両方で解決を試す
    (迷ったら残す側に倒す)。サイトに実在するファイルに解決できたものを「参照されている」とし、
    ``articles/assets/`` の下で参照されていないファイルを消す(``--apply`` が無ければ数えるだけ)。
    ``articles/assets/`` の外は、参照されていなくても触らない。

``check``(``html.parser`` で属性を読む厳密な読み方)
    門 1: 厳密に読んだ参照のうち、解決先が ``articles/assets/`` の下で ``--source-docs``(repo の docs)に
          実在するものは、サイトにも実在すること(repo を真値にする。prune の結果は真値に使わない)。
          ``--built-list``(``snapshot`` が prune の前に書いた os.walk の一覧)を渡すと、repo にあっても
          Jekyll が元から配信しないもの(パスの要素が ``_`` か ``.`` で始まる名前だけ)は門 1 でなく報告に分ける。
          いまのサイトが一覧の部分集合でなければ、一覧の取り違えとして終了コード 2。
          ``--source-docs`` の assets が ``--min-kept-assets`` 未満でも終了コード 2(違う docs を渡した)。
          どこでも解決できない assets への参照は、報告だけの切れたリンクに数える(assets の分は別に数える)。
          ``<base href>`` はそのページの相対 URL の起点に使い(base 自身は参照に数えない)、
          ``<meta http-equiv="refresh" content="…;url=…">`` の ``url=`` も参照に数える。
          ``--source-docs`` と ``--site`` が同じか、片方がもう片方の中にあれば終了コード 2。
    門 2: サイトの総バイト数が ``--max-bytes`` 以下。
    門 3: 読んだ html のページ数が ``--min-pages`` 以上、残った assets が ``--min-kept-assets`` 以上
          (空のサイト・違うディレクトリを通さない床)。
    門 4: html の ``<link rel="stylesheet">`` と ``<script src>`` のうちサイト内を指すものが全部実在し、
          ルート相対の参照が ``/fullseye/`` で始まるページが 0(baseurl が repo 名に倒れた印)。
          サイト内の stylesheet が 0 本のサイトも落とす(空を通さない)。
    報告だけ: assets 以外で解決できない内部リンク(元からある切れたリンク)の件数と一覧。

対象外(読まない): JS が文字列を組み立てて作る URL、fetch した JSON の中身から作る URL。prune は json・js の
字句を緩く拾うので多くは残るが、check はそれを検めない(2026-11-11 の調査では view2026 に無かった)。

URL の読み方はブラウザ(WHATWG URL、http(s))に合わせる: 先頭の ``../`` が根を越えるときは根で止める
(サイトの根の外へは出ない)。バックスラッシュは ``/`` と読む。prune と check の両方が同じ規則で解く(2026-11-11 の
独立レビュー R1。どちらか片方だけだと、prune が消して check が通す形が残る)。

判定は ``os.walk`` で集めた相対パス(posix 形)の集合で行う。``os.path.exists`` は使わない
(Windows は大文字小文字を区別しないので、Linux の配信と結果が変わる)。

終了コード: 0 = 通過 / 1 = 門が落ちた / 2 = 使い方・入力の誤り(サイトのディレクトリが無い等)。
"""
from __future__ import annotations

import argparse
import html
import json
import os
import posixpath
import re
import sys
import time
from html.parser import HTMLParser
from urllib.parse import unquote

#: prune の対象。この下だけを消す。
ASSETS_PREFIX = "articles/assets/"

#: 門 2 で足す、配備の tar の 1 ファイルあたりの見出しの見積もり(ustar の 512 B の見出し + 末尾の詰め物
#: の平均 512 B)。GitHub の 1 GB の上限は tar の大きさに掛かるので、中身の合計だけでは甘い。
TAR_HEADER_BYTES = 1024

#: 緩い読み方で読むテキストの拡張子。
TEXT_EXT = (".html", ".htm", ".css", ".js", ".mjs", ".cjs", ".json", ".jsonl", ".svg", ".xml",
            ".txt", ".md", ".webmanifest", ".map", ".csv", ".tsv", ".yml", ".yaml")

#: html として厳密に読む拡張子。
HTML_EXT = (".html", ".htm")

#: このサイトそのものを指す絶対 URL の頭(後ろはサイトの根からのパス)。
SITE_HOSTS = (
    "https://furuse.work/", "http://furuse.work/", "//furuse.work/",
    "https://www.furuse.work/", "http://www.furuse.work/", "//www.furuse.work/",
    "https://furuse-kazufumi.github.io/fullseye/", "http://furuse-kazufumi.github.io/fullseye/",
    "//furuse-kazufumi.github.io/fullseye/",
)

#: 緩い読み方の字句(refs.py と同じ切り方)。
LOOSE_TOKEN = re.compile(r"""[^\s"'()<>\[\]{}`,;|*\\]+""")
#: 引用符の中(空白入りのファイル名を拾う)。開いた引用符と同じ引用符で閉じる形を、二重・一重で別々に
#: 走らせる(片方の引用符が値の中にあっても、もう片方の組を壊さない。2026-11-11 の R2:
#: ``alt="Fullseye's demo" src="…/fig(1).png"`` で ``'`` と ``"`` が組になり src を拾えなかった)。
LOOSE_QUOTED = (
    re.compile(r'"([^"<>\r\n]{1,600})"'),
    re.compile(r"'([^'<>\r\n]{1,600})'"),
)
#: ``<base href>`` を緩く拾う(prune が base の下でも解決を試すため)。
LOOSE_BASE = re.compile(r"""<base\b[^>]*?\bhref\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))""", re.IGNORECASE)
#: meta refresh の content の URL(``5; url=x``・``0;URL='x'``・``url=x`` を拾う)。
META_REFRESH_URL = re.compile(r"""^\s*[\d.]*\s*[;,]?\s*(?:url\s*=\s*)?(.*)$""", re.IGNORECASE | re.DOTALL)

_SCHEME = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")

#: 厳密な読み方で URL として読む属性。
STRICT_URL_ATTRS = ("href", "src", "poster", "data-src")
#: 厳密な読み方で srcset として読む属性(複数・記述子つき)。
STRICT_SRCSET_ATTRS = ("srcset",)
#: 厳密な読み方の CSS url()。
STRICT_CSS_URL = re.compile(r"""url\(\s*(?:"([^"]*)"|'([^']*)'|([^)'"\s][^)]*?))\s*\)""", re.IGNORECASE)


# ---------------------------------------------------------------------------
# サイトの木
# ---------------------------------------------------------------------------

class SiteError(Exception):
    """入力の誤り(終了コード 2)。"""


def walk_files(root: str) -> dict[str, int]:
    """``root`` の下の全ファイルを ``{posix 相対パス: バイト数}`` で返す(os.walk の集合)。"""
    if not os.path.isdir(root):
        raise SiteError(f"ディレクトリが無い: {root}")
    out: dict[str, int] = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        rel_dir = os.path.relpath(dirpath, root).replace(os.sep, "/")
        rel_dir = "" if rel_dir == "." else rel_dir + "/"
        for fn in sorted(filenames):
            full = os.path.join(dirpath, fn)
            if os.path.islink(full) and not os.path.isfile(full):
                continue
            out[rel_dir + fn] = os.path.getsize(full)
    return out


def dirs_of(files) -> set[str]:
    """ファイル集合から、その祖先のディレクトリ集合(posix、末尾 / なし、根は "")を作る。"""
    ds = {""}
    for p in files:
        d = posixpath.dirname(p)
        while d and d not in ds:
            ds.add(d)
            d = posixpath.dirname(d)
    return ds


def read_text(root: str, rel: str) -> str:
    with open(os.path.join(root, *rel.split("/")), "rb") as f:
        return f.read().decode("utf-8", "replace")


# ---------------------------------------------------------------------------
# 参照の解決(両方の読み方が使う小道具。候補の作り方が違う)
# ---------------------------------------------------------------------------

def _norm(path: str) -> str | None:
    """posix に正規化し、サイトの根からのパス(先頭の / なし)にする。空・根そのものは None。

    先頭の ``../`` が根を越えるときは、ブラウザ(WHATWG URL)と同じく根で止める
    (``../x`` → ``x``)。根の外へは出ない。``//`` で始まるもの(別のホスト)は None。
    以前は根を越えるものを None にしていたが、ブラウザはそのページの assets を読むので、
    prune が消して check が通す穴になっていた(2026-11-11 の R1 a)。
    """
    if not path or path.startswith("//"):
        return None
    p = posixpath.normpath("/" + path).lstrip("/")
    return p or None


def _slashes(url: str) -> str:
    """ブラウザは http(s) の URL の ``\\`` を ``/`` と読む(2026-11-11 の R1 b)。"""
    return url.replace("\\", "/")


def strip_site_host(url: str) -> tuple[str, bool] | None:
    """サイト自身の絶対 URL なら (根からのパス, True)。外のサイト・別スキームなら None。相対はそのまま。"""
    low = url.lower()
    for h in SITE_HOSTS:
        if low.startswith(h):
            return "/" + url[len(h):], True
    if url.startswith("//") or _SCHEME.match(url):
        return None
    return url, False


# ---------------------------------------------------------------------------
# (a) 緩い読み方 = prune
# ---------------------------------------------------------------------------

def _json_strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from _json_strings(k)
            yield from _json_strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _json_strings(v)


def loose_tokens(rel: str, text: str) -> set[str]:
    """緩い字句の拾い方。生の本文と、実体参照を外した本文の両方から拾う。

    CSS の ``url(...)`` は字句(括弧で切れる)と引用符の中で拾える。引用符なしで空白を含む url() は
    CSS として無効なので、別の拾い方は持たない(2026-11-11 の変異で等価と確かめた)。
    """
    toks: set[str] = set()
    bodies = {text, html.unescape(text)}
    # \ を / と読んだ本文も拾う(ブラウザの読み方。LOOSE_TOKEN は \ で切るので、生の本文だけでは拾えない)
    bodies |= {_slashes(b.replace("\\/", "/")) for b in bodies if "\\" in b}
    for body in bodies:
        toks.update(LOOSE_TOKEN.findall(body))
        for rx in LOOSE_QUOTED:
            toks.update(m.strip() for m in rx.findall(body))
    if rel.endswith((".json", ".webmanifest", ".map")):
        try:
            toks.update(_json_strings(json.loads(text)))
        except ValueError:
            pass
    if rel.endswith(".jsonl"):
        for line in text.splitlines():
            try:
                toks.update(_json_strings(json.loads(line)))
            except ValueError:
                continue
    # JS の文字列の中の \/ を外した形
    toks.update(t.replace("\\/", "/") for t in list(toks) if "\\/" in t)
    return {t for t in toks if t and ("/" in t or "." in t)}


def loose_candidates(src: str, token: str) -> set[str]:
    """1 つの字句から、サイトの中のパスの候補を全部作る(迷ったら多めに)。"""
    forms = {token, html.unescape(token)}
    forms |= {_slashes(f) for f in forms}
    # ``url=x``(meta refresh の content)・``href=x`` などの ``=`` の後ろも候補にする(迷ったら多めに)
    forms |= {f.split("=", 1)[1].strip().strip("'\"") for f in list(forms) if "=" in f}
    out: set[str] = set()
    for f in list(forms):
        for cut in (f, f.split("#")[0], f.split("?")[0].split("#")[0]):
            for dec in {cut, unquote(cut)}:
                forms.add(dec)
    src_dir = posixpath.dirname(src)
    for f in forms:
        f = f.strip()
        r = strip_site_host(f)
        if r is None:
            continue
        path, _absolute = r
        if path.startswith("/"):
            c = _norm(path)
            if c:
                out.add(c)
            continue
        for c in (_norm(posixpath.join(src_dir, path)), _norm(path)):
            if c:
                out.add(c)
    # 配信と同じ解決(check の _resolve_file と同じ規則): ディレクトリ → index.html、拡張子なし → .html
    out |= {c + "/index.html" for c in out} | {c + ".html" for c in out}
    return out


def _loose_base_srcs(rel: str, text: str) -> list[str]:
    """ページに ``<base href>`` があれば、その下で相対の字句を解くための仮の参照元を返す(迷ったら多めに)。

    base の行き先がディレクトリかファイルかは字句では決められないので、両方の形を返す
    (``X/_`` = X の下、``X`` = X の隣)。根を指す base は ``_``(根の下)。外のサイトを指す base は
    候補を作らない(ページの場所と根からの解決は、base があっても別に試すので、残す側に倒れる)。
    """
    if not rel.lower().endswith(HTML_EXT) or "<base" not in text.lower():
        return []
    out: list[str] = ["_"]
    for m in LOOSE_BASE.finditer(text):
        href = next((g for g in m.groups() if g is not None), "")
        for c in sorted(loose_candidates(rel, href)):
            out += [c + "/_", c]
    return out


def loose_references(site: str, files: dict[str, int]) -> tuple[set[str], int]:
    """緩い読み方で「参照されている」サイト内のファイル集合と、読んだテキストの数。

    参照を数えるのは、**配備に残るファイルから**だけ。``articles/assets/`` の外のテキストを根にして、
    そこから参照された assets のテキスト(json・svg・md など)をさらに読む(到達できるものの閉包)。
    どこからも参照されない assets の中の json が隣の gif を並べていても、その json ごと消えるので
    gif を残す理由にしない(2026-11-11、実物で assets の中の json の参照が 3 千本あった)。
    """
    refs_of: dict[str, set[str]] = {}
    n_read = 0
    for rel in files:
        if not rel.lower().endswith(TEXT_EXT):
            continue
        n_read += 1
        text = read_text(site, rel)
        hit: set[str] = set()
        srcs = [rel] + _loose_base_srcs(rel, text)
        for tok in loose_tokens(rel, text):
            for s in srcs:
                for c in loose_candidates(s, tok):
                    if c in files and c != rel:
                        hit.add(c)
        refs_of[rel] = hit
    referenced: set[str] = set()
    todo = [rel for rel in refs_of if not rel.startswith(ASSETS_PREFIX)]
    seen = set(todo)
    while todo:
        rel = todo.pop()
        for c in refs_of.get(rel, ()):
            referenced.add(c)
            if c not in seen:
                seen.add(c)
                todo.append(c)
    return referenced, n_read


def plan_prune(site: str) -> dict:
    """消す計画(何も消さない)。"""
    files = walk_files(site)
    referenced, n_read = loose_references(site, files)
    assets = {p for p in files if p.startswith(ASSETS_PREFIX)}
    kept = assets & referenced
    remove = sorted(assets - kept)
    n_html = sum(1 for p in files if p.lower().endswith(HTML_EXT))
    total = sum(files.values())
    removed_bytes = sum(files[p] for p in remove)
    return {
        "site": os.path.abspath(site),
        "texts_read": n_read,
        "html_pages": n_html,
        "assets_total": len(assets),
        "assets_total_bytes": sum(files[p] for p in assets),
        "kept_assets": len(kept),
        "kept_assets_bytes": sum(files[p] for p in kept),
        "removed_assets": len(remove),
        "removed_assets_bytes": removed_bytes,
        "site_bytes_before": total,
        "site_bytes_after": total - removed_bytes,
        "kept_largest": [[p, files[p]] for p in sorted(kept, key=lambda q: (-files[q], q))[:30]],
        "remove": remove,
    }


def apply_prune(site: str, remove) -> int:
    """``remove``(articles/assets/ の下だけ)を消し、空になった assets の下のディレクトリを消す。消した数。"""
    n = 0
    for rel in remove:
        if not rel.startswith(ASSETS_PREFIX):  # 念のため(計画の外を消さない)
            raise SiteError(f"articles/assets/ の外は消さない: {rel}")
        os.remove(os.path.join(site, *rel.split("/")))
        n += 1
    assets_root = os.path.join(site, *ASSETS_PREFIX.strip("/").split("/"))
    if os.path.isdir(assets_root):
        for dirpath, _dirnames, _filenames in os.walk(assets_root, topdown=False):
            if dirpath != assets_root and not os.listdir(dirpath):
                os.rmdir(dirpath)
    return n


# ---------------------------------------------------------------------------
# (b) 厳密な読み方 = check
# ---------------------------------------------------------------------------

def parse_srcset(value: str) -> list[str]:
    """``srcset`` の URL だけを返す(``a.png 1x, b.png 640w``)。"""
    urls = []
    for part in value.split(","):
        part = part.strip()
        if part:
            urls.append(part.split()[0])
    return urls


def css_urls(text: str) -> list[str]:
    out = []
    for a, b, c in STRICT_CSS_URL.findall(text):
        u = (a or b or c).strip()
        if u:
            out.append(u)
    return out


class _StrictParser(HTMLParser):
    """属性(html.parser が実体参照を外したもの)と <style> の本文から URL を集める。"""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.urls: list[str] = []
        self.base: str | None = None  # 最初の <base href>(HTML の規則: href を持つ最初の base だけが効く)
        self._in_style = False

    def handle_starttag(self, tag, attrs):
        if tag == "base":
            # base の href は読みに行く URL でなく、相対 URL の起点(参照に数えない)
            href = next((v for k, v in attrs if k == "href" and v is not None), None)
            if href is not None and self.base is None:
                self.base = href.strip()
            return
        if tag == "meta":
            a = {k: (v or "") for k, v in attrs}
            if a.get("http-equiv", "").strip().lower() == "refresh" and a.get("content"):
                u = meta_refresh_url(a["content"])
                if u:
                    self.urls.append(u)
        for name, value in attrs:
            if value is None:
                continue
            if name in STRICT_URL_ATTRS:
                self.urls.append(value.strip())
            elif name in STRICT_SRCSET_ATTRS:
                self.urls.extend(parse_srcset(value))
            elif name == "style":
                self.urls.extend(css_urls(value))
        if tag == "style":
            self._in_style = True

    def handle_endtag(self, tag):
        if tag == "style":
            self._in_style = False

    def handle_data(self, data):
        if self._in_style:
            self.urls.extend(css_urls(data))


def meta_refresh_url(content: str) -> str | None:
    """``<meta http-equiv="refresh" content="0;url=x">`` の URL(無ければ None)。引用符は外す。"""
    m = META_REFRESH_URL.match(content)
    if not m:
        return None
    u = m.group(1).strip()
    if u[:1] in ("'", '"'):
        u = u[1:].split(u[0], 1)[0]
    return u.strip() or None


def strict_page(rel: str, text: str) -> tuple[list[str], str | None]:
    """1 つのファイルの厳密な参照(生の URL 文字列)と ``<base href>``(無ければ None)。html と css だけを読む。"""
    low = rel.lower()
    if low.endswith(HTML_EXT):
        p = _StrictParser()
        p.feed(text)
        p.close()
        return p.urls, p.base
    if low.endswith(".css"):
        return css_urls(text), None
    return [], None


def strict_urls(rel: str, text: str) -> list[str]:
    """1 つのファイルの厳密な参照(生の URL 文字列)。html と css だけを読む。"""
    return strict_page(rel, text)[0]


def base_src(src: str, base: str | None) -> str | None:
    """``<base href>`` を、相対 URL を解くときの仮の参照元に直す。base が無ければ ``src``。

    外のサイトを指す base なら None(そのページの相対 URL はサイトの外へ行く)。
    """
    if base is None or not base.strip():
        return src
    b = strict_resolve(src, base)
    if b is None:
        return None
    raw = _slashes(base.strip()).split("#", 1)[0].split("?", 1)[0]
    if b == "" or b.endswith("/") or raw.endswith("/"):
        # ディレクトリの下(dirname が b になる仮の名前)。ルート相対の解決は末尾の / を落とすので、
        # 生の href の末尾で見る
        return (b.rstrip("/") + "/_") if b.rstrip("/") else "_"
    return b


def strict_resolve_in_page(src: str, url: str, base: str | None) -> str | None:
    """``strict_resolve`` に ``<base href>`` を足したもの(相対 URL だけが base の影響を受ける)。"""
    pseudo = base_src(src, base)
    if pseudo is None:
        r = strip_site_host(_slashes(url.strip()))
        if r is None or r[0].startswith("/"):
            return strict_resolve(src, url)
        return None  # 外の base の下の相対 URL = 外のサイト
    return strict_resolve(pseudo, url)


def strict_resolve(src: str, url: str) -> str | None:
    """厳密な解決: 1 つの URL → サイトの根からのパス 1 つ(外のサイト・空・自分自身は None)。"""
    r = strip_site_host(_slashes(url.strip()))
    if r is None:
        return None
    path, _absolute = r
    path = path.split("#", 1)[0].split("?", 1)[0]
    if not path:
        return None
    path = unquote(path)
    if path.startswith("/"):
        return _norm(path) if path != "/" else ""
    joined = posixpath.join(posixpath.dirname(src), path)
    if joined.endswith("/") or path in (".", "./"):
        n = _norm(joined)
        return (n + "/") if n else ""
    return _norm(joined)


def strict_references(site: str, files: dict[str, int]) -> tuple[list[tuple[str, str, str]], int]:
    """[(参照元, 生の URL, 解決したパス)] と、読んだ html の数。"""
    refs = []
    n_html = 0
    for rel in files:
        low = rel.lower()
        if not low.endswith(HTML_EXT + (".css",)):
            continue
        if low.endswith(HTML_EXT):
            n_html += 1
        urls, base = strict_page(rel, read_text(site, rel))
        for url in urls:
            tgt = strict_resolve_in_page(rel, url, base)
            if tgt is not None:
                refs.append((rel, url, tgt))
    return refs, n_html


def _resolve_file(tgt: str, files, dirs) -> str | None:
    """配信で解決したときのファイル(ファイル / ディレクトリ + index.html / 拡張子なし + .html)。無ければ None。"""
    t = tgt.rstrip("/")
    if t == "":
        return "index.html" if "index.html" in files else None
    if not tgt.endswith("/") and t in files:
        return t
    if t in dirs and t + "/index.html" in files:
        return t + "/index.html"
    if not tgt.endswith("/") and t + ".html" in files:
        return t + ".html"
    return None


def _not_served_name(path: str) -> bool:
    """パスの要素のどこかが ``_`` か ``.`` で始まる(Jekyll が既定で配信しない名前)。"""
    return any(part[:1] in ("_", ".") for part in path.split("/"))


def _resolves_in(tgt: str, files, dirs) -> bool:
    """配信で解決できるか(ファイル、または ディレクトリ + index.html)。"""
    if tgt in ("", "/"):
        return "index.html" in files
    if tgt.endswith("/"):
        return tgt + "index.html" in files
    if tgt in files:
        return True
    if tgt in dirs:
        return tgt + "/index.html" in files
    return tgt + ".html" in files  # Jekyll の拡張子なし URL


# ---------------------------------------------------------------------------
# 門 4: ページの組み方(stylesheet・script・baseurl)
# ---------------------------------------------------------------------------

#: baseurl が repo 名に倒れたときの前置(https://<owner>.github.io/fullseye/ の形)。
BASEURL_FALLBACK_PREFIX = "/fullseye/"
#: 要約に「組み方の見本」を出すページ。
SAMPLE_PAGES = ("index.html", "view2026/index.html")


class _WiringParser(HTMLParser):
    """門 4 用: stylesheet の href・script の src・``/fullseye/`` 前置の参照・見本の欄を集める。

    門 1 の ``_StrictParser`` とは別に持つ(stylesheet と script だけを、属性の組で見る)。
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.wiring: list[tuple[str, str]] = []  # (種類, 生の URL)
        self.fullseye_prefixed: list[str] = []
        self.sample = {"stylesheet": [], "canonical": None, "og:url": None, "title": None, "generator": None}
        self.base: str | None = None
        self._in_title = False
        self._title: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = {k: (v or "") for k, v in attrs}
        if tag == "base" and self.base is None and "href" in a:
            self.base = a["href"].strip()
        for name, value in attrs:
            if not value:
                continue
            urls = parse_srcset(value) if name in STRICT_SRCSET_ATTRS else (
                [value.strip()] if name in STRICT_URL_ATTRS else [])
            for u in urls:
                if u == BASEURL_FALLBACK_PREFIX.rstrip("/") or u.startswith(BASEURL_FALLBACK_PREFIX):
                    self.fullseye_prefixed.append(u)
        rel = a.get("rel", "").lower().split()
        if tag == "link" and "stylesheet" in rel and a.get("href"):
            self.wiring.append(("stylesheet", a["href"].strip()))
            self.sample["stylesheet"].append(a["href"].strip())
        if tag == "link" and "canonical" in rel and self.sample["canonical"] is None:
            self.sample["canonical"] = a.get("href")
        if tag == "script" and a.get("src"):
            self.wiring.append(("script", a["src"].strip()))
        if tag == "meta":
            if a.get("property") == "og:url" and self.sample["og:url"] is None:
                self.sample["og:url"] = a.get("content")
            if a.get("name") == "generator" and self.sample["generator"] is None:
                self.sample["generator"] = a.get("content")
        if tag == "title" and self.sample["title"] is None:
            self._in_title = True

    def handle_endtag(self, tag):
        if tag == "title" and self._in_title:
            self._in_title = False
            self.sample["title"] = "".join(self._title).strip()

    def handle_data(self, data):
        if self._in_title:
            self._title.append(data)


def page_wiring(site: str, files: dict[str, int]) -> dict:
    """門 4: サイト内を指す stylesheet と script が全部実在するか、``/fullseye/`` 前置のページが無いか。

    サイト内 = 相対・ルート相対・このサイトの絶対 URL(``strict_resolve`` が None でないもの)。
    ``?query`` と ``#fragment`` は外して、ファイルそのものが在ることを求める(ディレクトリでは足りない)。
    空を通さない: サイト内を指す stylesheet が 1 本も無いサイトは落とす(既定テーマの CSS が全ページに
    付くはずなので、0 本は組み方が壊れた印)。
    """
    missing = []
    internal = {"stylesheet": 0, "script": 0}
    prefixed_pages = []
    samples = {}
    for rel in files:
        if not rel.lower().endswith(HTML_EXT):
            continue
        p = _WiringParser()
        p.feed(read_text(site, rel))
        p.close()
        for kind, url in p.wiring:
            tgt = strict_resolve_in_page(rel, url, p.base)
            if tgt is None:
                continue
            internal[kind] += 1
            if tgt not in files:
                missing.append({"page": rel, "kind": kind, "url": url, "target": tgt})
        if p.fullseye_prefixed:
            prefixed_pages.append({"page": rel, "first": p.fullseye_prefixed[0], "count": len(p.fullseye_prefixed)})
        if rel in SAMPLE_PAGES:
            samples[rel] = p.sample
    return {
        "wiring_internal_stylesheets": internal["stylesheet"],
        "wiring_internal_scripts": internal["script"],
        "wiring_missing": missing,
        "baseurl_prefixed_pages_count": len(prefixed_pages),
        "baseurl_prefixed_pages": prefixed_pages[:200],
        "build_samples": samples,
        "ok": not missing and not prefixed_pages and internal["stylesheet"] >= 1,
    }


def read_list(path: str) -> set[str]:
    """``snapshot`` が書いた一覧(1 行 1 パス)を読む。空の一覧は誤りとして拒む(空を通さない)。"""
    try:
        with open(path, encoding="utf-8") as f:
            out = {ln.rstrip("\n") for ln in f if ln.strip()}
    except OSError as e:
        raise SiteError(f"一覧が読めない: {path}: {e}") from e
    if not out:
        raise SiteError(f"一覧が空: {path}")
    return out


def _refuse_nested(site: str, source_docs: str) -> None:
    """``--site`` と ``--source-docs`` が同じか、片方がもう片方の中なら誤り(終了コード 2)。

    組んだサイトそのものを真値に渡すと、prune の後に残ったものが真値になり門 1 が空を通す
    (2026-11-11 の R3)。
    """
    a = os.path.normcase(os.path.realpath(site))
    b = os.path.normcase(os.path.realpath(source_docs))
    try:
        common = os.path.commonpath([a, b])
    except ValueError:  # 別のドライブ
        return
    if common in (a, b):
        raise SiteError(f"--source-docs と --site が同じか、片方がもう片方の中にある: {site} / {source_docs}。"
                        "--source-docs には repo の docs を渡す")


def run_check(site: str, source_docs: str, max_bytes: int, min_pages: int, min_kept_assets: int,
              built: set[str] | None = None) -> dict:
    """``built`` = 組んだ直後(prune の前)のサイトのファイル一覧(``snapshot``)。

    門 1 の真値は repo(``source_docs``)。ただし ``built`` を渡すと、repo にあっても Jekyll が
    **元から配信しない**もの(``_`` で始まる名前など。prune の前のサイトにも無い)は、門 1 ではなく
    ``not_built_assets`` に数える(prune が起こした欠けではないので)。``built`` は os.walk の一覧で、
    prune の読み方の結果ではない。
    """
    _refuse_nested(site, source_docs)
    files = walk_files(site)
    src_files = walk_files(source_docs)
    n_src_assets = sum(1 for q in src_files if q.startswith(ASSETS_PREFIX))
    if n_src_assets < min_kept_assets:
        raise SiteError(f"--source-docs の {ASSETS_PREFIX} が {n_src_assets} 本(床 {min_kept_assets} 未満)。"
                        "repo の docs を渡しているか確かめる")
    if built is not None and not set(files) <= built:
        extra = sorted(set(files) - built)
        raise SiteError(f"--built-list に無いファイルがサイトにある({len(extra)} 本、例 {extra[0]})。"
                        "一覧は prune の前の同じサイトで取ったものか")
    dirs = dirs_of(files)
    src_dirs = dirs_of(src_files)
    built_dirs = dirs_of(built) if built is not None else None
    refs, n_html = strict_references(site, files)
    missing = []
    not_built = []
    broken = []
    for src, url, tgt in refs:
        if tgt.startswith(ASSETS_PREFIX):
            if _resolve_file(tgt, files, dirs):
                continue
            item = {"page": src, "url": url, "target": tgt}
            in_src = _resolve_file(tgt, src_files, src_dirs)
            if built is not None:
                in_built = _resolve_file(tgt, built, built_dirs)
                if in_built:
                    missing.append(item)  # 組んだ直後は解決できた = prune が消した
                elif in_src and _not_served_name(in_src):
                    not_built.append(item)  # repo にあるが Jekyll が元から配信しない名前
                elif in_src:
                    missing.append(item)  # repo にあり配信される名前なのに組んだ直後にも無い = 疑わしい
                else:
                    broken.append(item)  # どこにも無い(元から切れている)
            elif in_src:
                missing.append(item)
            else:
                broken.append(item)
        elif not _resolves_in(tgt, files, dirs):
            broken.append({"page": src, "url": url, "target": tgt})
    kept_assets = sum(1 for p in files if p.startswith(ASSETS_PREFIX))
    total = sum(files.values())
    tar_headers = len(files) * TAR_HEADER_BYTES
    total_est = total + tar_headers
    gates = {
        "gate1_assets_present": not missing,
        "gate2_size": total_est <= max_bytes,
        "gate3_min_pages": n_html >= min_pages,
        "gate3_min_kept_assets": kept_assets >= min_kept_assets,
    }
    wiring = page_wiring(site, files)
    gates["gate4_page_wiring"] = wiring.pop("ok")
    return {
        **wiring,
        "site": os.path.abspath(site),
        "html_pages": n_html,
        "strict_references": len(refs),
        "strict_asset_references": sum(1 for _s, _u, t in refs if t.startswith(ASSETS_PREFIX)),
        "kept_assets": kept_assets,
        "kept_assets_bytes": sum(v for p, v in files.items() if p.startswith(ASSETS_PREFIX)),
        "site_bytes": total,
        "tar_header_estimate_bytes": tar_headers,
        "site_bytes_with_tar_headers": total_est,
        "max_bytes": max_bytes,
        "margin_bytes": max_bytes - total_est,
        "min_pages": min_pages,
        "min_kept_assets": min_kept_assets,
        "missing_assets": missing,
        "built_list_used": built is not None,
        "not_built_assets_count": len(not_built),
        "not_built_assets": not_built,
        "broken_internal_links_count": len(broken),
        "broken_asset_links_count": sum(1 for b in broken if b["target"].startswith(ASSETS_PREFIX)),
        "broken_internal_links": broken,
        "gates": gates,
        "ok": all(gates.values()),
    }


# ---------------------------------------------------------------------------
# 報告
# ---------------------------------------------------------------------------

def _mib(n: int) -> str:
    return f"{n / 1048576:,.1f} MiB"


def prune_summary(rep: dict) -> str:
    mode = "消した" if rep.get("applied") else "消す予定(--apply 無し、何も消していない)"
    return "\n".join([
        "## Pages: 参照されない assets を配備物から外す(prune)",
        "",
        f"- 読んだテキスト {rep['texts_read']:,} 本(うち html {rep['html_pages']:,} ページ)",
        f"- 残した assets {rep['kept_assets']:,} 本 / {_mib(rep['kept_assets_bytes'])}",
        f"- {mode} assets {rep['removed_assets']:,} 本 / {_mib(rep['removed_assets_bytes'])}",
        f"- サイトの総量 {_mib(rep['site_bytes_before'])} → {_mib(rep['site_bytes_after'])}",
        f"- 所要 {rep['seconds']:.1f} 秒",
        "",
    ])


def check_summary(rep: dict) -> str:
    g = rep["gates"]
    mark = {True: "通過", False: "**落ちた**"}
    lines = [
        "## Pages: 外した後のサイトの検査(check)",
        "",
        f"- 門 1 repo にある assets への参照が全部サイトに在る: {mark[g['gate1_assets_present']]}"
        f"(欠け {len(rep['missing_assets'])} 件 / assets への参照 {rep['strict_asset_references']:,} 件)",
        f"- 門 2 総量 {rep['site_bytes']:,} B + tar の見出しの見積もり {rep['tar_header_estimate_bytes']:,} B"
        f" = {rep['site_bytes_with_tar_headers']:,} B ≤ {rep['max_bytes']:,} B: {mark[g['gate2_size']]}"
        f"(1 GB まで残り {_mib(rep['margin_bytes'])} = {100 * rep['margin_bytes'] / rep['max_bytes']:.1f} %)",
        f"- 門 3 html {rep['html_pages']:,} ≥ {rep['min_pages']:,}: {mark[g['gate3_min_pages']]}"
        f" / 残った assets {rep['kept_assets']:,} ≥ {rep['min_kept_assets']:,}: {mark[g['gate3_min_kept_assets']]}",
        f"- 門 4 サイト内の stylesheet・script が全部在り、`/fullseye/` 前置のページが無い: {mark[g['gate4_page_wiring']]}"
        f"(stylesheet {rep['wiring_internal_stylesheets']:,} 本・script {rep['wiring_internal_scripts']:,} 本、"
        f"欠け {len(rep['wiring_missing'])} 件、`/fullseye/` 前置 {rep['baseurl_prefixed_pages_count']} ページ)",
        f"- 報告だけ: 解決できない内部リンク(repo でも解決できない assets への参照を含む) {rep['broken_internal_links_count']:,} 件"
        f"(うち assets を指すもの {rep['broken_asset_links_count']:,} 件)",
        f"- 報告だけ: repo にあるが組んだ直後のサイトにも無い assets への参照(Jekyll が配信しない名前)"
        f" {rep['not_built_assets_count']:,} 件",
        f"- 所要 {rep['seconds']:.1f} 秒",
        "",
    ]
    lines.append("### 組み方の見本(legacy の値と見比べる)")
    for page in SAMPLE_PAGES:
        smp = rep["build_samples"].get(page)
        if smp is None:
            lines.append(f"- `{page}`: (サイトに無い)")
            continue
        lines.append(f"- `{page}` stylesheet: {', '.join('`%s`' % h for h in smp['stylesheet']) or '(無し)'}")
        for key in ("canonical", "og:url", "title", "generator"):
            lines.append(f"- `{page}` {key}: `{smp[key]}`")
    lines.append("")
    if rep["wiring_missing"] or rep["baseurl_prefixed_pages"]:
        lines.append("### 門 4 に引っかかったもの")
        for m in rep["wiring_missing"][:100]:
            lines.append(f"- `{m['page']}` の {m['kind']} `{m['url']}` が無い(`{m['target']}`)")
        for m in rep["baseurl_prefixed_pages"][:100]:
            lines.append(f"- `{m['page']}` に `/fullseye/` 前置の参照 {m['count']} 本(例 `{m['first']}`)")
        lines.append("")
    if rep["missing_assets"]:
        lines.append("### 欠けた assets(参照元のページ → 参照)")
        for m in rep["missing_assets"][:200]:
            lines.append(f"- `{m['page']}` → `{m['url']}`(`{m['target']}`)")
        lines.append("")
    return "\n".join(lines)


def _write_reports(rep: dict, summary: str, args) -> None:
    if args.report_json:
        with open(args.report_json, "w", encoding="utf-8") as f:
            json.dump(rep, f, ensure_ascii=False, indent=1)
    if args.summary_md:
        with open(args.summary_md, "a", encoding="utf-8") as f:
            f.write(summary + "\n")
    print(summary)


def _positive_int(s: str) -> int:
    v = int(s)
    if v < 1:
        raise argparse.ArgumentTypeError("1 以上を渡す(0 では床にならない)")
    return v


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("prune", help="参照されない articles/assets/** を外す(緩い読み方)")
    p.add_argument("--site", required=True)
    p.add_argument("--apply", action="store_true", help="実際に消す(無ければ数えるだけ)")
    p.add_argument("--report-json")
    p.add_argument("--summary-md", help="人が読む要約を追記するファイル($GITHUB_STEP_SUMMARY など)")
    p.add_argument("--list", action="store_true", help="消す(消した)ファイルを 1 行ずつ出す")

    n = sub.add_parser("snapshot", help="組んだ直後のサイトのファイル一覧を書く(check --built-list 用)")
    n.add_argument("--site", required=True)
    n.add_argument("--out", required=True)

    c = sub.add_parser("check", help="外した後のサイトを検める(厳密な読み方、門 1〜3)")
    c.add_argument("--site", required=True)
    c.add_argument("--source-docs", required=True, help="repo の docs(門 1 の真値)")
    c.add_argument("--max-bytes", required=True, type=_positive_int)
    c.add_argument("--min-pages", required=True, type=_positive_int)
    c.add_argument("--min-kept-assets", required=True, type=_positive_int)
    c.add_argument("--built-list", help="snapshot の一覧(prune の前)。元から配信されない assets を門 1 から分ける")
    c.add_argument("--report-json")
    c.add_argument("--summary-md")

    args = ap.parse_args(argv)
    t0 = time.monotonic()
    try:
        if args.cmd == "prune":
            rep = plan_prune(args.site)
            rep["applied"] = bool(args.apply)
            if args.apply:
                apply_prune(args.site, rep["remove"])
                after = walk_files(args.site)
                rep["site_bytes_after"] = sum(after.values())
            rep["seconds"] = time.monotonic() - t0
            if args.list:
                for r in rep["remove"]:
                    print(r)
            _write_reports(rep, prune_summary(rep), args)
            return 0
        if args.cmd == "snapshot":
            listing = sorted(walk_files(args.site))
            if not listing:
                raise SiteError(f"サイトが空: {args.site}")
            with open(args.out, "w", encoding="utf-8", newline="\n") as f:
                f.write("".join(p + "\n" for p in listing))
            print(f"snapshot: {len(listing):,} files -> {args.out}")
            return 0
        built = read_list(args.built_list) if args.built_list else None
        rep = run_check(args.site, args.source_docs, args.max_bytes, args.min_pages, args.min_kept_assets, built)
        rep["seconds"] = time.monotonic() - t0
        _write_reports(rep, check_summary(rep), args)
        if not rep["ok"]:
            for m in rep["missing_assets"]:
                print(f"MISSING {m['page']} -> {m['url']} ({m['target']})", file=sys.stderr)
            for m in rep["wiring_missing"]:
                print(f"WIRING {m['page']} {m['kind']} -> {m['url']} ({m['target']})", file=sys.stderr)
            for m in rep["baseurl_prefixed_pages"]:
                print(f"BASEURL {m['page']} -> {m['first']}", file=sys.stderr)
            return 1
        return 0
    except SiteError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
