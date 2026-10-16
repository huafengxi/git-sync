"""Resolve the caller workspace for a standalone source checkout.

Contract version 1. The implementation is local: no sibling repositories or
consolidated-platform marker are consulted. See recovery/ADAPTATION.md.
"""
import os
from pathlib import Path
import sys


def workspace_root(source):
    """Return an absolute caller root, independent of cwd and checkout name.

    A nonempty PLATFORM_WORKSPACE overrides the source-derived default and
    expands ``~``. Relative overrides are resolved against the caller's cwd.
    Without an override, follow source symlinks and use the source repo's
    parent directory. CLI-specific --root precedence belongs to each caller.
    """
    override = os.environ.get("PLATFORM_WORKSPACE")
    if override:
        return str(Path(override).expanduser().resolve())
    return str(Path(source).resolve().parent.parent)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: platform_paths.py <component entry path>")
    print(workspace_root(sys.argv[1]))
