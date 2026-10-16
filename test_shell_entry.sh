#!/usr/bin/env bash
# Bash 3.2-compatible caller/entry contract. Only new retained fixtures; no Git.
set -eu
PY=${1:?usage: bash test_shell_entry.sh /absolute/path/to/python}
# The executable entry uses /usr/bin/env python3; pin it to the same interpreter.
PATH="$(dirname -- "$PY"):$PATH"
export PATH
SOURCE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
FIXTURE=$(mktemp -d "${TMPDIR:-/tmp}/git-sync-shell.XXXXXX")
WS="$FIXTURE/caller with spaces"
REPO="$WS/standalone arbitrary name"
mkdir -p "$REPO" "$FIXTURE/unrelated cwd"
cp "$SOURCE/platform_paths.py" "$SOURCE/git-sync.py" "$REPO/"
ln -s "$REPO/git-sync.py" "$FIXTURE/entry link.py"
ln -s "$REPO/platform_paths.py" "$FIXTURE/helper link.py"
cd "$FIXTURE/unrelated cwd"
for entry in "$REPO/git-sync.py" "$FIXTURE/entry link.py"; do
    actual=$(PLATFORM_WORKSPACE='' "$PY" -c 'import runpy,sys; print(runpy.run_path(sys.argv[1])["DEFAULT_ROOT"])' "$entry")
    test "$actual" = "$WS"
    actual=$(PLATFORM_WORKSPACE="$FIXTURE/override with spaces" "$PY" -c 'import runpy,sys; print(runpy.run_path(sys.argv[1])["DEFAULT_ROOT"])' "$entry")
    test "$actual" = "$FIXTURE/override with spaces"
    PLATFORM_WORKSPACE='' "$PY" "$entry" --help > "$FIXTURE/help.txt"
    PLATFORM_WORKSPACE='' "$entry" --help > "$FIXTURE/direct-help.txt"
done
for helper in "$REPO/platform_paths.py" "$FIXTURE/helper link.py"; do
    actual=$(PLATFORM_WORKSPACE='' "$PY" "$helper" "$FIXTURE/entry link.py")
    test "$actual" = "$WS"
    actual=$(HOME="$FIXTURE" PLATFORM_WORKSPACE='~/expanded caller' "$PY" "$helper" "$REPO/git-sync.py")
    test "$actual" = "$FIXTURE/expanded caller"
done
cd "$FIXTURE"
actual=$(PLATFORM_WORKSPACE='' "$PY" 'caller with spaces/standalone arbitrary name/platform_paths.py' 'entry link.py')
test "$actual" = "$WS"
printf 'PASS shell=%s; real/symlink/relative/helper/space/override; fixtures retained=%s\n' "$BASH_VERSION" "$FIXTURE"
