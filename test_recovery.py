"""Recovery regressions: local mirror fixtures and standalone CLI entries only.

All repositories, HOME, cwd, and mirror dirs are new retained fixtures. No
network remotes, production workspace, recursive cleanup or service execution.
"""
import contextlib
import importlib.util
import io
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("git_sync_recovery", HERE / "git-sync.py")
gs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gs)


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="git-sync-recovery-")).resolve()
        self.home = self.root / "home with spaces"
        self.home.mkdir()
        self.env = dict(os.environ, HOME=str(self.home), GIT_CONFIG_NOSYSTEM="1",
                        GIT_CONFIG_GLOBAL=os.devnull, GIT_TERMINAL_PROMPT="0",
                        PYTHONDONTWRITEBYTECODE="1", PYTHONPATH="", PLATFORM_WORKSPACE="")

    def git(self, path, *args):
        r = subprocess.run(["git", "-C", str(path), *args], env=self.env,
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout.strip()

    def identity(self, path):
        self.git(path, "config", "user.name", "fixture")
        self.git(path, "config", "user.email", "fixture@example.invalid")
        self.git(path, "config", "commit.gpgsign", "false")

    def commit(self, path, filename):
        (path / filename).write_text("local fixture\n")
        self.git(path, "add", "--", filename)
        self.git(path, "commit", "-qm", "fixture change", "--", filename)
        return self.git(path, "rev-parse", "HEAD")

    def mirror_fixture(self):
        src = self.root / "source"
        src.mkdir()
        self.git(src, "init", "-q")
        self.git(src, "symbolic-ref", "HEAD", "refs/heads/main")
        self.identity(src)
        self.commit(src, "seed")
        upstream = self.root / "upstream.git"
        self.git(self.root, "clone", "-q", "--bare", str(src), str(upstream))
        self.git(src, "remote", "add", "origin", str(upstream))
        mirrors = self.root / "mirrors with spaces"
        mirrors.mkdir()
        mirror = mirrors / "candidate.git"
        self.git(self.root, "clone", "-q", "--bare", str(upstream), str(mirror))
        return src, upstream, mirrors, mirror

    def test_real_mirror_fast_forward_and_non_ff_rejection(self):
        src, upstream, mirrors, mirror = self.mirror_fixture()
        advanced = self.commit(src, "upstream update")
        self.git(src, "push", "-q", "origin", "main")
        self.assertEqual(gs.mirror_repos(str(mirrors)), ["candidate"])
        self.assertEqual(gs.mirror_fetch(str(mirrors)), 0)
        self.assertEqual(self.git(mirror, "rev-parse", "main"), advanced)
        local = self.root / "mirror author"
        self.git(self.root, "clone", "-q", str(mirror), str(local))
        self.identity(local)
        mirror_tip = self.commit(local, "mirror only")
        self.git(local, "push", "-q", "origin", "main")
        upstream_tip = self.commit(src, "upstream only")
        self.git(src, "push", "-q", "origin", "main")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.assertEqual(gs.mirror_fetch(str(mirrors)), 1)
        self.assertIn("WARN fetch (non-ff or error)", buf.getvalue())
        self.assertEqual(self.git(mirror, "rev-parse", "main"), mirror_tip)
        self.assertEqual(self.git(upstream, "rev-parse", "main"), upstream_tip)

    def test_mirror_thread_does_not_overlap(self):
        entered, release = threading.Event(), threading.Event()
        calls = []
        def blocked(path):
            calls.append(path)
            entered.set()
            if not release.wait(10):
                raise AssertionError("test timeout")
            return 0
        with patch.object(gs, "mirror_fetch", blocked):
            thread = gs.start_mirror_fetch(str(self.root / "empty fixture"))
            try:
                self.assertTrue(entered.wait(5))
                self.assertIsNone(gs.start_mirror_fetch(str(self.root / "empty fixture")))
                self.assertEqual(len(calls), 1)
            finally:
                release.set()
                thread.join(10)
            self.assertFalse(thread.is_alive())
        self.assertFalse(gs._MIRROR_LOCK.locked())

    def test_mirror_fetch_timeout_is_bounded_and_visible(self):
        _, _, mirrors, _ = self.mirror_fixture()
        with patch.object(gs, "git", side_effect=subprocess.TimeoutExpired("fixture git", 1)) as mock:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                self.assertEqual(gs.mirror_fetch(str(mirrors)), 1)
            self.assertEqual(mock.call_args.kwargs["timeout"], gs.MIRROR_FETCH_TIMEOUT)
            self.assertIn("WARN fetch exception (TimeoutExpired)", buf.getvalue())

    def copy_entry(self):
        repo = self.root / "caller with spaces" / "standalone source"
        repo.mkdir(parents=True)
        for filename in ("git-sync.py", "platform_paths.py"):
            shutil.copyfile(HERE / filename, repo / filename)
        link = self.root / "symlink entry.py"
        link.symlink_to(repo / "git-sync.py")
        return repo, link

    def test_default_root_real_symlink_and_relative_entry(self):
        repo, link = self.copy_entry()
        code = "import runpy,sys; print(runpy.run_path(sys.argv[1])['DEFAULT_ROOT'])"
        for entry in (repo / "git-sync.py", link, Path("caller with spaces/standalone source/git-sync.py")):
            p = subprocess.run([sys.executable, "-c", code, str(entry)], cwd=self.root,
                               env=self.env, capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertEqual(p.stdout.strip(), str(repo.parent))

    def test_cli_root_priority_and_symlink_with_local_origin_only(self):
        src, upstream, _, _ = self.mirror_fixture()
        caller = self.root / "explicit workspace"
        self.git(self.root, "clone", "-q", str(upstream), str(caller))
        repo, link = self.copy_entry()
        for entry in (repo / "git-sync.py", link):
            p = subprocess.run([sys.executable, str(entry), "--once", "--root", str(caller),
                                "--repos", ".", "--mirror-dir", str(self.root / "no mirrors")],
                               cwd=self.home, env=dict(self.env, PLATFORM_WORKSPACE=str(self.root / "wrong env root")),
                               capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stderr + p.stdout)
            self.assertIn("root=" + str(caller) + ",", p.stdout)
            self.assertIn("mirror=no", p.stdout)
        p = subprocess.run([sys.executable, str(link), "--once", "--repos", ".",
                            "--mirror-dir", str(self.root / "no mirrors")], cwd=self.home,
                           env=dict(self.env, PLATFORM_WORKSPACE=str(caller)), capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr + p.stdout)
        self.assertIn("root=" + str(caller) + ",", p.stdout)

    def test_no_fallback_if_local_helper_is_missing(self):
        repo = self.root / "no helper source"
        repo.mkdir()
        shutil.copyfile(HERE / "git-sync.py", repo / "git-sync.py")
        p = subprocess.run([sys.executable, str(repo / "git-sync.py"), "--help"],
                           cwd=self.home, env=self.env, capture_output=True, text=True)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("platform_paths", p.stderr)


if __name__ == "__main__":
    unittest.main()
