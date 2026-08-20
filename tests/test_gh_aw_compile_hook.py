from __future__ import annotations

import os
import shlex
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

# Allow overriding how prek is invoked, e.g. PREK="uvx prek" in CI.
PREK = shlex.split(os.environ.get("PREK", "prek"))

WORKFLOW_MD = """\
---
on:
  workflow_dispatch:
permissions:
  contents: read
engine: copilot
---

# Demo Workflow

Say hello to the world.
"""


def _is_prek_available() -> bool:
    return shutil.which(PREK[0]) is not None


pytestmark = pytest.mark.skipif(
    not _is_prek_available(), reason=f"{PREK[0]} not found on PATH"
)


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.pop("SKIP", None)  # don't let a caller's SKIP disable the hook
    return subprocess.run(
        cmd, cwd=cwd, env=env, capture_output=True, text=True, check=False
    )


def _git(args: list[str], cwd: Path) -> None:
    result = _run(["git", *args], cwd)
    assert result.returncode == 0, f"git {args} failed:\n{result.stderr}"


def _try_repo(cwd: Path) -> subprocess.CompletedProcess[str]:
    return _run(
        [*PREK, "try-repo", str(REPO_ROOT), "gh-aw-compile", "--all-files"], cwd
    )


@pytest.fixture
def consumer_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "consumer"
    (repo / ".github" / "workflows").mkdir(parents=True)
    (repo / ".github" / "workflows" / "demo.md").write_text(WORKFLOW_MD)
    (repo / ".github" / "workflows" / "demo.lock.yml").write_text("# stale lock\n")

    _git(["init"], repo)
    _git(["config", "user.email", "test@example.com"], repo)
    _git(["config", "user.name", "test"], repo)
    _git(["add", "-A"], repo)
    _git(["commit", "-m", "init"], repo)
    return repo


def test_hook_recompiles_stale_lock_then_is_idempotent(consumer_repo: Path) -> None:
    lock = consumer_repo / ".github" / "workflows" / "demo.lock.yml"

    # Out of sync: the hook recompiles, the tracked lock changes, prek fails.
    stale = _try_repo(consumer_repo)
    assert stale.returncode != 0, stale.stdout + stale.stderr
    compiled = lock.read_text()
    assert compiled != "# stale lock\n"
    assert "gh-aw-metadata" in compiled

    # In sync: stage the freshly compiled lock, the hook produces the same
    # output, nothing changes, prek passes.
    _git(["add", "-A"], consumer_repo)
    ok = _try_repo(consumer_repo)
    assert ok.returncode == 0, ok.stdout + ok.stderr

    diff = _run(["git", "diff", "--stat"], consumer_repo)
    assert diff.stdout.strip() == "", (
        f"hook modified files on a clean run:\n{diff.stdout}"
    )
