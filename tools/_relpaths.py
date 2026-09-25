# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""生成物に残すパスを **repo からの相対**に落とす。

★2026-09-25: 棟の台帳 6 本(`docs/articles/assets/_*_meta.json`)が、図の場所を
手元の絶対パスで書いていた。公開される `docs/` の下なので、読み手の機械には無い
パスが載り、こちらの作業環境も晒していた。生成のときに絶対で持つのは正しい ——
**残すときに落とす**。

規則の実装はここ 1 つだけにする。6 本の生成器がそれぞれ持つと、次に台帳を足した
人が 1 つだけ直して、残りは静かに絶対のままになる。
`tests/test_docs_no_local_paths.py` が公開範囲を見張る。
"""
from __future__ import annotations

import os

__all__ = ["relativise"]


def relativise(obj, root: str):
    """*obj* の中の、*root* の下を指す文字列を repo 相対に落として返す。

    dict / list / str を再帰的にたどる。*root* の外を指すパスと、パスでない文字列は
    そのまま返す —— **書き換えすぎない**(説明文のなかの `C:` の話まで壊さない)。
    区切りは `/` に揃える(台帳は OS をまたいで読まれる)。
    """
    if isinstance(obj, dict):
        return {k: relativise(v, root) for k, v in obj.items()}
    if isinstance(obj, list):
        return [relativise(v, root) for v in obj]
    if isinstance(obj, str):
        flat, base = obj.replace(chr(92), "/"), root.replace(chr(92), "/")
        if flat.lower().startswith(base.lower().rstrip("/") + "/"):
            return os.path.relpath(obj, root).replace(os.sep, "/")
    return obj
