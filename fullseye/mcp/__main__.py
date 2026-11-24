# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
import sys

from fullseye import startup_errors

try:
    from .server import main
    sys.exit(main())
except (ImportError, OSError, UnicodeError) as exc:
    # stdout は MCP protocol 専用。 / stdout belongs to the MCP protocol.
    # server 前は stderr だけが説明と元 traceback を安全に出せる。 / Before it starts, stderr is the safe human channel.
    startup_errors.report(exc, "MCP server")
    sys.exit(1)
