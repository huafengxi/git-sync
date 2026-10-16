# git-sync source recovery (task rd6-g-171006)

Candidate source only. No installation, caller preconfiguration, service switch,
profile update or production activation is part of this repository recovery.

## History and projection

Original main `77e2c85fa084f8c808928d37c45b5e119844ca90` remains an ancestor.
The integrated baseline `990253da3b5c5ec83fd43a2a463f39ed6d42aadf:git-sync`
is exactly that original main tree. All original files, not just changed paths,
therefore come from the original history. Discovery per candidate (including
slashed/unslashed check-ignore fallback), mirror discovery, clean-worktree /
ahead checks, ff-only pulls and non-force mirror fetches are inherited intact.

`source-refs.json` records original archive/retired refs and OIDs, target
mappings and per-ref object closures. The old reflog-only root remains on
`refs/heads/preserve/reflog-initial-4f08270`, never substituted for main.
`preserve/source-remotes/origin/main` retains the original main OID. No preserve
ref was rewritten, no old history filtered, no cross-module commit cherry-picked.

`projection.json` enumerates all first-parent source commits in order from the
baseline through `4ac4631fbdbf27f3c400805b233dc1d7a9892d46`. Exact path projections
are separate commits, followed by the standalone adaptation. Each projected
path records before/after blob, mode and deletion state. Irrelevant commits
are explicit no-ops, not omitted. The intermediate portable installer and its
later replacement are both recorded as no-ops for this module; no installer is
resurrected. There are no deleted git-sync/helper paths in this source range.
The final three-file pi-wrap-only source delta (c8tpr5) is committed upstream
and recorded as another no-op; its previously dirty worktree was never copied.

### Shared source and root README

The local helper and original contract tests were introduced by
`9809211b1e91adabb0dfda570bd4a79dc4313d21`, then changed by
`4dd1b8eaa958ef5f236afed78a74be30e43d030b`. Both intermediate versions are
preserved in the exact projection commits. No helper is imported from a
sibling directory or the integrated platform if the local copy is missing.

Root README changes are classified per source in projection.json:

- `9809211…`: generic module purpose, caller-owned configuration boundary,
  workspace override and CLI precedence are retained in this README's Boundary /
  root contract (the repository root `README.md`). Whole-platform layout,
  six-module table, installation and integrated test runner are not a git-sync
  mechanism and are not copied.
- `4dd1b8e…`: canonical `agent-platform/<module>` command examples and installation
  aliases are superseded by standalone absolute-path examples; the caller-root
  contract is retained, no compatibility alias/sibling fallback is added.
- `f93b8eb…`, `fb758234…`: integrated portable installer then in-place launcher
  guidance belongs to agentd/portable, not git-sync. These documentation changes
  are classified no-op here, not silently dropped as runnable git-sync code.

The module README's original deployment-specific machine name, service commands
and hook installation path are removed from the public mechanism documentation.
Their generic meaning remains: callers own supervision and mirror push-back,
and a broken discovery face cannot deliver its own fix. This is a documentation
boundary adaptation, not permission to modify any actual deployment.

## Standalone adaptation by path

| Path | Difference from exact projection | Reason / verification |
| --- | --- | --- |
| git-sync.py (100755) | import helper from real source directory; SCRIPT_DIR uses realpath; generic opening text and --root help | real/symlink/relative CLI in non-sibling layout; sync/discovery/mirror function ASTs unchanged; main differs only in help text |
| platform_paths.py (100644) | remove marker + integrated MODULES coupling; honor nonempty override even without marker; resolve source symlinks | local contract v1 below; independent helper tests |
| test_platform_paths.py (100644) | replace integrated six-module fixtures with standalone contract fixtures | no production workspace and no dependency on other modules |
| test_git_sync.py (100644) | retain original assertions; retain fixtures instead of recursive cleanup; clone directly into unused slots | original 49 assertions; all pulls/fetches to local fixture origins only |
| README.md (100644) | independent root/usage/boundary docs above | mechanism only, caller deployment not activated |
| test_recovery.py (100644, new) | standalone entries, real mirror ff/rejection, timeout and overlap fixtures | six isolated regressions; fixture-only Git |
| test_shell_entry.sh (100644, new) | Bash 3.2-compatible test caller, no runtime wrapper | quoted spaces, real/symlink/relative helper + CLI, explicit override |
| recovery/* (100644, new) | history/projection/adaptation/test evidence | metadata only; no service/caller manifest |

### Local workspace helper contract v1

`workspace_root(source)` returns an absolute string. Nonempty
`PLATFORM_WORKSPACE` wins, expands `~`, and resolves relative values against the
caller's cwd. Empty/unset override defaults to the real source repo's parent.
Marker presence is irrelevant. Root selection follows source identity, not a
symlink's lexical ancestors. git-sync's existing `--root` still wins at the CLI.
Fixed release callers must provide their real workspace explicitly. No new
module-specific environment variable or runtime dependency is introduced.

The original mirror-mode predicate is deliberately unchanged: a root equal to
DEFAULT_ROOT with no --repos can fetch mirrors even when that identical root
was explicitly passed. README documents this boundary; tests always use their
own fixture paths / --repos and never rely on that argument alone for isolation.

## Validation and reproduction

Use a new external test root (not a production workspace) for TMPDIR and HOME,
set GIT_CONFIG_GLOBAL=/dev/null, GIT_CONFIG_NOSYSTEM=1, GIT_TERMINAL_PROMPT=0,
and PYTHONDONTWRITEBYTECODE=1; invoke the conda Python on each `test_*.py`.
Then invoke `bash test_shell_entry.sh /absolute/path/to/conda/python` using a
real Bash 3.2 binary as well as the available host Bash. All fixtures are newly
created and retained. No production fetch, model call or cleanup is required.

`validation.json` records per-source and per-path content/mode/deletion checks,
original refs/closures, ancestor verification and source freshness. Function AST
comparison proves that the original main's synchronization behavior is unchanged.
`test-results.json` records tested versions, commands, outcome and harness fixes.
Full logs and immutable source objects are retained in this task's external
staging; independent review should rerun, not treat these results as review PASS.
