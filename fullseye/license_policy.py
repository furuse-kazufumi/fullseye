# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""配布時の強いコピーレフト例外を一か所に置く / one source of truth for distribution exceptions.

The licence-compliance workstream records ``plyfile`` as GPL-3.0-or-later and
limits it to the independent export-verification extra.  Setup imports this
small, dependency-free policy so it cannot accidentally turn that test reader
into a default product installation.
"""
from __future__ import annotations

STRONG_COPYLEFT_EXTRAS = {
    "export-verify": {
        "package": "plyfile",
        "spdx": "GPL-3.0-or-later",
        "reason_ja": "`export-verify` は GPL-3.0-or-later の `plyfile` を含むため既定では入れません。"
                     " 本番の配布物に強いコピーレフト依存を意図せず加えないためです。"
                     " 入れる場合は `fullseye setup --include export-verify` を実行してください。",
        "reason_en": "`export-verify` is not installed by default because it includes GPL-3.0-or-later "
                     "`plyfile`; this prevents an unintended strong-copyleft dependency in a product install. "
                     "To include it, run `fullseye setup --include export-verify`.",
    },
}
