"""``backends_auto`` の形(``_sh_*``)の分岐は、どれもコンパイルされる spec から届くこと(2026-10-03)。

棚卸しで 21 の形のうち 14 に、どの spec からも届かない分岐が計 30 本あった
(``_sh_threshold`` の li / yen / triangle / isodata / mean / minimum / niblack など)。
spec の側が消えた(実在しない HALCON 名を落とした等)あとに、語彙だけが残ったもの。
届かない分岐は門が 1 度も実行しないので、壊れても誰も気づかない —— ``log_gain`` には
白飛びの修正まで入っていたが、その修正は op として一度も呼ばれていなかった。
同じ機能は ``sk_*`` / ``cv_*`` / 型つき台帳(seggraph, segcontour)に生きた op として在る。

語彙を足すときは、それを使う spec を同じ commit で足すこと。
"""
import ast
import warnings
from collections import defaultdict
from pathlib import Path

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    import backends_auto as B

_SRC = Path(B.__file__).read_text(encoding="utf-8")
_KEYS = ("method", "kind", "mode", "op", "which")


def _branch_literals():
    """形の関数ごとに ``<key> == "<文字列>"`` で分けている分岐の文字列を集める。"""
    out = {}
    for f in ast.parse(_SRC).body:
        if not (isinstance(f, ast.FunctionDef) and f.name.startswith("_sh_")):
            continue
        lits = set()
        for n in ast.walk(f):
            if (isinstance(n, ast.Compare) and isinstance(n.left, ast.Name) and n.left.id in _KEYS
                    and len(n.ops) == 1 and isinstance(n.ops[0], (ast.Eq, ast.In))):
                c = n.comparators[0]
                vals = [c] if isinstance(c, ast.Constant) else list(getattr(c, "elts", []))
                lits |= {v.value for v in vals if isinstance(v, ast.Constant) and isinstance(v.value, str)}
        out[f.name] = lits
    return out


def _reached():
    """``build`` と同じ規則(実在する HALCON 名・同名は最初の 1 本)で、届く分岐の文字列を集める。"""
    real, seen, live = B._real_ops(), set(), defaultdict(set)
    for s in B.load_specs():
        shape, name = s.get("shape", ""), s.get("halcon", "")
        if shape not in B.SHAPES or name not in real or name in seen:
            continue
        seen.add(name)
        live[B.SHAPES[shape].__name__] |= {v for v in (s.get("params") or {}).values() if isinstance(v, str)}
    return live


def test_the_scope_is_not_silently_empty():
    lits = _branch_literals()
    assert len(lits) >= 20 and sum(map(len, lits.values())) >= 100, {k: len(v) for k, v in lits.items()}
    assert len(B.load_specs()) >= 200


def test_every_shape_branch_is_reached_by_a_compiled_spec():
    live = _reached()
    dead = {f: sorted(lits - live[f]) for f, lits in _branch_literals().items() if lits - live[f]}
    assert not dead, "どの spec からも届かない分岐: %s" % dead
