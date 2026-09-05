# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""opdocs — single-source-of-truth operator documentation (Markdown) + derived help.

The Markdown under ``docs/ops/`` is the **source of truth** for operator docs: one
note per operator (``docs/ops/<dim>/<category>/<op>.md``), a hand/agent-authored
family usage guide per op-family (``docs/ops/2d/guides/<family>.md``, math は
``docs/ops/math/guides/``), and an **auto-generated** table of contents that simply
walks the folder hierarchy. Studio's per-op HTML help (``studio_assets/op_help/``)
is produced by **bulk-converting** that Markdown — never authored twice. The same
Markdown tree is shaped as an AI-usage corpus (file-per-note) so an assistant can
grasp *how to use* each op.

Dimensions: ``2d`` (ops.REGISTRY), ``3d`` (ops3d.OPS3D), ``math`` (opsmath.OPSMATH)
and ``optics`` (opsoptics.OPSOPTICS). The two *ledger* dimensions share one code
path (:data:`LEDGER_DIMS`): notes land in ``docs/ops/<dim>/<category>/<op>.md``
and help pages in ``op_help/<dim>/``, namespaced like 3-D.

Subcommands (all idempotent; safe to re-run)::

    py -3.11 tools/opdocs.py md      # (re)write per-op Markdown notes (deterministic)
    py -3.11 tools/opdocs.py toc     # (re)write INDEX.md files by walking the tree
    py -3.11 tools/opdocs.py html    # bulk-convert 2-D Markdown -> Studio HTML help
    py -3.11 tools/opdocs.py all     # md + toc + html

Per-op notes and every INDEX.md are **generated** — do not hand-edit (a drift test
regenerates and diffs). The guides under ``docs/ops/<dim>/guides/`` are authored and
are NOT overwritten by ``md``. They come in two kinds (see :func:`knowledge_guides`):

* **family guide** — filename equals the family name; linked from every op note of
  that family.
* **knowledge guide** — cross-cutting background (colorimetry, depth sensors,
  measurement uncertainty, dataset conventions …); linked from the op notes named by
  its ``applies_to`` frontmatter (``<dim>`` or ``<dim>/<category>``).
