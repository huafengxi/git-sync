"""Standalone helper contract v1; only newly created, retained fixtures.

The integrated-platform MODULES/marker tests are deliberately replaced: this
repository neither knows siblings nor needs a consolidated checkout.
"""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from platform_paths import workspace_root

HERE = Path(__file__).resolve().parent


class LayoutTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="git-sync-root-contract-")).resolve()
        self.ws = self.root / "caller with spaces"
        self.repo = self.ws / "arbitrary standalone checkout"
        self.repo.mkdir(parents=True)
        self.entry = self.repo / "git-sync.py"
        self.entry.touch()
        self.link = self.root / "entry link.py"
        self.link.symlink_to(self.entry)

    def test_default_real_and_symlink_identity_without_marker(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(workspace_root(self.entry), str(self.ws))
            self.assertEqual(workspace_root(self.link), str(self.ws))
            (self.repo / ".platform-root").touch()
            self.assertEqual(workspace_root(self.entry), str(self.ws))

    def test_explicit_override_independent_of_source_and_marker(self):
        with patch.dict(os.environ, {"PLATFORM_WORKSPACE": str(self.root / "explicit caller")}):
            self.assertEqual(workspace_root(self.entry), str(self.root / "explicit caller"))
            self.assertEqual(workspace_root(self.link), str(self.root / "explicit caller"))

    def test_empty_override_uses_source(self):
        with patch.dict(os.environ, {"PLATFORM_WORKSPACE": ""}):
            self.assertEqual(workspace_root(self.entry), str(self.ws))

    def test_expanduser_and_relative_override(self):
        with patch.dict(os.environ, {"HOME": str(self.root), "PLATFORM_WORKSPACE": "~/workspace with spaces"}):
            self.assertEqual(workspace_root(self.entry), str(self.root / "workspace with spaces"))
        with patch.dict(os.environ, {"PLATFORM_WORKSPACE": "relative workspace"}):
            self.assertEqual(workspace_root(self.entry), str((Path.cwd() / "relative workspace").resolve()))

    def test_helper_cli_different_cwd_real_and_symlink(self):
        helper = self.repo / "platform_paths.py"
        shutil.copyfile(HERE / "platform_paths.py", helper)
        env = dict(os.environ, PLATFORM_WORKSPACE="", PYTHONDONTWRITEBYTECODE="1")
        helper_link = self.root / "helper link.py"
        helper_link.symlink_to(helper)
        for executable in (helper, helper_link):
            for source in (self.entry, self.link, Path("../caller with spaces/arbitrary standalone checkout/git-sync.py")):
                cwd = self.root / "other cwd"
                cwd.mkdir(exist_ok=True)
                p = subprocess.run([sys.executable, str(executable), str(source)], cwd=cwd,
                                   env=env, capture_output=True, text=True)
                self.assertEqual(p.returncode, 0, p.stderr)
                self.assertEqual(p.stdout.strip(), str(self.ws))


if __name__ == "__main__":
    unittest.main()
