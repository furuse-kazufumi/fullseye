"""PoC の距離・高さ場を誤ってグレースケールへ戻さない静的な門。"""
import ast
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
KEYWORDS = ("深度", "高さ", "距離", "視差", "変位",
            "depth", "height", "range", "disparity", "displacement")


def _has_keyword(word):
    low = word.lower()
    return any((key in low if not key.isascii()
                else re.search(r"(?<![a-z])%s(?![a-z])" % re.escape(key), low))
               for key in KEYWORDS)


def _strings(node):
    return [n.value for n in ast.walk(node)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)]


def test_depth_like_poc_figures_never_request_gray(capsys):
    matches = []
    exemptions = []
    offenders = []
    for path in sorted((ROOT / "examples").glob("poc_*.py")):
        source = path.read_text(encoding="utf-8")
        lines = source.splitlines()
        for call in ast.walk(ast.parse(source)):
            if not (isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
                    and call.func.attr in ("save", "save_grid")):
                continue
            # Name and caption(s) are positional 0/2 or named.  Constants inside
            # f-strings and caption lists count; panel expressions do not.
            fields = list(call.args[:1])
            if len(call.args) > 2:
                fields.append(call.args[2])
            fields += [kw.value for kw in call.keywords
                       if kw.arg in ("name", "caption", "captions", "title", "kind")]
            words = _strings(ast.Tuple(elts=fields))
            if not any(_has_keyword(word) for word in words):
                continue
            label = "%s:%d" % (path.relative_to(ROOT), call.lineno)
            matches.append(label)
            gray = any(kw.arg == "gray" and isinstance(kw.value, ast.Constant)
                       and kw.value.value is True for kw in call.keywords)
            marker = lines[call.lineno - 1].partition("# gray-ok:")[2].strip()
            if marker:
                exemptions.append("%s — %s" % (label, marker))
            elif gray:
                offenders.append(label)
    print("matches:\n" + "\n".join(matches))
    print("exemptions:\n" + "\n".join(exemptions))
    assert len(matches) >= 30, "走査が空振りしている: %d 件" % len(matches)
    assert len(exemptions) <= 10, "例外が増えすぎた: %s" % exemptions
    assert not offenders, "距離・高さ場に gray=True: %s" % offenders
