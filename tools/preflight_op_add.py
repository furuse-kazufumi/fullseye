# -*- coding: utf-8 -*-
"""触った帳簿に反応する門だけを選んで回す(コミット前の 1 コマンド)。

## なぜ要るか(2026-09-23)

`tools/regen_all.py` は「生成物をどれを作り直すか」を記憶で選ぶのをやめた道具だが、
**門の側は記憶で選んだままだった**。complex 第 2 陣(8 op)を足した回、38 分の
フルスイートを 3 回まわして 1 件ずつ潰した —— 落ちたのは全部「同じ 1 つの原因
(op を足した)」が別々の門に映ったものだった:

  探針引数表に 8 op が無い / 要約の対訳が 5 言語ぶん無い / 橋の免除台帳に 1 本足りない /
  橋から外した op の**孤児ノート**が索引からのリンク切れ / 手書きのノート枚数が 1 ずれる /
  その手書きを直したら 5 言語の**翻訳の指紋**が古くなる

どれも実害がある(対訳が無ければ日本語ヘルプが英語のまま出るし、免除台帳の漏れは
「登録されているのに毎回 ValueError で死ぬ op」になる)。門は正しく働いていて、
**見つけ方が 38 分 x 3 回だったのが欠陥**だった。実測では、後半 2 回で直したのは
**6 ファイル**だけで、関係する門は **2 ファイル**しかない。

## 選び方(★ここが肝)

門の一覧を**手で書かない**。手で書いた一覧は、新しい門が増えたときに古くなる。
代わりに 2 段で絞る:

1. `tests/` を走査して「**登録面(帳簿)を名指ししているテスト**」を拾う。
   新しい門が `op_summary.json` を読み始めたら、その瞬間から自動で入る。
2. `git diff` で**今回触った帳簿**を求め、それを読んでいる門だけに絞る
   (`--all` で 1 だけにできる)。

    py -3.11 tools/preflight_op_add.py           # 触った帳簿に反応する門だけ
    py -3.11 tools/preflight_op_add.py --all     # 帳簿に触る全門(op を足した回)
    py -3.11 tools/preflight_op_add.py --list    # 何をなぜ選んだかだけ見る

`regen_all.py --check` を先に回すのは、**孤児ノートは作り直す前に消さないと索引に
残る**ため(索引はノートの実ファイルから作られる)。

★これは**フルスイートの代わりではない**。push の直前には凍結した木で 1 回
全部を通すこと —— 手元で緑でも CI(3.10/3.12・Linux・wheel の中身)で赤くなる
事故は、ここでは捕まえられない。
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: op を足す/外すと必ず動く「登録面」= 帳簿。テスト側がこの語を名指ししていたら、
#: そのテストは帳簿の増減に反応しうる門である。
#:
#: ★`__all__` と `list_ops` は**入れない**。どの族のテストにも出てくる語なので
#: 392 本中 107 本を選んでしまい、そのうえ肝心の探針の門(`test_op_probe_ledger`)は
#: その語を持たないので**取り逃す**(2026-09-23 実測)。広く取れば安全、ではない ——
#: 選ぶ語は「その帳簿を読んでいる」ことの証拠でなければならない。
SURFACES = {
    "docs/ops": "op ノートと索引(孤児ノート・リンク切れ)",
    "op_summary.json": "要約の 6 言語対訳(指紋つき)",
    "op_help": "Studio のヘルプ HTML(言語ごと)",
    "OP_INDEX.json": "機械可読索引(RAG が読む正本)",
    "OP_CATALOG": "1 枚もののカタログ",
    "AI_RAG_GUIDE": "RAG 案内の手書き件数",
    "COLLECTION_SIZES": "収蔵数の台帳",
    "OP_PROBE_ALLOWLIST": "探針の免除台帳(死んだ op の許可)",
    "op_probe": "構造入力の探針そのもの",
    "_OP_BRIDGE_SKIP": "2-D 橋の免除台帳",
    "_CATALOG": "2-D 台帳の登録",
    "OPSMATH": "math 台帳の登録",
    "capabilities": "能力ノートと区分(新カテゴリの英語名)",
    "i18n": "翻訳の指紋(原文を直したら打ち直す)",
    "regen_all": "生成物の作り直しそのものを見る門",
}

#: 変更されたファイルの**パス**からどの帳簿を触ったかを読む対応。
#: レジストリ本体(op を定義する .py)を触ったら、帳簿は全部動きうる。
PATH_TO_SURFACE = [
    ("docs/ops", ("docs/ops",)),
    ("docs/i18n", ("i18n", "op_summary.json")),
    ("studio_assets/op_help", ("op_help",)),
    ("docs/AI_RAG_GUIDE", ("AI_RAG_GUIDE", "i18n")),
    ("docs/capabilities", ("capabilities",)),
    ("docs/CAPABILITIES", ("capabilities",)),
    ("docs/OP_INDEX.json", ("OP_INDEX.json",)),
    ("docs/OP_CATALOG", ("OP_CATALOG",)),
    ("docs/OP_PROBE_ALLOWLIST", ("OP_PROBE_ALLOWLIST", "op_probe")),
    ("docs/COLLECTION_SIZES", ("COLLECTION_SIZES",)),
    ("backends_typed.py", ("_OP_BRIDGE_SKIP", "op_probe")),
    ("typed_catalog.py", ("_CATALOG", "OPSMATH")),
    ("tools/regen_all.py", ("regen_all",)),
]

#: ここを触ったら「op が増減しうる」= 帳簿は全部動く。
REGISTRY_FILES = ("ops.py", "opsmath.py", "ops3d.py", "mathops.py", "api.py",
                  "fullseye/__init__.py", "backends_", "printpath.py")


def _selected():
    """(テストファイル, 当たった登録面) を返す。"""
    tests = os.path.join(ROOT, "tests")
    out = []
    for name in sorted(os.listdir(tests)):
        if not (name.startswith("test_") and name.endswith(".py")):
            continue
        with open(os.path.join(tests, name), encoding="utf-8", errors="replace") as fh:
            src = fh.read()
        hit = sorted(k for k in SURFACES if k in src)
        if hit:
            out.append((name, hit))
    return out


def _changed_paths():
    """commit 済みでない変更 + origin との差分(どちらも push 前に効く)。"""
    paths = set()
    for cmd in (["git", "status", "--porcelain"],
                ["git", "diff", "--name-only", "origin/master...HEAD"]):
        try:
            txt = subprocess.check_output(cmd, cwd=ROOT, text=True,
                                          stderr=subprocess.DEVNULL)
        except Exception:                                  # noqa: BLE001 - git 無しでも動く
            continue
        for line in txt.splitlines():
            line = line.strip()
            if cmd[1] == "status":
                line = line[2:].strip().strip('"')
                line = line.split(" -> ")[-1]
            if line:
                paths.add(line.replace("\\", "/"))
    return paths


def _touched_surfaces(paths):
    """触ったパスから、動きうる帳簿の集合を出す。レジストリ本体なら全部。"""
    surf = set()
    for p in paths:
        if any(p.startswith(r) or p == r for r in REGISTRY_FILES):
            return set(SURFACES)                           # op が増減しうる = 全部
        for prefix, names in PATH_TO_SURFACE:
            if p.startswith(prefix):
                surf.update(names)
        if p.startswith("tests/"):
            surf.add("__test__")                           # 門そのものを触った
    return surf


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--list", action="store_true", help="選んだ門と理由だけ見る")
    ap.add_argument("--all", action="store_true",
                    help="git の差分を見ず、帳簿に触る門を全部回す")
    ap.add_argument("--no-regen", action="store_true",
                    help="regen_all.py --check を省く(生成物を触っていない時だけ)")
    args = ap.parse_args(argv)

    sel = _selected()
    if not args.all:
        paths = _changed_paths()
        touched = _touched_surfaces(paths)
        print("変更: %d ファイル → 動きうる帳簿: %s"
              % (len(paths), ", ".join(sorted(touched)) or "(無し)"))
        if touched:
            changed_tests = {p.split("/")[-1] for p in paths if p.startswith("tests/")}
            sel = [(n, h) for n, h in sel
                   if (set(h) & touched) or n in changed_tests]
        else:
            sel = []

    print("選んだ門: %d ファイル" % len(sel))
    for name, hit in sel:
        print("  %-46s %s" % (name, ", ".join(SURFACES[h] for h in hit[:3])))
    if args.list:
        return 0

    if not args.no_regen:
        print("\n=== tools/regen_all.py --check(★孤児ノートは先に消すこと)")
        rc = subprocess.call([sys.executable,
                              os.path.join(ROOT, "tools", "regen_all.py"), "--check"],
                             cwd=ROOT)
        if rc:
            print("生成物に差分がある。作り直して commit に含めること。")
            return rc

    if not sel:
        print("\n回す門が無い(帳簿に触っていない)。push 前のフルスイートは別途 1 回。")
        return 0

    print("\n=== pytest")
    cmd = [sys.executable, "-m", "pytest", "-q", "-p", "no:randomly"]
    cmd += [os.path.join("tests", n) for n, _ in sel]
    return subprocess.call(cmd, cwd=ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
