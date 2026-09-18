"""Code version a Forecast Run was produced with."""

from __future__ import annotations

import os
import subprocess
from functools import lru_cache
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


@lru_cache(maxsize=1)
def git_version() -> tuple[str | None, bool | None]:
    """Return (commit SHA, whether the working tree has uncommitted changes)."""
    if sha := os.environ.get("GITHUB_SHA"):
        return sha, False
    try:
        sha = _git("rev-parse", "HEAD")
        dirty = bool(_git("status", "--porcelain", "--untracked-files=no"))
    except (OSError, subprocess.CalledProcessError):
        return None, None
    return sha, dirty


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()
