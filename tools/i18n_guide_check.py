# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""i18n_guide_check — 知識ガイドの訳(``<name>.en.md`` / ``<name>.zh.md``)を原文と機械で照合する。

    py -3.11 tools/i18n_guide_check.py docs/ops/2d/guides/colorimetry.md      # 1 本(en と zh)
    py -3.11 tools/i18n_guide_check.py docs/ops/2d/guides/colorimetry.md --lang en
    py -3.11 tools/i18n_guide_check.py --all                                  # 知識ガイド全部
    py -3.11 tools/i18n_guide_check.py --sha docs/ops/2d/guides/colorimetry.md # source_sha256 の値

訳のファイルの形式(1.0.0 の文書の門、2026-11-06 に 3 担当で決めた共通規則):

* 原文の横に置く: ``<name>.md`` → ``<name>.en.md`` / ``<name>.zh.md``。
* front matter は**原文の写し**で ``title`` だけ訳す(原文に ``title_<lang>`` があればその値)。
  そのうえで ``lang`` / ``translation_of``(原文の repo 相対パス、``/`` 区切り)/
  ``source_sha256``(原文の、**改行を LF に正規化した UTF-8 のバイト列**の SHA-256)を足す。
* 本文は原文の構造を保つ。機械で照合するのは:
  (a) バッククォートの code span の**集合**、(b) 数値の**多重集合**(桁区切りの違いは正規化)、
  (c) URL の集合、(d) 見出し(数と深さの並び)・表の行数・コードブロックの数。

``source_sha256`` が原文の今の中身と合わなければ落ちる —— 原文を直したら、訳し直すまで門が赤
(``docs/i18n/op_rest.json`` の指紋と同じ考え方。古い訳は無訳より悪い)。