"""
from __future__ import annotations

import glob
import hashlib
import html as _html
import inspect
import json
import os
import re
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "tools"))

DOCS = os.path.join(_ROOT, "docs", "ops")
HELP_ROOT = os.path.join(_ROOT, "studio_assets", "op_help")
_GEN_MARK = "<!-- opdocs:generated — do not edit; source of truth is docs/ops/*.md (tools/opdocs.py html) -->"

_AMBER = "#f5a524"
_TEAL = "#17b8a6"
_MUTE = "#8b91a0"
_CODE = "#22d3bf"

#: Ledger dimensions — registries that describe their ops with a typed catalog
#: instead of a 2-D/3-D op table. They share one notes/TOC/HTML code path; each
#: gets its own ``docs/ops/<dim>/`` tree, ``op_help/<dim>/`` help dir, anchor
#: namespace (``op<dim>:`` / ``guide<dim>:``) and one authored family guide.
LEDGER_DIMS = {
    "math": {"registry": "opsmath", "table": "OPSMATH", "module": "mathops",
             "family": "math_metrology"},
    "optics": {"registry": "opsoptics", "table": "OPSOPTICS", "module": "optics",
               "family": "optics_imaging"},
    "lightfield": {"registry": "opslightfield", "table": "OPSLIGHTFIELD",
                   "module": "lightfield", "family": "lightfield_depth"},
    "photon": {"registry": "opsphoton", "table": "OPSPHOTON",
               "module": "photoncount", "family": "photon_timeresolved"},
    "specular": {"registry": "opsspecular", "table": "OPSSPECULAR",
                 "module": "specularity", "family": "specular_photometric"},
    "motionmag": {"registry": "opsmotionmag", "table": "OPSMOTIONMAG",
                  "module": "motionmag", "family": "motion_magnification"},
    "quat": {"registry": "opsquat", "table": "OPSQUAT",
             "module": "quatimage", "family": "quaternion_monogenic"},
    "rangedoppler": {"registry": "opsrangedoppler", "table": "OPSRANGEDOPPLER",
                     "module": "rangedoppler", "family": "fmcw_range_doppler"},
    "acoustics": {"registry": "opsacoustics", "table": "OPSACOUSTICS",
                  "module": "acoustics", "family": "acoustic_condition_monitoring"},
    "interferometry": {"registry": "opsinterferometry", "table": "OPSINTERFEROMETRY",
                       "module": "interferometry", "family": "coherence_scanning"},
    # --- 2026-09-02 に登録した族。ここに載っていなかったあいだ、これらの op は
    #     docs/ops に 1 枚もノートを持っていなかった(RAG コーパスから丸ごと
    #     欠けていた)。ガイドは未執筆で、リンクは実在するときだけ張られる。
    "tomography": {"registry": "opstomography", "table": "OPSTOMOGRAPHY",
                   "module": "tomography", "family": "computed_tomography"},
    "volcolor": {"registry": "opsvolcolor", "table": "OPSVOLCOLOR",
                 "module": "volcolor", "family": "volume_labelling"},
    "reprconv": {"registry": "opsreprconv", "table": "OPSREPRCONV",
                 "module": "reprconv", "family": "representation_conversion"},
    "cadmap": {"registry": "opscadmap", "table": "OPSCADMAP",
               "module": "cadmap", "family": "cad_surface_mapping"},
    "annotate": {"registry": "opsannotate", "table": "OPSANNOTATE",
                 "module": "annotate", "family": "figure_annotation"},
    "gfx2d": {"registry": "opsgfx2d", "table": "OPSGFX2D",
              "module": "gfx2d", "family": "game_graphics_2d"},
    "imgmetrics": {"registry": "opsimgmetrics", "table": "OPSIMGMETRICS",
                   "module": "imgmetrics", "family": "image_difference_metrics"},
    "colortransport": {"registry": "opscolortransport", "table": "OPSCOLORTRANSPORT",
                       "module": "colortransport", "family": "optimal_transport"},
    "imgforensics": {"registry": "opsimgforensics", "table": "OPSIMGFORENSICS",
                     "module": "imgforensics", "family": "image_forensics"},
    "astrostack": {"registry": "opsastrostack", "table": "OPSASTROSTACK",
                   "module": "astrostack", "family": "astro_stacking"},
    # 2026-09-03: ストリーミング動画処理(リング/状態つき op/パイプライン)
    "videostream": {"registry": "opsvideostream", "table": "OPSVIDEOSTREAM",
                    "module": "videostream", "family": "video_streaming"},
}


def families_without_a_guide(recs):
    """ガイドが未執筆の族を数える —— **黙って消えないように**生成時に報告する。

    ノートのガイド節は実在するときだけ張るので、未執筆でもリンク切れは出ない。
    その代わり「書かれていない」ことが見えなくなるので、ここで数えて出す。
    """
    missing = {}
    for r in recs:
        fam = r.get("family")
        if not fam:
            continue
        dim = r["dim"]
        gp = os.path.join(DOCS, dim if dim in LEDGER_DIMS else "2d", "guides", fam + ".md")
        if not os.path.exists(gp):
            missing.setdefault(fam, 0)
            missing[fam] += 1
    return dict(sorted(missing.items()))

#: ガイドは二種ある。**族ガイド**はファイル名が族名と一致し(:data:`LEDGER_DIMS`
#: の ``family`` / 2-D は ``gallery2d_*``)、その族の全 op ノートから自動でリンク
#: される。**背景知識ガイド**は族に属さない横断的な教材(測色、深度センサ、計測の
#: 不確かさ、データセット規約 …)で、frontmatter の ``applies_to`` に書いた
#: ``<dim>`` または ``<dim>/<category>`` の op ノートからリンクされる。
#:
#: 置き場所(どの ``<dim>/guides/`` に置くか)は**分類であって配線ではない** ――
#: 例えばデータセット規約は ``annotate/guides/`` に置きつつ、生成側の op がいる
#: ``optics/scene`` からも辿れる。この分離が無かったあいだ、知識ガイドは INDEX に
#: しか出ず、**op から辿る経路が一本も無かった**(2026-09-05 に発見)。
_KNOWLEDGE_GUIDES = None


def _guide_front(path):
    """ガイド md の frontmatter を最小限だけ読む(YAML 依存を持たない)。"""
    front = {}
    try:
        with open(path, encoding="utf-8") as f:
            if f.readline().strip() != "---":
                return front
            for line in f:
                if line.strip() == "---":
                    break
                if ":" in line:
                    k, v = line.split(":", 1)
                    front[k.strip()] = v.strip()
    except OSError:
        pass
    return front


def _family_guide_stems():
    """族ガイドのファイル名(拡張子なし)の集合。"""
    stems = {m["family"] for m in LEDGER_DIMS.values()}
    stems |= {os.path.splitext(os.path.basename(p))[0]
              for p in glob.glob(os.path.join(DOCS, "2d", "guides", "gallery2d_*.md"))}
    return stems


def knowledge_guides():
    """背景知識ガイド一覧(族ガイドを除く全ガイド)。1 回だけ走査してキャッシュ。"""
    global _KNOWLEDGE_GUIDES
    if _KNOWLEDGE_GUIDES is None:
        fams = _family_guide_stems()
        out = []
        for g in sorted(glob.glob(os.path.join(DOCS, "*", "guides", "*.md"))):
            stem = os.path.splitext(os.path.basename(g))[0]
            if stem in fams:
                continue
            spec = _guide_front(g).get("applies_to", "").strip()
            targets = () if spec == "none" else tuple(
                t.strip() for t in spec.split(",") if t.strip())
            out.append({"path": g, "stem": stem, "title": _md_title(g),
                        "spec": spec, "applies_to": targets})
        _KNOWLEDGE_GUIDES = out
    return _KNOWLEDGE_GUIDES


def guides_for(dim, category):
    """``(dim, category)`` の op ノートから張るべき背景知識ガイド。"""
    return [g for g in knowledge_guides()
            if dim in g["applies_to"] or f"{dim}/{category}" in g["applies_to"]]


def guides_not_wired():
    """``applies_to`` を書き忘れた = **どの op からも辿れない**知識ガイド。

    リンク切れは出ないが「書いたのに繋がっていない」は見えなくなるので、
    :func:`families_without_a_guide` と同じ理由でここで数えて生成時に出す。

    ``applies_to: none`` は**意図的に配線しない**宣言(op 台帳に載っていない
    ファサード専用のガイドなど、繋ぐ先がそもそも無いもの)で、報告しない。
    書き忘れと区別できるように、空欄ではなく明示させている。
    """
    return [g["stem"] for g in knowledge_guides() if not g["applies_to"] and g["spec"] != "none"]


def guides_with_unknown_targets():
    """``applies_to`` が実在しない ``<dim>`` / ``<dim>/<category>`` を指しているもの。

    綴り違いを黙って無視すると「配線したつもり」で終わるので、報告して落とす
    材料にする。
    """
    dims = {d for d in ("2d", "3d", *LEDGER_DIMS) if os.path.isdir(os.path.join(DOCS, d))}
    known = set(dims)
    for d in dims:
        known |= {f"{d}/{c}" for c in _walk_ops(d)}
    bad = {}
    for g in knowledge_guides():
        miss = [t for t in g["applies_to"] if t not in known]
        if miss:
            bad[g["stem"]] = miss
    return bad


_AUTHOR = "Kazufumi Furuse"
_LICENSE = "Apache-2.0"
_COPYRIGHT = f"© 2026 {_AUTHOR} — Fullseye operator documentation. Licensed under {_LICENSE}."


# ------------------------------------------------------------------ #
# i18n —— ヘルプの「枠」の対訳
# ------------------------------------------------------------------ #
#: 出力する言語。``ja`` が**原文**(ベース言語)で、残りは対訳表からの差し替え。
#: 半導体サプライチェーンの主要国を見て選んだ: 台湾(繁体字)・韓国・ドイツ。
#: 追加は :data:`I18N_PATH` に 1 列足すだけ ―― 生成器のコード変更は要らない。
LANGS = ("ja", "en", "zh", "tw", "ko", "de")

#: 言語コード -> 自称表記(切替リンクに出す。英語名ではなく**その言語での名前**)。
LANG_NAMES = {"ja": "日本語", "en": "English", "zh": "简体中文",
              "tw": "繁體中文", "ko": "한국어", "de": "Deutsch"}

#: 標準の言語タグ(BCP 47)-> 上のコード。ファイル名を 2 文字でそろえたいので
#: 台湾は ``tw`` にしてあるが、``tw`` は本来 ISO 639-1 で Twi 語の記号なので、
#: OS/ブラウザのロケールから引くときはこの表を通す(``zh-Hant`` も同じ行き先)。
LANG_ALIASES = {"zh-tw": "tw", "zh-hant": "tw", "zh-hant-tw": "tw", "zh-hk": "tw",
                "zh-cn": "zh", "zh-hans": "zh", "ja-jp": "ja", "en-us": "en",
                "en-gb": "en", "ko-kr": "ko", "de-de": "de", "de-at": "de",
                "de-ch": "de"}


def normalize_lang(tag):
    """``zh-TW`` / ``zh-Hant`` のような標準タグを :data:`LANGS` のコードへ。

    未知のタグは主部分(``de-LU`` -> ``de``)で引き直し、それも無ければ ``en``。
    """
    t = (tag or "").strip().replace("_", "-").lower()
    if t in LANG_ALIASES:
        return LANG_ALIASES[t]
    if t in LANGS:
        return t
    head = t.split("-")[0]
    return head if head in LANGS else "en"

#: 枠の対訳表。**原文(日本語)がキー**で、値が言語コード -> 訳。studio.py の
#: :func:`tr` と同じ規約(ベース言語をキーにする)なので、翻訳者はキーを発明せずに
#: 済み、原文を変えれば「訳が古い」ことが未訳として即座に見える。
I18N_PATH = os.path.join(_ROOT, "docs", "i18n", "opdocs.json")

#: op 要約(docstring 1 行目)の対訳表。こちらは原文が長く数も多いので
#: ``<dim>/<op>`` をキーにし、原文の指紋 ``fp`` を併記する。**指紋が合わない訳は
#: 出さない**(原文が変わったのに訳が古いまま、が一番たちが悪い ――
#: :func:`op_summary_stale` が数える)。
SUMMARY_I18N_PATH = os.path.join(_ROOT, "docs", "i18n", "op_summary.json")

_I18N = None
_SUMMARY_I18N = None

#: :func:`T` が実際に引いた原文。対訳表の**過不足**をテストで突き合わせるための実測。
SEEN_STRINGS = set()


def _load_json(path, key):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f).get(key, {}) or {}
    except Exception:                                    # noqa: BLE001 — 訳が無くても原文で出す
        return {}


def _i18n():
    global _I18N
    if _I18N is None:
        _I18N = _load_json(I18N_PATH, "strings")
    return _I18N


def summary_i18n():
    global _SUMMARY_I18N
    if _SUMMARY_I18N is None:
        _SUMMARY_I18N = _load_json(SUMMARY_I18N_PATH, "summaries")
    return _SUMMARY_I18N


def T(s, lang="ja"):
    """生成文書の固定文言を ``lang`` へ。**原文(日本語)がキー**。

    未訳・未知の言語は**原文のまま**返す(壊れた訳より原文 —— studio.py の
    :func:`tr` と同じ規約)。黙って原文に落ちると「訳したつもり」になるので、
    引いた原文は :data:`SEEN_STRINGS` に記録し、テストが表と突き合わせる。
    """
    SEEN_STRINGS.add(s)
    if lang == "ja" or not s:
        return s
    return (_i18n().get(s) or {}).get(lang) or s


def fingerprint(text: str) -> str:
    """原文の指紋(先頭 12 桁)。訳が原文に追随しているかの判定にだけ使う。"""
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()[:12]


_CJK = re.compile(r"[぀-ヿ㐀-鿿＀-￯]")


def has_japanese(text) -> bool:
    """かな・漢字・全角記号を含むか(= 英語話者がそのままでは読めない散文か)。"""
    return bool(_CJK.search(text or ""))


def summary_and_rest(doc):
    """docstring を **先頭段落** と残りに割る。``(summary, rest)``。

    以前は「先頭の 1 行」を要約にしていたが、折り返した docstring では
    935 本のうち **35 本が文の途中で切れていた**(``…enclosed by a contour, from``)。
    切れた断片は訳しようがなく、訳してもそこだけ意味が通らない。段落で切っても
    総量はほぼ変わらない(実測 51,975 → 52,577 字)ので、段落を単位にする。
    """
    doc = (doc or "").strip()
    if not doc:
        return "", ""
    head, _, tail = doc.partition("\n\n")
    return " ".join(l.strip() for l in head.strip().split("\n")), tail.strip()


def not_in_language(text, lang) -> bool:
    """``text`` が読み手の言語で書かれて**いない**か(断り書きを出すかの判定)。

    原文は日本語か英語のどちらかしかないので、``zh`` / ``tw`` / ``ko`` / ``de``
    の読者にとっては常に別言語。``ja`` と ``en`` だけ中身を見て決める。
    """
    if lang == "ja":
        return not has_japanese(text)
    if lang == "en":
        return has_japanese(text)
    return True


def op_summary(rec, lang):
    """op 要約(先頭段落)の訳。``(text, in_readers_language)``。

    docstring は**もともと英語のものが混じっている**(要約 935 本のうち **349 本**)。
    それを英語の読者に出すとき「まだ訳がありません」と断るのは嘘なので、日本語を
    含まない原文は英語版では**訳済みとして扱う**(英語がこのリポジトリのベース言語)。

    ★逆向きも同じで、**``ja`` も翻訳先の 1 つ**である。原文が英語の 349 本は、
    日本語のヘルプを開いても英語のままだった —— 「原文だから ja は常に OK」と
    数えていたのが誤りで、実測の内訳は ja 586 / en 373 / 他 各 50(2026-09-05)。
    原文が日本語のときだけ ``ja`` は素通しにする。
    """
    src = summary_and_rest(rec.get("doc"))[0]
    if not src:
        return src, True
    if lang == "ja" and has_japanese(src):
        return src, True                                 # もともと日本語 —— 訳す物が無い
    if lang == "en" and not has_japanese(src):
        return src, True                                 # もともと英語 —— 訳す物が無い
    ent = summary_i18n().get("%s/%s" % (rec["dim"], rec["name"])) or {}
    if ent.get("fp") != fingerprint(src):
        return src, False                                # 原文が変わった → 古い訳は出さない
    tr = (ent.get(lang) or "").strip()
    return (tr, True) if tr else (src, False)


def op_summary_stale():
    """指紋が現行の原文と合わない要約訳のキー(= 出せない訳)を列挙する。"""
    recs, _, _, _ = _records()
    live = {"%s/%s" % (r["dim"], r["name"]):
            fingerprint(summary_and_rest(r.get("doc"))[0])
            for r in recs if (r.get("doc") or "").strip()}
    bad = []
    for k, ent in summary_i18n().items():
        if live.get(k) != ent.get("fp"):
            bad.append(k)
    return sorted(bad)

# ------------------------------------------------------------------ #
# registry access
# ------------------------------------------------------------------ #

def _lib_version() -> str:
    try:
        import fullseye
        return getattr(fullseye, "__version__", "0")
    except Exception:
        return "0"


_VERSION = _lib_version()


def _registry_fingerprint(recs) -> str:
    """Deterministic sha256 over op metadata — connects docs to the exact op set."""
    import hashlib
    payload = "\n".join(
        f"{r['dim']}|{r['name']}|{r['category']}|{r['in']}|{r['out']}|{r['halcon']}"
        for r in sorted(recs, key=lambda r: (r["dim"], r["name"])))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _catslug(cat: str) -> str:
    """Filesystem-safe category folder name (categories may contain '/' or '-')."""
    return re.sub(r"[^0-9a-zA-Z]+", "_", cat).strip("_").lower() or "misc"


def _family_map():
    """2-D op -> primary family (a gallery2d_* example id), and family -> [ops].

    Families are the coverage galleries (``examples/gallery2d_*.py``); each op is
    assigned to the gallery that exercises it (deterministic tie-break: the gallery
    covering the fewest ops, i.e. the most specific, then lexicographic)."""
    from op_example_index import build_index
    _, idx2d = build_index(split=True)
    fam_ops = {}
    for op, exs in idx2d.items():
        for e in exs:
            if e.startswith("gallery2d_"):
                fam_ops.setdefault(e, set()).add(op)
    size = {f: len(o) for f, o in fam_ops.items()}
    op_fam = {}
    for op, exs in idx2d.items():
        fams = sorted((e for e in exs if e.startswith("gallery2d_")),
                      key=lambda e: (size.get(e, 1 << 30), e))
        if fams:
            op_fam[op] = fams[0]
    return op_fam, fam_ops, idx2d


def _records():
    """Uniform per-op records for both dims. Returns (list, idx2d, op_fam, fam_ops)."""
    import ops
    op_fam, fam_ops, idx2d = _family_map()
    try:
        from op_example_index import build_index
        idx3d, _ = build_index(split=True)
    except Exception:
        idx3d = {}

    recs = []
    for o in ops.REGISTRY:
        fn = o.fn
        try:
            sig = str(inspect.signature(fn))
        except (TypeError, ValueError):
            sig = "(v, a, b)"
        recs.append({
            "dim": "2d", "name": o.name, "category": o.category,
            "in": o.in_sort, "out": o.out_sort,
            "halcon": (o.halcon or "").strip(),
            # ``Op.doc``(登録時に op 名で指定したもの)が第一で、無ければ実装の
            # docstring。逆にすると、汎用ファクトリが返す**共有の関数オブジェクト**
            # の docstring が勝ってしまう(backends_r3 の 56 op は fn が同一)。
            # cleandoc: 関数 docstring の 2 行目以降には定義位置ぶんの字下げが
            # 付いていて、そのまま出すと Markdown が**コードブロックと読む**
            # (3-D / ledger 側は最初からこれを通していた)。
            "doc": inspect.cleandoc(getattr(o, "doc", "") or fn.__doc__ or "").strip(),
            "module": "ops", "sig": sig,
            "examples": sorted(idx2d.get(o.name, [])),
            "family": op_fam.get(o.name),
        })
    try:
        import ops3d
        for name, info in ops3d.OPS3D.items():
            fn = info.get("func")
            try:
                sig = str(inspect.signature(fn)) if fn is not None else "(...)"
            except (TypeError, ValueError):
                sig = "(...)"
            ins = info["in"]
            ins = " × ".join(ins) if isinstance(ins, (list, tuple)) else str(ins)
            recs.append({
                "dim": "3d", "name": name, "category": info["category"],
                "in": ins, "out": info["out"],
                "halcon": "", "doc": (info.get("doc") or "").strip(),
                "module": info.get("module", "ops3d"), "sig": sig,
                "examples": sorted(idx3d.get(name, [])),
                "family": None, "gpu": bool(info.get("gpu")),
            })
    except Exception as e:  # ops3d needs torch-soft deps; corpus still builds for 2-D
        print(f"  (3-D registry unavailable: {e})", file=sys.stderr)
    for _dim, _meta in LEDGER_DIMS.items():
        try:
            ledger = getattr(__import__(_meta["registry"]), _meta["table"])
            from op_example_index import _index_for
            # ledger ops are demonstrated by scripts under examples/ (same dir as
            # 2-D); index them with the same call-detection used for the other dims.
            idx = _index_for(sorted(ledger), "examples")
            for name, info in ledger.items():
                fn = info.get("func")
                try:
                    sig = str(inspect.signature(fn)) if fn is not None else "(...)"
                except (TypeError, ValueError):
                    sig = "(...)"
                ins = info["in"]
                ins = " × ".join(ins) if isinstance(ins, (list, tuple)) else str(ins)
                doc = getattr(fn, "__doc__", None) or ""
                recs.append({
                    "dim": _dim, "name": name, "category": info["category"],
                    "in": ins, "out": info["out"],
                    # cleandoc: function docstrings carry the 4-space continuation
                    # indent, which Markdown would misread as a code block.
                    "halcon": "", "doc": inspect.cleandoc(doc).strip() if doc else "",
                    "module": info.get("module", _meta["module"]), "sig": sig,
                    "examples": sorted(idx.get(name, [])),
                    # one usage guide per ledger family, named after the coverage
                    # example that exercises its ops (2-D の gallery 命名と同型)
                    "family": _meta["family"],
                })
        except Exception as e:  # corpus still builds without a ledger
            print(f"  ({_dim} registry unavailable: {e})", file=sys.stderr)
    # mark ops whose name is registered more than once in their dim: a backend override
    # (e.g. backends_auto's _safe wrapper) shadows a core fallback of the same op. The note
    # for such a name describes the winner; flag it so the override is stated, not hidden.
    from collections import Counter
    for dim in ("2d", "3d"):
        cnt = Counter(r["name"] for r in recs if r["dim"] == dim)
        for r in recs:
            if r["dim"] == dim and cnt[r["name"]] > 1:
                r["override"] = True
    return recs, idx2d, op_fam, fam_ops


# ------------------------------------------------------------------ #
# per-op Markdown notes  (deterministic; source of truth)
# ------------------------------------------------------------------ #

def _rel(from_file: str, to_file: str) -> str:
    r = os.path.relpath(to_file, os.path.dirname(from_file)).replace(os.sep, "/")
    return r


def _op_md(rec, path, by_name, lang="ja", verbatim_doc=None):
    """1 op 分のノート(Markdown)。``lang`` は**枠**の言語。

    枠(見出し・ラベル・契約の説明)は :func:`T` の対訳表で差し替わる。本文の散文
    (op の docstring)は原文が日本語で、要約 1 行だけ :func:`op_summary` の表を持つ
    —— 訳が無い部分は**訳したふりをせず**、その旨を明示した 1 行を添えて原文を出す。

    ``verbatim_doc`` は「docstring を 1 文字も動かさずに写すか」。既定は ``lang == "ja"``
    ―― ``docs/ops/**`` のノートは docstring の**単一真実源としての写し**なので、
    段落を詰め直すことも要約を差し替えることもしない(drift テストが写しを固定する)。
    ``ja`` のヘルプ頁だけは ``False`` で呼び、原文が英語の 349 本に日本語の要約を出す。
    """
    dim, name, cat = rec["dim"], rec["name"], rec["category"]
    ins, out = rec["in"], rec["out"]
    if verbatim_doc is None:
        verbatim_doc = (lang == "ja")
    lines = []
    # frontmatter: machine-readable, stable field order
    fm = [
        f"op: {name}", f"dim: {dim}", f"category: {cat}",
        f"in: {ins}", f"out: {out}",
    ]
    if rec["halcon"]:
        fm.append(f"halcon: {rec['halcon']}")
    if rec.get("gpu"):
        fm.append("gpu: true")
    fm.append("examples: [" + ", ".join(rec["examples"]) + "]")
    fm.append(f"author: {_AUTHOR}")
    fm.append(f"license: {_LICENSE}")
    fm.append(f"version: {_VERSION}  # fullseye lib version this note was generated for")
    lines.append("---")
    lines.extend(fm)
    lines.append("---")
    lines.append("")
    lines.append(f"# {name} — {dim.upper()} `{cat}` op")
    lines.append("")
    # 入力ソートが空の op が 82 個ある —— **引数だけで動く** op(`thin_lens(focal_mm=…)`
    # のように画像やデータを取らない)。空のまま流すと `` → `table` という中身の無い
    # コードスパンになり、「型が抜けている」のか「入力が無い」のかが読み手に区別
    # できない(2026-09-05 に 5 言語へ複製する直前に発見)。名指しで書く。
    if str(ins).strip():
        lines.append(T('- **データ種**: `{a0}` → `{a1}`', lang).format(a0=ins, a1=out))
    else:
        lines.append(T('- **データ種**: `{a0}` → `{a1}`(引数だけで決まる op —— '
                       '画像やデータの入力を取らない)', lang)
                     .format(a0=T("なし", lang), a1=out))
    if dim == "2d":
        lines.append(T('- **呼び出し**: `fullseye.apply(img, "{a0}", a=0.5, b=0.5)` (2-D は 1 画像 + 2 スカラつまみ `a,b∈[0,1]` のモデル)', lang).format(a0=name))
    else:
        reg_mod = ({"3d": "ops3d"}.get(dim)
                   or (LEDGER_DIMS[dim]["registry"] if dim in LEDGER_DIMS
                       else rec["module"]))
        lines.append(T('- **呼び出し**: `import {a0}; {a1}.{a2}{a3}` (または `{a4}.get("{a5}")`)', lang).format(a0=rec['module'], a1=rec['module'], a2=name, a3=rec['sig'], a4=reg_mod, a5=name))
    if rec["halcon"]:
        lines.append(T('- **HALCON 相当**: `{a0}`(意味・パラメータは HALCON リファレンスが参考になる)', lang).format(a0=rec['halcon']))
    if rec.get("gpu"):
        lines.append(T("- **GPU**: この op は GPU 経路あり(`device=\"cuda\"`)", lang))
    if rec.get("override"):
        lines.append(T('- **上書き登録**: この名前は 2 回登録されている(core 実装 + backend の安全ラッパ)。`apply` が実行するのは**後勝ちの安全版**(fail-closed ラッパ)。core 版は backend 不在時のフォールバックとして残る(登録順=Wave0 stable slot は不変、`tests/test_opdocs.py` が上書き集合を pin)。', lang))
    lines.append("")
    # usage / behaviour — honest: docstring if present, else typed contract only
    lines.append(T("## 使い方", lang))
    lines.append("")
    if rec["doc"]:
        # 散文は原文が日本語。要約 1 行だけ対訳表を持ち、残りは**訳したふりをせず**
        # 原文を出したうえで「ここは原文だ」と明示する(黙って日本語が出てくると、
        # 訳が抜けているのか原文がそうなのかを読者が区別できない)。
        _src_summary, rest = summary_and_rest(rec["doc"])
        summ, translated = op_summary(rec, lang)
        if verbatim_doc:
            lines.append(rec["doc"])
        # 断り書きを出すかは「読み手の言語で書かれているか」で決める —— 表を引けたかでは
        # ない。原文が英語の op を英語の読者に出すとき「未訳です」と断るのは嘘になる。
        elif translated:
            lines.append(summ)
            if rest:
                lines.append("")
                if not_in_language(rest, lang):
                    lines.append(T("> 以下の詳細説明は原文のままです —— 要約と見出しは訳出済み。", lang))
                    lines.append("")
                lines.append(rest)
        else:
            lines.append(T("> この op の説明はまだ訳がありません。原文をそのまま載せます。", lang))
            lines.append("")
            lines.append(rec["doc"])
    else:
        lines.append(T('型契約は `{a0} → {a1}`。挙動の言語説明は下記のファミリ使い方ガイドと実行可能サンプルを参照(ここでは推測を書かない)。', lang).format(a0=ins, a1=out))
    lines.append("")
    if dim == "optics":
        # family-wide fail-closed input contract for the optics ledger (grounded in
        # optics._finite_scalar / _require_image / _require_vec / the size caps —
        # every item below is a bug the 2026-09-01 adversarial pass actually found,
        # or a trap it was written to close).
        lines.append(T("## ファミリ共通の入力契約(fail-closed)", lang))
        lines.append("")
        lines.append(T("optics の全 op は入力を検証してから計算する(黙って通さない):", lang))
        lines.append("")
        lines.append(T("- **単位は引数名に埋め込む** — `_mm` / `_um` / `_deg` / `_mrad`。"
                     "mm と µm の取り違えは crash ではなく「もっともらしく間違った答え」"
                     "なので、名前で防ぐ。大きさから単位を推測する処理は一切しない。", lang))
        lines.append(T("- **文字列は `ValueError`** — `float('50')` は成功してしまうため、"
                     "未パースの設定値が長さとして通り抜ける(実測: `thin_lens('50', '200')` が"
                     "もっともらしい 66.667 mm を返していた)。bool も `True == 1` の"
                     "暗黙昇格として拒否。", lang))
        lines.append(T("- **complex / masked array は `ValueError`**(実数枠のみ。虚部の"
                     "無言切り捨て・マスク剥がしを拒否)。**NaN/Inf は全入力で `ValueError`**。", lang))
        lines.append(T("- **0 除算とその親戚を名指しで拒否**: 焦点距離 0・曲率半径 0・"
                     "屈折率 <= 0・不透明な開口(全 0 なので正規化が 0/0)・総和 <= 0 の PSF・"
                     "S0 = 0 の Stokes ベクトル・物体が前側焦点にある(像が無限遠)。", lang))
        lines.append(T("- **非有限を返すのは 2 op だけ、しかも契約として明記**: "
                     "`depth_of_field` の過焦点距離以遠の `far_mm = inf`(それが過焦点距離の"
                     "定義)と `gaussian_beam` のウエストでの `wavefront_radius_mm = inf`"
                     "(平面波面の曲率半径)。どちらも有限の相棒(`far_is_infinite` / "
                     "`curvature_per_mm`)を併せて返す。**それ以外の無言 NaN/Inf は内部で"
                     "検出して `ValueError`** —「float64 が溢れた」と「答えが無限大」は"
                     "別の主張なので、後者の顔で前者を返さない。", lang))
        lines.append(T("- **サイズ上限**: 生成格子は `optics.MAX_GRID`(4096)、供給された"
                     "場/PSF/開口は `optics.MAX_FIELD_ELEMENTS`(2^24)、ABCD 素子列は "
                     "`optics.MAX_SYSTEM_ELEMENTS`(1024)、Zernike は "
                     "`MAX_ZERNIKE_TERMS`(512)/ `MAX_ZERNIKE_ORDER`(40)/ "
                     "`MAX_ZERNIKE_BASIS`(2^25)。小さな引数から巨大な内部確保が起きる経路"
                     "(実測: n_max=40 × 4096² で 108 GB)を fail-closed で塞ぐ。", lang))
        lines.append(T("- **物理的に不可能な状態も拒否**: 偏光度 > 1 の Stokes ベクトル、"
                     "負の透過率、負の強度、n-|m| が奇数などの不正な Zernike 添字。", lang))
        lines.append("")
    if dim == "math":
        # family-wide fail-closed input contract, stated once per note (grounded in
        # mathops._as_float64 / _require_* / _check_elements — the 2026-08 adversarial
        # audits' confirmed bug families, refused explicitly instead of silently).
        lines.append(T("## ファミリ共通の入力契約(fail-closed)", lang))
        lines.append("")
        lines.append(T("mathops の全 op は入力を検証してから計算する(黙って通さない):", lang))
        lines.append("")
        lines.append(T("- **complex 入力は `ValueError`** — float64 への強制変換は虚部を黙って捨てる"
                     "(numpy は ComplexWarning だけ出して「もっともらしく間違った」実数を返す)。"
                     "`.real`/`.imag`/`abs()` を明示するか、複素対応の complexops を使う。", lang))
        lines.append(T("- **masked array(masked 要素あり)は `ValueError`** — マスクを剥がして"
                     "下の生値を使う暗黙変換を拒否。埋める/落とすを明示する。", lang))
        lines.append(T("- **NaN/Inf は全入力で `ValueError`**(件数を明示して拒否 — 結果全体に伝播するため)。", lang))
        lines.append(T("- **形状は厳格**: 1-D と 2-D を暗黙昇格・ブロードキャストしない"
                     "(vector 枠に matrix、matrix 枠に vector は `ValueError`。reshape を明示する)。", lang))
        lines.append(T("- **サイズ上限**: 行列を取る op と `stat_histogram` の bins は "
                     "`mathops.MAX_ELEMENTS`(2^26 ≈ 6700 万要素)超で `ValueError`。", lang))
        lines.append("")
    # family guide —— **実在するときだけリンクする**。
    #
    # 以前は無条件に出していた。族が 10 増えた時点(2026-09-02)で、ガイドを
    # 書いていない族のノート 196 枚が**存在しないファイルへのリンク**を持つ
    # ことになると分かったので、条件つきにした。リンク切れは「あるはずの物が
    # 見つからない」で、無い節より悪い。書かれていない族は
    # :func:`families_without_a_guide` が数えて生成時に報告する(黙って
    # 消えないように)。
    if rec.get("family"):
        gp = os.path.join(DOCS, dim if dim in LEDGER_DIMS else "2d",
                          "guides", rec["family"] + ".md")
        if os.path.exists(gp):
            lines.append(T("## 詳しい使い方ガイド", lang))
            lines.append("")
            lines.append(T('- [{a0} ファミリ ガイド]({a1})', lang).format(a0=rec['family'], a1=_rel(path, gp)))
            lines.append("")
    # 背景知識ガイド(族に属さない横断的な教材)。frontmatter の ``applies_to`` が
    # この op の dim / dim+category を挙げているものだけを張る。配線し忘れは
    # :func:`guides_not_wired` が数えて生成時に報告する。
    kg = guides_for(dim, rec["category"])
    if kg:
        lines.append(T("## 背景知識ガイド(この op の手前にある物理・規約)", lang))
        lines.append("")
        for g in kg:
            lines.append(f"- [{g['stem']}]({_rel(path, g['path'])}) — {g['title']}")
        lines.append("")
    # sample data + references (honest pointers to the curated catalogs)
    sp = os.path.join(DOCS, "SAMPLES.md")
    rp = os.path.join(_ROOT, "docs", "REFERENCES.md")
    lines.append(T("## 参考(サンプルデータ・文献)", lang))
    lines.append("")
    lines.append(T('- [サンプルデータ カタログ(DL URL / ライセンス)]({a0}) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。', lang).format(a0=_rel(path, sp)))
    lines.append(T('- [演算子の来歴・参考文献]({a0}) — この op 族の元になった研究/手法の出典。', lang).format(a0=_rel(path, rp)))
    if rec.get("family"):
        lines.append(T("- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。", lang))
    lines.append("")
    # worked examples
    lines.append(T("## 実行できる例(この op を実際に呼ぶ検証済みサンプル)", lang))
    lines.append("")
    if rec["examples"]:
        exdir = "examples_3d" if dim == "3d" else "examples"
        for e in rec["examples"]:
            ep = os.path.join(_ROOT, exdir, e + ".py")
            lines.append(f"- [{e}]({_rel(path, ep)}) — `py -3.11 {exdir}/{e}.py`")
    else:
        lines.append(T("- (まだありません)", lang))
    lines.append("")
    # related ops: type-compatible successors + same-category siblings
    succ, sib = [], []
    for r2 in by_name.values():
        if r2["dim"] != dim or r2["name"] == name:
            continue
        if r2["category"] == cat and len(sib) < 8:
            sib.append(r2)
        r2in = r2["in"]
        if (out in (r2in.split(" × ") if isinstance(r2in, str) else [r2in])
                or r2in == "any" or out == "any") and len(succ) < 8:
            succ.append(r2)

    def _links(rs):
        return " · ".join(f"[{r['name']}]({_rel(path, _op_path(r))})" for r in rs) or "—"

    lines.append(T('## 型が繋がる次の op(`{a0}` を入力に取れる)', lang).format(a0=out))
    lines.append("")
    lines.append(_links(succ))
    lines.append("")
    lines.append(T('## 同カテゴリ(`{a0}`)', lang).format(a0=cat))
    lines.append("")
    lines.append(_links(sib))
    lines.append("")
    lines.append(f"---")
    lines.append(T('*Provenance: {a0}.py — {a1} operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*', lang).format(a0=rec['module'], a1=dim.upper()))
    lines.append("")
    lines.append(_COPYRIGHT)
    lines.append("")
    return "\n".join(lines)


def _op_path(rec) -> str:
    return os.path.join(DOCS, rec["dim"], _catslug(rec["category"]), rec["name"] + ".md")


def cmd_md():
    recs, idx2d, op_fam, fam_ops = _records()
    by_name = {(r["dim"], r["name"]): r for r in recs}
    n = 0
    for rec in recs:
        p = _op_path(rec)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(_op_md(rec, p, by_name))
        n += 1
    # ensure guides dirs exist (authored separately)
    os.makedirs(os.path.join(DOCS, "2d", "guides"), exist_ok=True)
    for _d in LEDGER_DIMS:
        os.makedirs(os.path.join(DOCS, _d, "guides"), exist_ok=True)
    print(f"opdocs md: wrote {n} per-op notes under {DOCS}")
    unwired = guides_not_wired()
    if unwired:
        print("  (背景知識ガイドに applies_to が無く、どの op からも辿れない: "
              + ", ".join(unwired) + ")", file=sys.stderr)
    bad = guides_with_unknown_targets()
    for stem, miss in bad.items():
        print(f"  (背景知識ガイド {stem} の applies_to が実在しない対象を指している: "
              + ", ".join(miss) + ")", file=sys.stderr)
    return recs


# ------------------------------------------------------------------ #
# sample-data catalog  (real download URLs / licences)
# ------------------------------------------------------------------ #

def cmd_samples():
    out = ["# Fullseye サンプルデータ カタログ", "",
           "op の動作確認・デバッグに使える**実在**のサンプルデータ源(DL URL / ライセンス / 取得法)。"
           "同梱はせず**ユーザー DL 方式**(`fullseye` の `sample_data` / `sample_images`)。fail-closed"
           "(未取得なら明示エラー、捏造しない)。", ""]
    # 3-D / volume: real download URLs from sample_data.MANIFEST
    try:
        import sample_data as sd
        out.append("## 3-D / ボリューム(実 DL URL)")
        out.append("")
        out.append("| id | 種別 | アクセス | 出典 / DL URL |")
        out.append("|----|------|----------|----------------|")
        for e in sd.catalog():
            url = e.get("url") or e.get("source_page") or ""
            out.append(f"| `{e.get('id','')}` | {e.get('category','')} | {e.get('access','')} "
                       f"| <{url}> |")
        out.append("")
        out.append("取得: `py -3.11 -c \"import sample_data; sample_data.download('bunny', yes=True)\"` "
                   "(`access=direct` のみ自動 DL、`gated`/`info` は出典ページから手動)。", )
        out.append("")
    except Exception as e:
        out.append(f"(sample_data 利用不可: {e})\n")
    # 2-D images: skimage.data (BSD/public) + synthetic own-work
    try:
        import sample_images as si
        entries = si.entries() if hasattr(si, "entries") else [{"name": n} for n in si.names()]
        out.append("## 2-D 画像(skimage.data(BSD/public)+ 合成)")
        out.append("")
        out.append("| name | 出典 | ライセンス |")
        out.append("|------|------|-----------|")
        for e in entries:
            out.append(f"| `{e.get('name','')}` | {e.get('source','')} | {e.get('licence', e.get('license',''))} |")
        out.append("")
        out.append("2-D は外部 DL 不要(`skimage.data` は pip 導入済、合成は自作)。"
                   "`import sample_images; sample_images.load('<name>')` で取得。", )
        out.append("")
    except Exception as e:
        out.append(f"(sample_images 利用不可: {e})\n")
    out.append("---")
    out.append(_COPYRIGHT)
    out.append("")
    os.makedirs(DOCS, exist_ok=True)
    with open(os.path.join(DOCS, "SAMPLES.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    print(f"opdocs samples: wrote {os.path.join(DOCS, 'SAMPLES.md')}")


# ------------------------------------------------------------------ #
# auto TOC  (walks the folder hierarchy)
# ------------------------------------------------------------------ #

def _md_title(path: str) -> str:
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                if line.startswith("# "):
                    return line[2:].strip()
    except OSError:
        pass
    return os.path.splitext(os.path.basename(path))[0]


def _walk_ops(dim: str):
    """category -> sorted [op names] for a dimension, from the folder tree."""
    base = os.path.join(DOCS, dim)
    cats = {}
    if not os.path.isdir(base):
        return cats
    for cat in sorted(os.listdir(base)):
        cdir = os.path.join(base, cat)
        if not os.path.isdir(cdir) or cat == "guides":
            continue
        ops_ = sorted(os.path.splitext(f)[0] for f in os.listdir(cdir) if f.endswith(".md"))
        if ops_:
            cats[cat] = ops_
    return cats


def cmd_toc():
    written = 0
    dims = [d for d in ("2d", "3d", *LEDGER_DIMS)
            if os.path.isdir(os.path.join(DOCS, d))]
    # per-dimension INDEX
    dim_counts = {}
    for dim in dims:
        cats = _walk_ops(dim)
        total = sum(len(v) for v in cats.values())
        dim_counts[dim] = (len(cats), total)
        out = [f"# {dim.upper()} operator help — {total} ops in {len(cats)} categories", "",
               "自動生成(`tools/opdocs.py toc`)。フォルダ階層 `docs/ops/" + dim + "/<category>/<op>.md` を走査。", ""]
        guides = sorted(glob.glob(os.path.join(DOCS, dim, "guides", "*.md")))
        kstems = {g["stem"] for g in knowledge_guides()}
        for _head, _sel in (("## ファミリ使い方ガイド(用途→op の教材)", False),
                            ("## 背景知識ガイド(op の手前にある物理・規約)", True)):
            group = [g for g in guides
                     if (os.path.splitext(os.path.basename(g))[0] in kstems) is _sel]
            if not group:
                continue
            out.append(_head)
            out.append("")
            for g in group:
                stem = os.path.splitext(os.path.basename(g))[0]
                out.append(f"- [{stem}](guides/{stem}.md) — {_md_title(g)}")
            out.append("")
        out.append("## カテゴリ")
        out.append("")
        for cat in sorted(cats):
            out.append(f"### {cat} ({len(cats[cat])})")
            out.append("")
            out.append(" · ".join(f"[{op}]({cat}/{op}.md)" for op in cats[cat]))
            out.append("")
        out.append("---")
        out.append(_COPYRIGHT)
        out.append("")
        with open(os.path.join(DOCS, dim, "INDEX.md"), "w", encoding="utf-8") as f:
            f.write("\n".join(out))
        written += 1
    # top INDEX
    try:
        recs, *_ = _records()
        fp = _registry_fingerprint(recs)
    except Exception:
        fp = "?"
    top = [f"<!-- fullseye {_VERSION} · op-registry fingerprint {fp} · generated by tools/opdocs.py -->",
           "<!-- md(このコーパス)と code(op レジストリ)の版接続: この fingerprint が live レジストリと -->",
           "<!-- 一致することを CI drift テストが強制する(再生成==commit 済み)。手編集しないこと。 -->",
           "# Fullseye Operator Docs — AI 使い方コーパス", "",
           f"**fullseye {_VERSION}** の op ドキュメント。op ごとの使い方を Markdown で1件1ファイル"
           "(RAD コーパス形状)に持ち、Studio の HTML ヘルプはここから一括変換で生成する"
           "(`tools/opdocs.py html`)。この目次はフォルダ階層から自動生成。", ""]
    for dim in dims:
        nc, nt = dim_counts[dim]
        top.append(f"- [{dim.upper()} operators](./{dim}/INDEX.md) — {nt} ops / {nc} categories")
    top.append("- [サンプルデータ カタログ(DL URL / ライセンス)](./SAMPLES.md)")
    top.append("- [演算子の来歴・参考文献](../REFERENCES.md)")
    top.append("")
    top.append("## 使い方(assistant 向け)")
    top.append("")
    top.append("1. 用途(入力データ種・欲しい出力)から近い**ファミリ使い方ガイド**(`2d/guides/`)を読む。")
    top.append("2. 各 op ノートの**データ種 `in → out`** が繋がるように連鎖を組む。")
    top.append("3. 挙動が不確かなら、そのノートの**実行できる例**を走らせて GT 出力で確かめる。")
    top.append("")
    top.append("---")
    top.append(_COPYRIGHT)
    top.append("")
    with open(os.path.join(DOCS, "INDEX.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(top))
    written += 1
    print(f"opdocs toc: wrote {written} INDEX.md ({', '.join(f'{d}:{dim_counts[d][1]}ops' for d in dims)}) "
          f"fp={fp}")


# ------------------------------------------------------------------ #
# bulk Markdown -> Studio HTML  (derived; never authored twice)
# ------------------------------------------------------------------ #

_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_ICODE = re.compile(r"`([^`]+)`")
_BOLD = re.compile(r"\*\*([^*]+)\*\*")


def _rewrite_link(text: str, target: str) -> str:
    """Map a Markdown link target to a Studio QTextBrowser scheme.

    Corpus-navigation docs (SAMPLES/REFERENCES/INDEX) have no Studio handler and would
    mis-route to a bogus op card, so they render as plain text (their working relative
    links live on in the Markdown corpus for GitHub/Obsidian/RAD)."""
    t = target
    stem = os.path.splitext(os.path.basename(t))[0]
    if t.endswith(".md") and stem in ("SAMPLES", "REFERENCES", "INDEX"):
        return _html.escape(text)
    if t.endswith(".py") and "examples_3d/" in t:
        href = "example3d:" + stem
    elif t.endswith(".py") and "examples/" in t:
        href = "example2d:" + stem
    elif t.endswith(".md") and "/guides/" in t:
        href = "guide2d:" + stem
    elif t.endswith(".md"):                     # sibling op note
        href = "op:" + stem
    else:
        href = t
    return f'<a style="color:{_CODE}" href="{_html.escape(href, quote=True)}">{_html.escape(text)}</a>'


def _inline(s: str) -> str:
    # protect code spans, then escape, then re-insert styled code + bold + links
    parts = []
    idx = 0
    for m in _ICODE.finditer(s):
        parts.append(("t", s[idx:m.start()]))
        parts.append(("c", m.group(1)))
        idx = m.end()
    parts.append(("t", s[idx:]))
    out = []
    for kind, txt in parts:
        if kind == "c":
            out.append(f'<code style="color:{_CODE}">{_html.escape(txt)}</code>')
            continue
        # links first (escape handled inside), then bold, then escape remaining text
        pos = 0
        buf = []
        for m in _LINK.finditer(txt):
            buf.append(_bold_escape(txt[pos:m.start()]))
            buf.append(_rewrite_link(m.group(1), m.group(2)))
            pos = m.end()
        buf.append(_bold_escape(txt[pos:]))
        out.append("".join(buf))
    return "".join(out)


def _bold_escape(s: str) -> str:
    pos = 0
    buf = []
    for m in _BOLD.finditer(s):
        buf.append(_html.escape(s[pos:m.start()]))
        buf.append(f"<b>{_html.escape(m.group(1))}</b>")
        pos = m.end()
    buf.append(_html.escape(s[pos:]))
    return "".join(buf)


def md_to_html(md: str) -> str:
    """Convert the controlled Markdown subset we emit into Studio's inline-styled HTML."""
    lines = md.split("\n")
    # strip frontmatter -> render as a muted meta line
    meta = {}
    if lines and lines[0].strip() == "---":
        j = 1
        while j < len(lines) and lines[j].strip() != "---":
            if ":" in lines[j]:
                k, v = lines[j].split(":", 1)
                meta[k.strip()] = v.strip()
            j += 1
        lines = lines[j + 1:]
    out = []
    in_code = False
    code_lang = ""
    code_buf = []
    for line in lines:
        st = line.strip()
        if st.startswith("```"):
            if in_code:
                # mermaid / math: QTextBrowser can't render these, so we keep the source
                # in a labelled block (Markdown-native viewers — GitHub/Obsidian/RAD — do render).
                label = ""
                if code_lang in ("mermaid", "math"):
                    kind = "Mermaid 図" if code_lang == "mermaid" else "数式(LaTeX)"
                    label = (f'<p style="color:{_MUTE};font-size:11px;margin:6px 0 0 0">'
                             f'{kind}(ソース):</p>')
                out.append(label + f'<pre style="background:#12141b;border:1px solid #2c313f;'
                           f'padding:6px;color:{_CODE}">' + _html.escape("\n".join(code_buf)) + "</pre>")
                code_buf = []
                in_code = False
                code_lang = ""
            else:
                in_code = True
                code_lang = st[3:].strip().lower()
            continue
        if in_code:
            code_buf.append(line)
            continue
        if not st:
            continue
        if st == "---":
            out.append('<hr style="border:0;border-top:1px solid #2c313f">')
        elif st.startswith("#### "):
            out.append(f'<h4 style="color:{_TEAL};margin:6px 0 2px 0">{_inline(st[5:])}</h4>')
        elif st.startswith("### "):
            out.append(f'<h3 style="color:{_TEAL};margin:8px 0 2px 0">{_inline(st[4:])}</h3>')
        elif st.startswith("## "):
            out.append(f'<h3 style="color:{_TEAL};margin:10px 0 2px 0">{_inline(st[3:])}</h3>')
        elif st.startswith("# "):
            out.append(f'<h2 style="color:{_AMBER};margin:0 0 4px 0">{_inline(st[2:])}</h2>')
        elif st.startswith("- ") or st.startswith("* "):
            out.append(f'<p style="margin:2px 0 2px 12px">• {_inline(st[2:])}</p>')
        else:
            out.append(f"<p>{_inline(st)}</p>")
    if in_code and code_buf:
        out.append(f'<pre style="background:#12141b;border:1px solid #2c313f;padding:6px;color:{_CODE}">'
                   + _html.escape("\n".join(code_buf)) + "</pre>")
    return "\n".join(out) + "\n"


def _write_generated(path: str, body: str) -> bool:
    """Write a generated help page, but never clobber a hand-authored override.

    Studio's ``op_help_html`` reads ``op_help/<name>.html`` from the root, so the
    generated 2-D pages must live there too. A file counts as hand-authored (and is
    preserved) unless it carries the generated marker. This lets the 3 rich hand-written
    pages (gaussian/otsu/sobel_mag) win while every other op still gets a linked card."""
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                head = f.read(len(_GEN_MARK) + 4)
        except OSError:
            head = ""
        if _GEN_MARK not in head:
            return False  # hand-authored override — leave it
    with open(path, "w", encoding="utf-8") as f:
        f.write(_GEN_MARK + "\n" + body)
    return True


def _anchor_rewrite(html: str, dim: str) -> str:
    """生成 HTML のアンカーを次元ごとの名前空間へ。

    op 名は登録簿をまたいで衝突する(``fill_holes`` は 2-D にも 3-D にもある)ので、
    兄弟 op / 次の op / 族ガイドへのリンクは開くべき登録簿を接頭辞で持つ。
    """
    if dim == "2d":
        return html
    if dim == "3d":
        return html.replace('href="op:', 'href="op3d:')
    return (html.replace('href="op:', 'href="op%s:' % dim)
                .replace('href="guide2d:', 'href="guide%s:' % dim))


def _help_pages_for_dim(dim, recs_by_name, langs):
    """1 次元ぶんの op ヘルプを書き出す。``(written, skipped, translated)``。

    ``ja`` は**コミット済みの Markdown ノートから**変換する(ノート自体が単一真実源で、
    drift テストがノートと生成器の一致を担保しているため、ここで作り直さない)。
    それ以外の言語はノートを持たない —— レコードから ``lang`` 付きで組み立てて
    ``<op>.<lang>.html`` にだけ落とす。docs/ops を言語ぶん複製しないのは、あの木が
    RAG コーパス(読み手は LLM で、日本語で困らない)だからで、人が読むのはヘルプ側。
    """
    src = os.path.join(DOCS, dim)
    out = HELP_ROOT if dim == "2d" else os.path.join(HELP_ROOT, dim)
    if not os.path.isdir(src):
        return 0, 0, 0
    os.makedirs(out, exist_ok=True)
    n = skipped = tr = 0
    for cat in sorted(os.listdir(src)):
        cdir = os.path.join(src, cat)
        if not os.path.isdir(cdir) or cat == "guides":
            continue
        for f in sorted(os.listdir(cdir)):
            if not f.endswith(".md"):
                continue
            op = f[:-3]
            with open(os.path.join(cdir, f), encoding="utf-8") as fh:
                md = fh.read()
            if _write_generated(os.path.join(out, op + ".html"),
                                _anchor_rewrite(md_to_html(md), dim)):
                n += 1
            else:
                # 手書きの上書きページ(gaussian / otsu / sobel_mag)。**言語版も作らない** ――
                # これらは英語で書かれていて `sample:` で実行可能なパイプラインまで載せて
                # おり、生成訳を横に置くと言語を選んだ瞬間に**中身の薄いほうへ差し替わる**
                # (2026-09-05 実測: 英語を選ぶと sample リンクが消えた)。訳が本家より
                # 貧しくなるなら、訳を出さないほうが親切。
                skipped += 1
                continue
            rec = recs_by_name.get((dim, op))
            if rec is None:
                continue
            npath = os.path.join(cdir, f)
            for lang in langs:
                body = md_to_html(_op_md(rec, npath, recs_by_name, lang=lang))
                if _write_generated(os.path.join(out, "%s.%s.html" % (op, lang)),
                                    _anchor_rewrite(body, dim)):
                    tr += 1
            # **日本語も翻訳先**。原文が英語の 349 本は、日本語のヘルプを開いても
            # 英語のままだった(「原文だから ja は常に OK」と数えていたのが誤り)。
            # 訳があるものだけ ``<op>.ja.html`` を生やす —— 原文が日本語の op に
            # ノートと同じ中身の兄弟を並べても情報は増えず、枚数だけ増える。
            if _ja_help_differs(rec):
                body = md_to_html(_op_md(rec, npath, recs_by_name,
                                         lang="ja", verbatim_doc=False))
                if _write_generated(os.path.join(out, "%s.ja.html" % op),
                                    _anchor_rewrite(body, dim)):
                    tr += 1
    return n, skipped, tr


def _ja_help_differs(rec) -> bool:
    """``<op>.ja.html`` を出す価値があるか(= 原文が英語で、日本語の要約が在る)。"""
    src = summary_and_rest(rec.get("doc"))[0]
    if not src or has_japanese(src):
        return False
    return op_summary(rec, "ja")[1]


def cmd_html():
    os.makedirs(HELP_ROOT, exist_ok=True)
    recs, _idx, _of, _fo = _records()
    by_name = {(r["dim"], r["name"]): r for r in recs}
    langs = [c for c in LANGS if c != "ja"]
    n, skipped, tr = _help_pages_for_dim("2d", by_name, langs)
    n3, _s3, tr3 = _help_pages_for_dim("3d", by_name, langs)
    nm = trm = 0
    for ldim in LEDGER_DIMS:
        a, _b, c = _help_pages_for_dim(ldim, by_name, langs)
        nm += a
        trm += c
    # guides -> guide_<stem>.html (always generated from guide md; every dim's
    # guides share the flat guide_ namespace — stems are distinct by construction:
    # gallery2d_* / family names / knowledge-guide stems).
    #
    # ガイドは**人が書いた散文**なので機械的な差し替えができない。訳を持たない以上、
    # 訳したふりはせず日本語 1 枚だけを出し、その事実を冒頭に多言語で 1 行書く
    # (英語表示のユーザーが日本語のページに落ちた理由が分かるように)。
    #
    # ``3d`` がこのループから抜けていたため、``docs/ops/3d/guides/`` のガイドは
    # Studio ヘルプに 1 枚も出ていなかった(2026-09-05 に depth_sensors を書いて発覚)。
    g = 0
    for gdim in ("2d", "3d", *LEDGER_DIMS):
        gdir = os.path.join(DOCS, gdim, "guides")
        if not os.path.isdir(gdir):
            continue
        for f in sorted(os.listdir(gdir)):
            if not f.endswith(".md"):
                continue
            with open(os.path.join(gdir, f), encoding="utf-8") as fh:
                md = fh.read()
            body = md_to_html(md)
            _write_generated(os.path.join(HELP_ROOT, "guide_" + f[:-3] + ".html"), body)
            g += 1
            for lang in langs:
                banner = ('<p style="color:%s;font-size:11px;margin:0 0 8px 0">%s</p>\n'
                          % (_AMBER, _html.escape(
                              T("このガイドは日本語のみです(人が書いた散文なので機械的な差し替えをしていません)。", lang))))
                _write_generated(
                    os.path.join(HELP_ROOT, "guide_%s.%s.html" % (f[:-3], lang)),
                    banner + body)
    print(f"opdocs html: wrote {n} 2-D op pages ({skipped} hand-authored preserved) "
          f"+ {n3} 3-D op pages + {nm} ledger op pages ({'/'.join(LEDGER_DIMS)}) "
          f"+ {g} guides to {HELP_ROOT}")
    # 日本語も翻訳先(原文が英語の 349 本)。数だけ出して「5 言語」と書くと、
    # ja 版が出ていることが報告から消える。
    ja_pages = sum(1 for r in recs if _ja_help_differs(r))
    print(f"  translated op pages: {tr + tr3 + trm} "
          f"({len(langs) + 1} languages: ja, {', '.join(langs)}"
          f" — ja は原文が英語の {ja_pages} 本にだけ出る)")
    missing = untranslated_strings()
    for lang, miss in sorted(missing.items()):
        print(f"  ({lang}: 枠の対訳が {len(miss)} 件未訳 — 原文のまま出ます)", file=sys.stderr)


def untranslated_strings():
    """枠の対訳表に**穴**がある言語と、その原文。生成のたびに報告する。

    :data:`SEEN_STRINGS` は生成中に :func:`T` が実際に引いた原文なので、「表には
    あるが誰も引かない古い行」と「引かれたのに訳が無い行」を区別できる。
    """
    tbl = _i18n()
    out = {}
    for lang in LANGS:
        if lang == "ja":
            continue
        miss = sorted(s for s in SEEN_STRINGS if not (tbl.get(s) or {}).get(lang))
        if miss:
            out[lang] = miss
    return out


def main(argv):
    cmd = argv[1] if len(argv) > 1 else "all"
    if cmd in ("md", "all"):
        cmd_md()
    if cmd in ("samples", "all"):
        cmd_samples()
    if cmd in ("toc", "all"):
        cmd_toc()
    if cmd in ("html", "all"):
        cmd_html()
    if cmd not in ("md", "samples", "toc", "html", "all"):
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
