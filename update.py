#!/usr/bin/env python3
"""Bump this mirror to the latest gh-aw release.

Rewrites ``__version__`` in gh_aw_mirror/__init__.py and refreshes the committed
checksums.txt. Prints the new version on stdout (or ``up-to-date: <v>`` when
there is nothing to do) so .github/workflows/mirror.yml can tag the result.
"""

from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INIT = ROOT / "gh_aw_mirror" / "__init__.py"
CHECKSUMS = ROOT / "gh_aw_mirror" / "checksums.txt"
LATEST_API = "https://api.github.com/repos/github/gh-aw/releases/latest"
CHECKSUMS_URL = "https://github.com/github/gh-aw/releases/download/v{v}/checksums.txt"


def _current_version() -> str:
    match = re.search(r'__version__ = "([^"]+)"', INIT.read_text())
    if match is None:
        raise SystemExit("update: could not find __version__ in __init__.py")
    return match.group(1)


def main() -> None:
    with urllib.request.urlopen(LATEST_API) as resp:
        latest = json.load(resp)["tag_name"].lstrip("v")
    if latest == _current_version():
        print(f"up-to-date: {latest}")
        return
    with urllib.request.urlopen(CHECKSUMS_URL.format(v=latest)) as resp:
        CHECKSUMS.write_bytes(resp.read())
    INIT.write_text(
        re.sub(r'__version__ = "[^"]+"', f'__version__ = "{latest}"', INIT.read_text())
    )
    print(latest)


if __name__ == "__main__":
    main()