照合は**同じ物を数えているか**であって、訳の良し悪しは見ない。数が合っても訳が正しい保証は
無いので、ここが緑でも人(または別の読み手)が読む。
"""
from __future__ import annotations

import argparse
import collections
import decimal
import hashlib
import os
import re
import sys
import unicodedata

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: 訳を置く言語(1.0.0 の門)。
TARGET_LANGS = ("en", "zh")

#: 訳の front matter に足す 3 キー。
ADDED_KEYS = ("lang", "translation_of", "source_sha256")


# --------------------------------------------------------------------------- #
# 読む                                                                         #
# --------------------------------------------------------------------------- #
def normalized_bytes(data: bytes) -> bytes:
    """改行を LF に正規化したバイト列(CRLF / CR → LF)。中身は UTF-8 として扱う。"""
    return data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def normalized_sha256(path: str) -> str:
    """``source_sha256`` の値: 改行を LF に正規化した UTF-8 のバイト列の SHA-256(16 進)。

    Windows の作業木は ``core.autocrlf`` で CRLF になるので、正規化しないと同じ原文でも
    OS で値が変わる。
    """
    with open(path, "rb") as f:
        return hashlib.sha256(normalized_bytes(f.read())).hexdigest()


def read_text(path: str) -> str:
    with open(path, "rb") as f:
        return normalized_bytes(f.read()).decode("utf-8")


def split_front(text: str) -> tuple[dict, str]:
    """``(front matter の dict, 本文)``。front matter が無ければ ``({}, text)``。

    YAML 依存を持たない最小の読み方(``tools/opdocs._guide_front`` と同じ: ``key: value`` の行だけ)。
    """
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return {}, text
    front = {}
    for j in range(1, len(lines)):
        if lines[j].strip() == "---":
            return front, "\n".join(lines[j + 1:])
        if ":" in lines[j]:
            k, v = lines[j].split(":", 1)
            front[k.strip()] = v.strip()
    return {}, text                                     # 閉じていない —— front matter とみなさない


# --------------------------------------------------------------------------- #
# 構造を数える                                                                 #
# --------------------------------------------------------------------------- #
_FENCE = re.compile(r"^\s*(```|~~~)")
_HEADING = re.compile(r"^(#{1,6})\s+\S")
_CODE_SPAN = re.compile(r"(?<!`)(`+)(?!`)(.+?)(?<!`)\1(?!`)")
#: URL の終わり: 空白・括弧・引用符・全角の句読点(日本語・中国語の地の文に続くとき)。
_URL = re.compile(r"https?://[^\s<>()\[\]\"'`、。，；：！？）」』]+")
#: 数の字句。★桁区切りは **ASCII の ``,`` だけ**(全角の ``，`` は中国語の読点で、数を区切る ——
#: NFKC を先に掛けると ``350，424`` が ``350,424`` に化けて 1 つの数になる。訳 A の報告、2026-11-06)。
#: 数字は ASCII と全角(全角は字句を切り出した後に NFKC でそろえる)。
#: 後ろの単位: 和文・中文の ``万 / 千万 / 億 / 亿 / 兆``(空白は任意)と、英語の数詞
#: ``million / billion / trillion``(空白か ``-`` でつなぐ。``10-million`` / ``1.5 billion``)。
_NUM = re.compile(r"([0-9０-９][0-9０-９,]*(?:[.．][0-9０-９]+)?)"
                  r"(?:\s*(千万|万|億|亿|兆)|(?:\s+|-)(million|billion|trillion)\b)?", re.I)
#: 単位 -> 倍率(``100 万`` = ``1,000,000`` = ``1 million``)。訳で桁に展開しても、数詞で書いても同じ数として数える。
_UNIT = {"万": 10 ** 4, "千万": 10 ** 7, "億": 10 ** 8, "亿": 10 ** 8, "兆": 10 ** 12,
         "million": 10 ** 6, "billion": 10 ** 9, "trillion": 10 ** 12}
_THOUSANDS = re.compile(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?")


def _prose_and_code(body: str) -> tuple[list[tuple[int, str]], int]:
    """``([(行番号, フェンスの外の行)], コードブロックの数)``。フェンスの中の行は落とす。"""
    out, blocks, in_code, fence = [], 0, False, ""
    for n, line in enumerate(body.split("\n"), 1):
        m = _FENCE.match(line)
        if m:
            if not in_code:
                in_code, fence = True, m.group(1)
                blocks += 1
                continue
            if m.group(1) == fence:
                in_code = False
                continue
        if not in_code:
            out.append((n, line))
    return out, blocks


def _numbers(text: str) -> collections.Counter:
    """数値の多重集合。

    * 字句は原文のまま切り出す(桁区切りは ASCII の ``,`` だけ。全角の ``，`` は数を区切る)。
      切り出した字句だけを NFKC で半角にそろえる(全角数字 ``１２`` = ``12``)。
    * ``1,234`` の桁区切りを外す(``1,2`` のような桁区切りでないカンマは 2 つの数)。
    * ``100 万`` / ``1.5 億`` / ``3 亿`` / ``10-million`` は単位を掛けて展開する(``1000000`` /
      ``150000000`` / ``300000000`` / ``10000000``)。原文の「万・億」を訳で ``1,000,000`` や
      ``1 million`` と書いても一致する(訳 A・B の報告、2026-11-06)。
      ``2 億 5000 万`` のような 2 段の書き方は段ごとに展開する(合算しない)。
    """
    c = collections.Counter()
    for m in _NUM.finditer(text):
        tok = unicodedata.normalize("NFKC", m.group(1)).rstrip(",")
        unit = m.group(2) or (m.group(3) or "").lower() or None
        if "," in tok and not _THOUSANDS.fullmatch(tok):
            parts = [p for p in tok.split(",") if p]
        else:
            parts = [tok.replace(",", "")]
        if unit:
            last = decimal.Decimal(parts[-1]) * _UNIT[unit]
            parts[-1] = format(last.normalize(), "f") if last != last.to_integral() else str(int(last))
        c.update(parts)
    return c


def _urls(text: str) -> set:
    return {u.rstrip(".,;:!?*_") for u in _URL.findall(text)}


def structure(body: str) -> dict:
    """本文(front matter を除く)の照合用の要約。

    返り値のキー: ``code_spans``(集合)/ ``numbers``(Counter)/ ``urls``(集合)/
    ``headings``(深さの並び)/ ``table_rows``(行数)/ ``code_blocks``(数)。
    code span・見出し・表はフェンスの外だけを数える。数値と URL は本文全体(コードの中も原文のまま
    写す決まりなので、両側で同じになる)。
    """
    prose, blocks = _prose_and_code(body)
    spans, heads, rows = set(), [], 0
    for _n, line in prose:
        for _ticks, inner in _CODE_SPAN.findall(line):
            spans.add(inner.strip())
        m = _HEADING.match(line)
        if m:
            heads.append(len(m.group(1)))
        if line.lstrip().startswith("|"):
            rows += 1
    return {"code_spans": spans, "numbers": _numbers(body), "urls": _urls(body),
            "headings": heads, "table_rows": rows, "code_blocks": blocks}


def _short(items, k: int = 6) -> str:
    items = sorted(items, key=str)
    return ", ".join(repr(x) for x in items[:k]) + (" …(+%d)" % (len(items) - k) if len(items) > k else "")


def compare_structure(src_body: str, tr_body: str) -> list[str]:
    """原文と訳の本文を照合し、合わない項目を人が読める文で返す(空 = 一致)。"""
    a, b = structure(src_body), structure(tr_body)
    probs = []
    if a["code_spans"] != b["code_spans"]:
        probs.append("code span の集合が違う: 訳に無い %s / 原文に無い %s"
                     % (_short(a["code_spans"] - b["code_spans"]), _short(b["code_spans"] - a["code_spans"])))
    if a["numbers"] != b["numbers"]:
        lost, extra = a["numbers"] - b["numbers"], b["numbers"] - a["numbers"]
        probs.append("数値の多重集合が違う: 訳で減った %s / 訳で増えた %s"
                     % (_short(lost.elements()), _short(extra.elements())))
    if a["urls"] != b["urls"]:
        probs.append("URL の集合が違う: 訳に無い %s / 原文に無い %s"
                     % (_short(a["urls"] - b["urls"]), _short(b["urls"] - a["urls"])))
    if a["headings"] != b["headings"]:
        probs.append("見出しの数・深さが違う: 原文 %d 個 %s / 訳 %d 個 %s"
                     % (len(a["headings"]), a["headings"][:12], len(b["headings"]), b["headings"][:12]))
    for key, label in (("table_rows", "表の行数"), ("code_blocks", "コードブロックの数")):
        if a[key] != b[key]:
            probs.append("%sが違う: 原文 %d / 訳 %d" % (label, a[key], b[key]))
    return probs


# --------------------------------------------------------------------------- #
# front matter                                                                 #
# --------------------------------------------------------------------------- #
def repo_rel(path: str, root: str = _ROOT) -> str:
    """repo 相対・``/`` 区切りのパス(``translation_of`` の値の形)。"""
    return os.path.relpath(os.path.abspath(path), root).replace(os.sep, "/")


def compare_front(src_front: dict, tr_front: dict, lang: str, src_rel: str, src_sha: str) -> list[str]:
    """訳の front matter が「原文の写し + 3 キー、title だけ訳」になっているか。"""
    probs = []
    if not tr_front:
        return ["訳に front matter が無い"]
    if tr_front.get("lang") != lang:
        probs.append("lang が %r(期待 %r)" % (tr_front.get("lang"), lang))
    if tr_front.get("translation_of") != src_rel:
        probs.append("translation_of が %r(期待 %r)" % (tr_front.get("translation_of"), src_rel))
    if tr_front.get("source_sha256") != src_sha:
        probs.append("source_sha256 が原文の今の中身と合わない(訳 %s / 原文 %s)—— 原文が変わったなら訳し直す"
                     % (tr_front.get("source_sha256"), src_sha))
    for k, v in src_front.items():
        if k == "title":
            want = src_front.get("title_" + lang)
            got = tr_front.get("title", "")
            if want and got != want:
                probs.append("title が原文の title_%s と違う: %r(期待 %r)" % (lang, got, want))
            elif not got:
                probs.append("title が空")
            continue
        if k in ADDED_KEYS:
            continue
        if tr_front.get(k) != v:
            probs.append("front matter の %s が原文の写しでない: %r(原文 %r)" % (k, tr_front.get(k), v))
    extra = sorted(set(tr_front) - set(src_front) - set(ADDED_KEYS))
    if extra:
        probs.append("原文に無い front matter のキー: %s" % ", ".join(extra))
    return probs


# --------------------------------------------------------------------------- #
# 1 組を照合                                                                    #
# --------------------------------------------------------------------------- #
def translation_path(src_path: str, lang: str) -> str:
    """``<name>.md`` → ``<name>.<lang>.md``。"""
    base, ext = os.path.splitext(src_path)
    return "%s.%s%s" % (base, lang, ext)


def check_texts(src_text: str, tr_text: str, lang: str, src_rel: str, src_sha: str) -> list[str]:
    """原文と訳の**テキスト**を照合する(ファイルを読まない版。テストと :func:`check_pair` が使う)。"""
    sf, sb = split_front(src_text)
    tf, tb = split_front(tr_text)
    probs = compare_front(sf, tf, lang, src_rel, src_sha) + compare_structure(sb, tb)
    # ★コードブロックの中は数えない(2026-11-06 の決定、docs/I18N.md): 中のコメントや mermaid の
    #   ラベルは訳してもよく、原文のまま写してもよい。地の文(フェンスと code span の外)は訳す。
    if lang in ("en", "zh"):
        res = japanese_residue(tb, lang)
        if res:
            probs.append("地の文に日本語が %d 行残る(コードブロックと code span は除いて数えた): %s"
                         % (len(res), "; ".join("L%d %s" % (n, s) for n, s in res[:5])))
    return probs


def check_pair(src_path: str, lang: str, root: str = _ROOT) -> list[str]:
    """原文 ``src_path`` とその ``lang`` 訳を照合する。訳が無ければ ``["訳が無い: …"]``。"""
    tp = translation_path(src_path, lang)
    if not os.path.exists(tp):
        return ["訳が無い: %s" % repo_rel(tp, root)]
    return check_texts(read_text(src_path), read_text(tp), lang,
                       repo_rel(src_path, root), normalized_sha256(src_path))


# --------------------------------------------------------------------------- #
# 生成物に日本語が残っていないか                                                 #
# --------------------------------------------------------------------------- #
#: 英語版で「残り」とみなす字: かな・CJK 統合漢字(拡張 A を含む)・全角記号・和文の括弧と句読点。
_RESIDUE_EN = re.compile(r"[　-〿぀-ヿ㐀-䶿一-鿿＀-￯]")
#: 中国語版で「残り」とみなす字: ひらがな・カタカナ(漢字は正当に出る)。
#: ★``・``(U+30FB 中点)と ``ー``(U+30FC 長音)も数える —— どちらも中国語の文章には出ない
#: (中国語の間隔号は ``·`` U+00B7)。
_RESIDUE_ZH = re.compile(r"[぀-ゟ゠-ヿㇰ-ㇿ]")


def _strip_code(line: str) -> str:
    """行から code span と URL を除く(コードは訳さない決まり —— 中の日本語は残りに数えない)。"""
    return _URL.sub(" ", _CODE_SPAN.sub(" ", line))


def japanese_residue(text: str, lang: str) -> list[tuple[int, str]]:
    """``lang`` 版の Markdown に残った日本語の行 ``[(行番号, 抜粋)]``(フェンスの中と code span は除く)。

    ``en``: かな・漢字・全角記号。``zh``: ひらがな・カタカナ(``・`` を含む)。
    """
    if lang not in ("en", "zh"):
        raise ValueError("japanese_residue: lang は en / zh(got %r)" % (lang,))
    pat = _RESIDUE_EN if lang == "en" else _RESIDUE_ZH
    out = []
    prose, _blocks = _prose_and_code(text)
    for n, line in prose:
        bare = _strip_code(line)
        m = pat.search(bare)
        if m:
            s = max(0, m.start() - 20)
            out.append((n, bare[s:s + 60].strip()))
    return out


# --------------------------------------------------------------------------- #
# CLI                                                                          #
# --------------------------------------------------------------------------- #
def _knowledge_guide_paths() -> list[str]:
    sys.path.insert(0, os.path.join(_ROOT, "tools"))
    import opdocs as OD
    return [g["path"] for g in OD.knowledge_guides()]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src", nargs="*", help="原文のガイド(<name>.md)")
    ap.add_argument("--lang", default=",".join(TARGET_LANGS), help="照合する言語(カンマ区切り、既定 en,zh)")
    ap.add_argument("--all", action="store_true", help="知識ガイド全部(tools/opdocs.knowledge_guides)")
    ap.add_argument("--sha", action="store_true", help="原文の source_sha256 を出すだけ")
    args = ap.parse_args(argv)
    srcs = list(args.src)
    if args.all:
        srcs += _knowledge_guide_paths()
    if not srcs:
        ap.error("原文のパスか --all を渡す")
    if args.sha:
        for s in srcs:
            print("%s  %s" % (normalized_sha256(s), repo_rel(s)))
        return 0
    langs = [x.strip() for x in args.lang.split(",") if x.strip()]
    bad = 0
    for s in srcs:
        if not os.path.exists(s):
            print("NG %s: 原文が無い" % s)
            bad += 1
            continue
        for lang in langs:
            probs = check_pair(s, lang)
            tag = "%s [%s]" % (repo_rel(translation_path(s, lang)), lang)
            if probs:
                bad += 1
                print("NG %s" % tag)
                for p in probs:
                    print("   - " + p)
            else:
                print("OK %s" % tag)
    print("%d 組を照合、不一致 %d 組" % (len(srcs) * len(langs), bad))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
