"""The plugin around the skill: the hooks it registers and the SKILL.md.

What it pins: hooks/hooks.json registers the three adapters, each by
`${CLAUDE_PLUGIN_ROOT}`, run with `python3 -B` and ending in `|| true` so a
missing script cannot block a prompt, and every one it names exists; the
SKILL.md opens with the Values block, grants exactly that one command in its
frontmatter, hands `claim` the session id, names no person and no path in its
description, and keeps no build-time placeholder.
"""
from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from subprocess_env import subprocess_env

SKILL = Path(__file__).resolve().parents[1]
ROOT = SKILL.parents[1]
RENDER = '!`python3 -B "${CLAUDE_SKILL_DIR}/scripts/skill_values.py" render`'


class TheHooks(unittest.TestCase):
    def setUp(self):
        self.hooks = json.loads((ROOT / "hooks" / "hooks.json").read_text())["hooks"]

    def test_the_three_events(self):
        self.assertEqual(sorted(self.hooks), ["PreCompact", "SessionStart", "Stop"])

    def test_each_runs_its_adapter_once_from_the_plugin_root(self):
        for event, script in (("Stop", "stop"), ("PreCompact", "precompact"),
                              ("SessionStart", "sessionstart")):
            with self.subTest(event=event):
                entries = [h for group in self.hooks[event] for h in group["hooks"]]
                self.assertEqual(len(entries), 1)
                self.assertEqual(entries[0]["type"], "command")
                self.assertEqual(entries[0]["command"],
                                 'python3 -B "${CLAUDE_PLUGIN_ROOT}/skills/handoff/'
                                 f'adapters/claude/{script}.py" || true')
                self.assertTrue((SKILL / "adapters" / "claude" / f"{script}.py").is_file())
                self.assertLessEqual(entries[0].get("timeout", 30), 30)


class TheSkill(unittest.TestCase):
    def setUp(self):
        self.text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        _, self.front, self.body = self.text.split("---\n", 2)

    def test_the_first_line_after_the_heading_renders_the_values(self):
        lines = [line for line in self.body.splitlines() if line.strip()]
        self.assertEqual(lines[0], "# handoff")
        self.assertEqual(lines[1], RENDER)

    def test_the_frontmatter_grants_exactly_the_values_command(self):
        # A `!` line is not read-only, so a session with no grant of its own
        # denies it and the skill loads without its values.
        command = RENDER[2:-1]
        grants = [line for line in self.front.splitlines()
                  if line.startswith("allowed-tools:")]
        self.assertEqual(grants, [f"allowed-tools: 'Bash({command})'"])

    def test_every_session_argument_is_the_harness_session_id(self):
        sessions = re.findall(r'--session (\S+)', self.body)
        self.assertTrue(sessions)
        self.assertEqual(set(sessions), {'"${CLAUDE_SESSION_ID}"'})

    def test_the_claim_command_hands_claim_a_session_id(self):
        block = re.search(r"^ {4}(python3 -B \S+ claim .*?)\n\n", self.body,
                          re.M | re.S).group(1)
        text = (block.replace("\\\n", " ")
                .replace("${CLAUDE_SESSION_ID}", "s-from-the-harness")
                .replace("${CLAUDE_SKILL_DIR}", str(SKILL)))
        argv = [re.sub(r"^<.*>$", "x", a) for a in shlex.split(text)]
        argv = [a for a in argv if a not in ("slug>", "id>")]
        with tempfile.TemporaryDirectory() as root:
            env = subprocess_env(HANDOFF_STATE_ROOT=root,
                                 HANDOFF_CONFIG=os.path.join(root, "none.json"))
            done = subprocess.run([sys.executable, *argv[2:]], capture_output=True,
                                  text=True, env=env)
            self.assertEqual(done.returncode, 0, done.stderr)
            written = [p.name for p in Path(root).rglob("*") if p.is_file()]
            self.assertTrue(any("s-from-the-harness" in n for n in written), written)

    def test_no_placeholder_is_left(self):
        self.assertNotIn("{" * 2, self.text)

    def test_the_description_names_no_person_and_no_path(self):
        description = self.front.split("description:", 1)[1].split("\nallowed-tools:")[0]
        self.assertIn("the user", description)
        self.assertNotRegex(description, r"[~/]\w")
        self.assertNotRegex(description, r"\b[A-Z][a-z]+'s\b")

    def test_every_value_it_names_is_a_text_key(self):
        import sys
        sys.path.insert(0, str(SKILL / "scripts"))
        import skill_values as sv
        named = set(re.findall(r"`([a-z]+\.[A-Za-z.]+)` in Values", self.body))
        self.assertTrue(named)
        self.assertLessEqual(named, {k for k, _ in sv.TEXT_KEYS})


if __name__ == "__main__":
    unittest.main()
