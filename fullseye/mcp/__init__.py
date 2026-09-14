# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""fullseye を MCP(Model Context Protocol)から使う。

    py -3.11 -m fullseye.mcp              # stdio サーバ
    py -3.11 -m fullseye.mcp --coverage   # カタログ 4 層の被覆を JSON で

置き場所を ``fullseye/`` の下にしたのは、root モジュールを増やすと **wheel から
落ちる事故**(0.1.6 で 321 op、2026-09-05 で 224 op、2026-09-14 で 26 op)を
再発させるため。``packages = ["fullseye", ...]`` の下なら自動で同梱される。
"""
from .catalog import Catalog, CatalogError
from .server import TOOLS, call_tool, dispatch, run_stdio_server, main

__all__ = ["Catalog", "CatalogError", "TOOLS", "call_tool", "dispatch",
           "run_stdio_server", "main"]
