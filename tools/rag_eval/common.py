"""RAG 評価の共通部品 —— op の実在確認・語彙・回答からの抽出。

`tools/rag_eval/` は「同じ質問集を複数の AI に投げ、機械的に採点する」道具。
この module はその**一次情報**を一か所に集める:

* :func:`op_universe` —— fullseye に**実在する op 名**の全集合(4 層)。
  ``fs.find_op`` は 2-D レジストリ(+HALCON 別名)しか見ないので、それだけで
  「無い」と言うと台帳(``fs.ledger``、1,000 本超)の op を見落とす
  (memory ``feedback_search_all_tiers_before_declaring_a_gap`` の型)。
  ここでは 2-D レジストリ → 台帳 → n 項 op(``imgops_nary``)→ docs/ops ノート
  (CI の drift 門でレジストリと一致が強制されている)の順に全部引く。
* :func:`vocabulary` —— op ではないが文書に出てくる識別子(型名・引数名・
  返り値の鍵)。回答に出た snake_case が **op でも語彙でもない**ときだけ
  「実在しない op を作った」候補として減点する。
* :func:`extract_identifiers` / :func:`extract_paths` —— 回答 Markdown から
  バッククォート内の識別子と、根拠として挙げたリポジトリ相対パスを抜く。

LLM は使わない。全部 regex と集合演算で、同じ入力なら同じ答えが出る。
"""
from __future__ import annotations

import functools
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DOCS_OPS = REPO / "docs" / "ops"
QUESTIONS_PATH = Path(__file__).resolve().parent / "questions.json"

if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

#: 回答に出ても「op を作った」とは数えない識別子(fullseye の呼び方・型語彙・
#: Python の一般語)。docs から機械抽出する語彙(:func:`vocabulary`)の補い。
STATIC_ALLOWLIST = frozenset({
    "fullseye", "fs", "ledger", "apply", "raw", "run", "import", "numpy", "np",
    "scipy", "skimage", "cv2", "torch", "kornia", "opsspecular", "opsmeasure1d",
    "specularity", "measuring1d", "metrology", "ops", "ops3d", "opassist",
    "op_find", "find_op", "op_path", "op_run", "op_assist", "list_ops", "op_names",
    "docs", "examples", "examples_3d", "skills", "tools", "tests",
    "fullseye_rag", "setup_claude_rag", "update_fullseye", "regen_all",
    "FULLSEYE_REPO", "FULLSEYE_MCP_ROOT", "OP_CATALOG", "OP_INDEX", "OP_NOTES",
    "AI_RAG_GUIDE", "INDEX", "README", "CatalogError",
    # MCP tool 名(docs/MCP.md の表)
    "fullseye_search_ops", "fullseye_op_help", "fullseye_catalog_coverage",
    "fullseye_list_samples", "fullseye_load_image", "fullseye_apply",
    "fullseye_pipeline", "fullseye_inspect", "note_body_unavailable",
    "index_source", "notes_source", "by_sources", "resource_link",
    "params", "notes", "info", "error", "table", "dict", "list", "tuple",
    "None", "True", "False", "inf", "nan", "int32", "float64", "bool",
    "a", "b", "n", "sigma", "threshold", "x", "y", "z", "r", "t", "k",
    "in", "out", "sort", "sorts", "op", "ops", "px", "mm", "deg", "rad",
    "mm_per_px", "px_to_mm", "pixel_size", "scale", "spacing",
})

_SNAKE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
_BACKTICK = re.compile(r"`([^`\n]{1,120})`")
#: `fs.ledger.foo(` / `fullseye.apply(img, "foo"` / `opsxxx.get("foo")` の形も op 名。
_CALL_FORMS = [
    re.compile(r"\bledger\.([A-Za-z_][A-Za-z0-9_]*)"),
    re.compile(r"apply\(\s*[^,()]*,\s*[\"']([A-Za-z_][A-Za-z0-9_]*)[\"']"),
    re.compile(r"\.get\(\s*[\"']([A-Za-z_][A-Za-z0-9_]*)[\"']\s*\)"),
]
_PATH = re.compile(
    r"(?<![A-Za-z0-9_./\\])"
    r"((?:docs|examples|examples_3d|skills|tools|tests|fullseye)[\\/][\w.\-\\/ ]*?"
    r"\.(?:md|py|json|txt|html))"
)


# --------------------------------------------------------------------------- #
# op の実在(4 層)                                                              #
# --------------------------------------------------------------------------- #
def _iter_notes():
    """docs/ops の per-op ノート(INDEX・guides・翻訳版を除く)を yield。"""
    for p in sorted(DOCS_OPS.rglob("*.md")):
        if p.name.startswith("INDEX") or "guides" in p.parts:
            continue
        if re.search(r"\.(en|zh|ko|tw|de)\.md$", p.name):
            continue
        yield p


@functools.lru_cache(maxsize=None)
def note_index() -> dict[str, str]:
    """op 名 → ノートのリポジトリ相対パス(posix)。front-matter の ``op:`` から。"""
    out: dict[str, str] = {}
    for p in _iter_notes():
        head = p.read_text(encoding="utf-8", errors="replace")[:600]
        m = re.search(r"^op:\s*(\S+)", head, re.M)
        if m:
            out[m.group(1)] = p.relative_to(REPO).as_posix()
    return out


