"""「できること」台帳と「PoC が上げた堅牢性」台帳を、実物に照らして落とす門。

この 2 つは**説明を貯める場所**なので、放っておくと真っ先に現実から離れる ——
[[feedback_gates_go_stale_not_missing]] の型そのもの。ここで見るのは 3 つ:

1. **書いた op が実在するか**。`fs.` / `fs.op.` / `fs.ledger.` / `op_find` の
   4 層すべてを引く(1 層だけ見て「無い」と言ったことも、「在る」と言ったことも
   過去にある)。
2. **挙げた例が実際に在るか**。ファイルが消えた能力書きは、能力ではない。
3. **生成した索引がコミット済みのものと一致するか**(drift)。生成物を
   コミットしておきながら誰も突き合わせない、が起きないように。

★堅牢性台帳には 4 つめがある: **`status: fixed` なら `gate` に実在する試験関数を
書いていること**。「直した」という記録だけが残って再発を止められない状態を、
記録の側が作らないため。
"""
import io
import os
import re
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))

import gen_capabilities_index as CAP                                # noqa: E402
import gen_hardening_index as HARD                                  # noqa: E402


# --------------------------------------------------------------------------- #
# 共通ヘルパ
# --------------------------------------------------------------------------- #
def _op_exists(name: str) -> bool:
    """4 層すべてを引く。1 つでも当たれば実在。"""
    import fullseye as fs

    if hasattr(fs, name) or hasattr(fs.ledger, name) or hasattr(fs.op, name):
        return True
    try:
        return any(h["op"] == name for h in fs.op_find(name))
    except Exception:                                                # noqa: BLE001
        return False


def _example_exists(name: str) -> bool:
    """`examples/<name>.py` か `examples_3d/<name>.py`(拡張子つきの相対指定も可)。"""
    if name.endswith(".py") and os.path.isfile(os.path.join(ROOT, name)):
        return True
    return any(os.path.isfile(os.path.join(ROOT, d, name + ".py"))
               for d in ("examples", "examples_3d"))


def _test_function_names() -> set:
    names = set()
    tdir = os.path.join(ROOT, "tests")
    for fn in os.listdir(tdir):
        if not (fn.startswith("test_") and fn.endswith(".py")):
            continue
        text = io.open(os.path.join(tdir, fn), encoding="utf-8").read()
        names.update(re.findall(r"^\s*def (test_\w+)", text, re.M))
    return names


def _run(script: str) -> subprocess.CompletedProcess:
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    return subprocess.run([sys.executable, os.path.join(ROOT, "tools", script), "--check"],
                          capture_output=True, text=True, cwd=ROOT, env=env)


# --------------------------------------------------------------------------- #
# できること台帳
# --------------------------------------------------------------------------- #
def test_every_capability_names_operators_that_exist():
    """能力の裏づけに挙げた op が 4 層のどこかに実在すること。"""
    bad = []
    for cap in CAP.load_all():
        if not cap["ops"]:
            bad.append((cap["id"], "ops が空"))
        for op in cap["ops"]:
            if not _op_exists(op):
                bad.append((cap["id"], op))
    assert not bad, "実在しない op を挙げている能力: %s" % bad[:8]


def test_every_capability_points_at_something_that_runs():
    bad = []
    for cap in CAP.load_all():
        if not cap["examples"]:
            bad.append((cap["id"], "examples が空"))
        for ex in cap["examples"]:
            if not _example_exists(ex):
                bad.append((cap["id"], ex))
    assert not bad, "実在しない例を挙げている能力: %s" % bad[:8]


def test_the_capability_index_is_not_stale():
    r = _run("gen_capabilities_index.py")
    assert r.returncode == 0, (r.stdout + r.stderr)[-800:]


# --------------------------------------------------------------------------- #
# 堅牢性台帳
# --------------------------------------------------------------------------- #
def test_every_hardening_entry_was_found_by_a_real_poc():
    bad = [(h["id"], h["found_by"]) for h in HARD.load_all()
           if not _example_exists(h["found_by"])]
    assert not bad, "実在しない PoC を『見つけた』と書いている: %s" % bad


def test_every_hardening_entry_names_files_and_ops_that_exist():
    bad = []
    for h in HARD.load_all():
        for w in h["where"]:
            if not os.path.exists(os.path.join(ROOT, w)):
                bad.append((h["id"], "where", w))
        for op in h["ops"]:
            if not _op_exists(op):
                bad.append((h["id"], "ops", op))
    assert not bad, "実在しない対象を挙げている記録: %s" % bad[:8]


def test_a_fixed_finding_names_a_gate_that_actually_exists():
    """★『直した』の隣に、再発を止める試験の実名があること。

    これが無いと、台帳は武勇伝置き場になる。ここで見るのは「書いてあるか」では
    なく「**その名前の試験が本当に在るか**」。
    """
    have = _test_function_names()
    bad = []
    for h in HARD.load_all():
        if h["status"] != "fixed":
            continue
        for g in h["gate"]:
            if g not in have:
                bad.append((h["id"], g))
    assert not bad, "実在しない試験を門として挙げている: %s" % bad


def test_the_hardening_index_is_not_stale():
    r = _run("gen_hardening_index.py")
    assert r.returncode == 0, (r.stdout + r.stderr)[-800:]


# --------------------------------------------------------------------------- #
# トップページからの導線(ユーザー要望: 一覧へのリンクを「はじめの方」に置く)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("path,head_lines", [
    ("README.md", 40),
    (os.path.join("docs", "README.md"), 30),
])
def test_the_top_pages_link_to_both_ledgers_near_the_top(path, head_lines):
    """★リンクは**先頭付近**に在ること。下の方に在るのは「無い」とほぼ同じ。"""
    text = io.open(os.path.join(ROOT, path), encoding="utf-8").read()
    head = "\n".join(text.split("\n")[:head_lines])
    for target in ("CAPABILITIES", "HARDENING"):
        assert target in head, (
            "%s の先頭 %d 行に %s へのリンクが無い" % (path, head_lines, target))
