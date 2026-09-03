"""pre-commit mirror for the gh-aw agentic-workflow compiler.

gh-aw is a Go binary distributed only as a ``gh`` CLI extension and as raw
per-platform release binaries. It cannot be installed with ``go install`` (its
``go.mod`` carries ``replace`` directives, which ``go install pkg@version``
rejects), and it publishes no PyPI wheel, so none of pre-commit's tool-managing
languages can fetch it directly.

This shim closes that gap: on first run it downloads the pinned gh-aw release
binary for the current platform, verifies it against the checksums committed
next to this file, caches it inside the installed package, and execs it. No
system ``gh`` or ``gh-aw`` install is required.
"""

from __future__ import annotations

import hashlib
import os
import platform
import stat
import sys
import urllib.request
from pathlib import Path

# Single source of truth for the mirrored gh-aw version; the git tag and the
# committed checksums.txt are kept in sync with it by update.py.
__version__ = "0.88.2"

_RELEASE = "https://github.com/github/gh-aw/releases/download/v{version}/{asset}"
_PKG = Path(__file__).resolve().parent
_BIN_DIR = _PKG / "_bin"

_ARCH = {
    "x86_64": "amd64",
    "amd64": "amd64",
    "aarch64": "arm64",
    "arm64": "arm64",
    "i386": "386",
    "i686": "386",
    "x86": "386",
}
_OS = frozenset({"linux", "darwin", "windows"})


def _asset_name() -> str:
    system = platform.system().lower()
    machine = platform.machine().lower()
    arch = _ARCH.get(machine)
    if system not in _OS or arch is None:
        raise SystemExit(f"gh-aw-mirror: unsupported platform {system}/{machine}")
    return f"{system}-{arch}.exe" if system == "windows" else f"{system}-{arch}"


def _expected_sha(asset: str) -> str:
    for line in (_PKG / "checksums.txt").read_text().splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1] == asset:
            return parts[0]
    raise SystemExit(f"gh-aw-mirror: no pinned checksum for {asset} at v{__version__}")


def _ensure_binary() -> Path:
    asset = _asset_name()
    binary = _BIN_DIR / f"gh-aw-{__version__}-{asset}"
    if binary.exists():
        return binary
    url = _RELEASE.format(version=__version__, asset=asset)
    with urllib.request.urlopen(url) as resp:
        data = resp.read()
    actual = hashlib.sha256(data).hexdigest()
    expected = _expected_sha(asset)
    if actual != expected:
        raise SystemExit(
            f"gh-aw-mirror: checksum mismatch for {asset}\n"
            f"  expected {expected}\n"
            f"  got      {actual}"
        )
    _BIN_DIR.mkdir(parents=True, exist_ok=True)
    tmp = binary.with_name(binary.name + ".tmp")
    tmp.write_bytes(data)
    tmp.chmod(tmp.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    tmp.replace(binary)
    return binary


def main() -> int:
    binary = _ensure_binary()
    argv = [str(binary), *sys.argv[1:]]
    if os.name == "nt":
        import subprocess

        return subprocess.call(argv)
    os.execv(str(binary), argv)  # replaces this process; never returns on POSIX
    return 0  # pragma: no cover


if __name__ == "__main__":
    raise SystemExit(main())