@functools.lru_cache(maxsize=None)
def op_universe() -> dict[str, str]:
    """実在する op 名 → 見つかった層(``2d`` / ``ledger`` / ``algo`` / ``note``)。

    先に見つかった層が勝つ。``note`` 層は「レジストリからは引けないが drift 門で
    実在が保証されたノートがある」名前(2026-09-15 時点で n 項 op 17 本:
    ``add_image`` / ``bit_and`` / ``reduce_domain`` など ``imgops_nary`` の op)。
    """
    import fullseye as fs

    uni: dict[str, str] = {}
    for name in fs.op_names():
        uni.setdefault(name, "2d")
    for name in dir(fs.ledger):
        if not name.startswith("_"):
            uni.setdefault(name, "ledger")
    # n 項 op(imgops_nary: add_image / bit_and / reduce_domain …)は公開レジストリから
    # 名前で引けないので、下の ``note`` 層(drift 門つきのノート)で拾う。
    try:
        for rec in fs.algo_ops():
            nm = rec.get("name") if isinstance(rec, dict) else getattr(rec, "name", None)
            if nm:
                uni.setdefault(str(nm), "algo")
    except Exception:
        pass
    for name in note_index():
        uni.setdefault(name, "note")
    return uni


def resolve_op(name: str) -> str | None:
    """``name`` が実在する op ならその**正規名**を返す。無ければ ``None``。

    順序: ``fs.find_op``(2-D 完全一致 → HALCON 別名)→ 台帳 → n 項 → algo → ノート。
    HALCON 別名(例 ``fit_circle_contour_xld`` → ``hx_fit_circle_contour``)は
    正規名に畳む —— 回答が別名で書いても「実在」と数えるが、採点表には正規名が出る。
    """
    import fullseye as fs

    uni = op_universe()
    if name in uni:
        return name
    op = fs.find_op(name)
    if op is not None:
        return op.name
    return None


def op_exists(name: str) -> bool:
    return resolve_op(name) is not None


# --------------------------------------------------------------------------- #
# 語彙(op ではない識別子)                                                       #
# --------------------------------------------------------------------------- #
@functools.lru_cache(maxsize=None)
def vocabulary() -> frozenset[str]:
    """文書に出てくる op 以外の識別子: 型名(``in:``/``out:``)、呼び出し行の
    引数名、ノート本文でバッククォートされた snake_case。

    これに入っている名前は回答に出ても減点しない(「op を作った」のではなく
    「引数や返り値の鍵を書いた」だけ)。ただし op でも無いので op 網羅にも
    数えない —— 採点表では ``documented_non_ops`` として別枠で見せる。
    """
    vocab: set[str] = set(STATIC_ALLOWLIST)
    for p in _iter_notes():
        text = p.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r"^(?:in|out):\s*(.+)$", text, re.M):
            for tok in re.split(r"[×x,\s]+", m.group(1)):
                if _SNAKE.match(tok):
                    vocab.add(tok)
        for m in re.finditer(r"\*\*呼び出し\*\*.*$", text, re.M):
            vocab.update(re.findall(r"([A-Za-z_][A-Za-z0-9_]*)\s*=", m.group(0)))
        body = text.split("## 使い方", 1)[1] if "## 使い方" in text else ""
        for m in re.finditer(r"``?([A-Za-z_][A-Za-z0-9_]*)``?", body):
            tok = m.group(1)
            if "_" in tok:
                vocab.add(tok)
    return frozenset(vocab)


# --------------------------------------------------------------------------- #
# 回答からの抽出                                                                #
# --------------------------------------------------------------------------- #
def extract_identifiers(text: str) -> list[str]:
    """バッククォート内の識別子(+ 呼び出し形の op 名)を出現順・重複なしで返す。

    ``fs.ledger.polarization_separate(...)`` のような span は最後の要素
    (``polarization_separate``)と ``ledger`` 形の両方から拾う。``params["radius"]``
    や ``n=40`` のような式は識別子ではないので落とす。
    """
    seen: list[str] = []

    def _add(tok: str) -> None:
        if tok and _SNAKE.match(tok) and tok not in seen:
            seen.append(tok)

    for m in _BACKTICK.finditer(text):
        span = m.group(1).strip()
        for rx in _CALL_FORMS:
            for mm in rx.finditer(span):
                _add(mm.group(1))
        # `a.b.c` → c、`foo(` → foo、`foo=1` → foo
        core = re.split(r"[\s(=\[]", span, 1)[0]
        core = core.split(".")[-1]
        _add(core)
    for rx in _CALL_FORMS:
        for mm in rx.finditer(text):
            _add(mm.group(1))
    return seen


def extract_paths(text: str) -> list[str]:
    """根拠として挙げたリポジトリ相対パス(posix 正規化、出現順・重複なし)。"""
    out: list[str] = []
    for m in _PATH.finditer(text):
        p = m.group(1).replace("\\", "/").strip()
        p = re.sub(r"\s+", "", p)
        if p not in out:
            out.append(p)
    return out


def path_exists(rel: str) -> bool:
    return (REPO / rel).is_file()


def load_questions(path: Path | None = None) -> list[dict]:
    data = json.loads((path or QUESTIONS_PATH).read_text(encoding="utf-8"))
    return data["questions"]
