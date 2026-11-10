import os
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import updater as U  # noqa: E402

PULLED = """Updating 8fd3772..a1b2c3d4e5
Fast-forward
 capri.py | 12 ++++++------
 1 file changed, 6 insertions(+), 6 deletions(-)
"""


class ParseTests(unittest.TestCase):
    def test_outcomes(self):
        self.assertEqual(U.parse_pull(0, "Already up to date.\n", ""), ("current", ""))
        self.assertEqual(U.parse_pull(0, PULLED, "From https://x\n   8fd3772..a1b2c3d  main -> origin/main\n"),
                         ("updated", ("8fd3772", "a1b2c3d4e5")))
        cases = {
            "error: Your local changes to the following files would be overwritten by merge:\n\tcapri.py\n"
            "Please commit your changes or stash them before you merge.\nAborting": "local_changes",
            "fatal: unable to access 'https://github.com/a/b/': Could not resolve host: github.com": "offline",
            "fatal: unable to access 'https://github.com/a/b/': The requested URL returned error: 403": "login",
            "fatal: could not read Username for 'https://github.com': terminal prompts disabled": "login",
            "remote: Repository not found.\nfatal: repository 'https://github.com/a/b/' not found": "login",
            "There is no tracking information for the current branch.": "no_branch",
            "You are not currently on a branch.": "no_branch",
            "fatal: Not possible to fast-forward, aborting.": "diverged",
            "fatal: not a git repository (or any of the parent directories): .git": "not_git",
        }
        for err, want in cases.items():
            self.assertEqual(U.parse_pull(1, "", err)[0], want, err)
        st, detail = U.parse_pull(128, "", "warning: x\nfatal: something odd happened\n")
        self.assertEqual((st, detail), ("error", "fatal: something odd happened"))
        self.assertEqual(U.parse_pull(2, "", "")[0], "error")

    def test_subjects(self):
        log = ("Fix: she fell off the window\nMerge pull request #7 from a/b\nHANDOFF: notes\n"
               "Fix: she fell off the window\n\n" + "x" * 300 + "\n" + "\n".join(f"change {i}" for i in range(9)))
        subs, more = U.subjects(log)
        self.assertEqual(subs[0], "Fix: she fell off the window")
        self.assertEqual(len(subs), U.MAX_NEWS)
        self.assertEqual(more, 5)
        self.assertTrue(all(len(s) <= 110 for s in subs))
        self.assertFalse(any("Merge" in s or "HANDOFF" in s for s in subs))
        self.assertEqual(U.subjects(""), ([], 0))

    def test_report_text(self):
        lines = U.report("updated", ("a", "b"), ["One", "Two"], 3)
        self.assertIn("start me again", lines[0])
        self.assertEqual(lines[1:], ["New:", "  - One", "  - Two", "  ...and 3 more."])
        self.assertEqual(U.report("updated", ("", ""))[1:], [])
        self.assertIn("3 updates waiting", U.report("behind", "3")[0])
        self.assertIn("1 update waiting", U.report("behind", "1")[0])
        self.assertEqual(U.report("behind", "0"), [U.MESSAGES["current"]])
        self.assertIn("odd", U.report("error", "odd thing")[0])
        for st in ("current", "local_changes", "offline", "login", "no_branch", "not_git", "diverged", "no_git", "frozen"):
            self.assertTrue(U.report(st)[0])

    def test_env_never_prompts(self):
        env = U.git_env({"PATH": "/x", "LANG": "fr_FR.UTF-8"})
        self.assertEqual(env["GIT_TERMINAL_PROMPT"], "0")
        self.assertEqual(env["LC_ALL"], "C")
        self.assertEqual(env["PATH"], "/x")


@unittest.skipUnless(shutil.which("git"), "git not installed")
class RealGitTests(unittest.TestCase):
    """The parser against what a real git says (a local 'remote', no network)."""

    def git(self, cwd, *args):
        env = U.git_env(os.environ)
        env.update({"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid", "GIT_COMMITTER_NAME": "t",
                    "GIT_COMMITTER_EMAIL": "t@example.invalid", "GIT_CONFIG_GLOBAL": os.devnull,
                    "GIT_CONFIG_SYSTEM": os.devnull})
        return subprocess.run(["git", *args], cwd=cwd, env=env, capture_output=True, text=True, timeout=60)

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.origin = os.path.join(self.tmp, "origin")
        self.copy = os.path.join(self.tmp, "copy")
        os.mkdir(self.origin)
        self.git(self.origin, "init", "-q", "-b", "main")
        self.commit(self.origin, "capri.py", "v1", "First version")
        self.git(self.tmp, "clone", "-q", self.origin, "copy")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def commit(self, repo, name, text, msg):
        with open(os.path.join(repo, name), "w") as f:
            f.write(text)
        self.git(repo, "add", "-A")
        self.git(repo, "commit", "-q", "-m", msg)

    def pull(self):
        r = self.git(self.copy, *U.PULL[1:])
        return U.parse_pull(r.returncode, r.stdout, r.stderr)

    def test_current_then_updated_with_news(self):
        self.assertTrue(U.is_checkout(self.copy))
        self.assertFalse(U.is_checkout(self.tmp))
        self.assertEqual(self.pull(), ("current", ""))
        self.commit(self.origin, "capri.py", "v2", "Fix: she fell off the window")
        self.commit(self.origin, "notes.py", "n", "Notes: voice recall")
        self.git(self.copy, *U.FETCH[1:])
        self.assertEqual(self.git(self.copy, *U.BEHIND[1:]).stdout.strip(), "2")
        status, (old, new) = self.pull()
        self.assertEqual(status, "updated")
        log = self.git(self.copy, *U.news_cmd(old, new)[1:]).stdout
        self.assertEqual(U.subjects(log), (["Notes: voice recall", "Fix: she fell off the window"], 0))
        with open(os.path.join(self.copy, "capri.py")) as f:
            self.assertEqual(f.read(), "v2")

    def test_local_edits_are_never_overwritten(self):
        self.commit(self.origin, "capri.py", "v2", "Newer")
        with open(os.path.join(self.copy, "capri.py"), "w") as f:
            f.write("my own edit")
        self.assertEqual(self.pull()[0], "local_changes")
        with open(os.path.join(self.copy, "capri.py")) as f:
            self.assertEqual(f.read(), "my own edit")

    def test_own_commits_are_left_alone(self):
        self.commit(self.origin, "capri.py", "v2", "Newer")
        self.commit(self.copy, "mine.py", "x", "My own change")
        self.assertEqual(self.pull()[0], "diverged")

    def test_remote_gone_and_not_a_checkout(self):
        shutil.rmtree(self.origin)
        self.assertIn(self.pull()[0], ("offline", "error", "login"))
        r = self.git(self.tmp, *U.PULL[1:])
        self.assertEqual(U.parse_pull(r.returncode, r.stdout, r.stderr)[0], "not_git")


if __name__ == "__main__":
    unittest.main()
