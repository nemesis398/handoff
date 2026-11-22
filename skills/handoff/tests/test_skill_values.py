"""skill_values.py, the one reader of the handoff skill's config file.

What it pins: where the file is looked for, that anything other than a JSON
object reads as no values, that a key of the wrong type or an empty string
counts as not set, the one sentence a missing key produces, and `render`, the
Values block the SKILL.md opens with.
"""
from __future__ import annotations

import contextlib
import io
import json
import subprocess
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import skill_values as sv  # noqa: E402


class Where(unittest.TestCase):
    def test_the_variable_names_the_file(self):
        with mock.patch.dict(os.environ, {"HANDOFF_CONFIG": "/x/values.json"}):
            self.assertEqual(sv.path(), Path("/x/values.json"))

    def test_without_it_the_xdg_config_home(self):
        env = {"XDG_CONFIG_HOME": "/cfg", "HOME": "/home/tester"}
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertEqual(sv.path(), Path("/cfg/handoff/config.json"))

    def test_without_both_the_home_config(self):
        with mock.patch.dict(os.environ, {"HOME": "/home/tester"}, clear=True):
            self.assertEqual(sv.path(), Path("/home/tester/.config/handoff/config.json"))

    def test_an_empty_variable_counts_as_unset(self):
        env = {"HANDOFF_CONFIG": "", "XDG_CONFIG_HOME": "", "HOME": "/h"}
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertEqual(sv.path(), Path("/h/.config/handoff/config.json"))


class Reading(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.file = Path(self.tmp.name) / "values.json"
        patcher = mock.patch.dict(os.environ, {"HANDOFF_CONFIG": str(self.file)})
        patcher.start()
        self.addCleanup(patcher.stop)

    def write(self, text: str) -> None:
        self.file.write_text(text, encoding="utf-8")

    def test_a_missing_file_is_no_values(self):
        self.assertEqual(sv.load(), {})

    def test_malformed_json_is_no_values(self):
        self.write("{not json")
        self.assertEqual(sv.load(), {})

    def test_a_list_is_no_values(self):
        self.write("[1, 2]")
        self.assertEqual(sv.load(), {})

    def test_bytes_that_are_not_utf8_are_no_values(self):
        self.file.write_bytes(b"\xff\xfe{}")
        self.assertEqual(sv.load(), {})

    def test_a_directory_is_no_values(self):
        self.file.mkdir()
        self.assertEqual(sv.load(), {})

    def test_a_dotted_key_walks_the_objects(self):
        self.write(json.dumps({"user": {"name": "Alice"}}))
        self.assertEqual(sv.get("user.name"), "Alice")

    def test_a_missing_key_is_none(self):
        self.write(json.dumps({"user": {}}))
        self.assertIsNone(sv.get("user.name"))
        self.assertIsNone(sv.get("nothing.at.all"))

    def test_a_key_under_a_string_is_none(self):
        self.write(json.dumps({"user": "Alice"}))
        self.assertIsNone(sv.get("user.name"))

    def test_the_wrong_type_is_none(self):
        self.write(json.dumps({"user": {"name": ["Alice"]}, "n": 3, "flag": True}))
        self.assertIsNone(sv.get("user.name"))
        self.assertIsNone(sv.get("n"))
        self.assertIsNone(sv.get("flag", dict))

    def test_an_empty_or_blank_string_is_not_set(self):
        self.write(json.dumps({"a": "", "b": "  \n"}))
        self.assertIsNone(sv.get("a"))
        self.assertIsNone(sv.get("b"))

    def test_objects_and_lists_by_kind(self):
        self.write(json.dumps({"m": {"x": [1]}, "l": ["a"]}))
        self.assertEqual(sv.get("m", dict), {"x": [1]})
        self.assertEqual(sv.get("l", list), ["a"])

    def test_values_can_be_handed_in(self):
        self.assertEqual(sv.get("a.b", values={"a": {"b": "c"}}), "c")

    def test_require_names_the_key(self):
        self.write("{}")
        with self.assertRaises(sv.Missing) as caught:
            sv.require("vault.root")
        self.assertEqual(str(caught.exception),
                         f"set `vault.root` in `{self.file}`")
        self.assertEqual(caught.exception.key, "vault.root")

    def test_require_returns_a_value_that_is_set(self):
        self.write(json.dumps({"vault": {"root": "/v"}}))
        self.assertEqual(sv.require("vault.root"), "/v")

    def test_an_empty_object_or_list_is_not_set(self):
        self.write(json.dumps({"m": {}, "l": []}))
        self.assertIsNone(sv.get("m", dict))
        self.assertIsNone(sv.get("l", list))
        with self.assertRaises(sv.Missing):
            sv.require("m", dict)

    def test_a_huge_file_reads(self):
        self.write(json.dumps({"k": "x" * 2_000_000}))
        self.assertEqual(len(sv.get("k")), 2_000_000)


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "skill_values.py"
FULL = {"user": {"name": "Alice"},
        "handoff": {"workspaces": {"home": {"default": True, "projects": {}}},
                    "assignee": "00000000-0000-0000-0000-00000000000a"}}


class Render(unittest.TestCase):
    """`render` prints the Values block the SKILL.md opens with: one line per
    key of TEXT_KEYS, a stop line for a key the skill needs, an off line for a
    key one step needs. It never fails, whatever the file holds."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.file = Path(self.tmp.name) / "config.json"

    def render(self) -> tuple[int, str, str]:
        env = {"HANDOFF_CONFIG": str(self.file), "PATH": os.environ.get("PATH", ""),
               "PYTHONDONTWRITEBYTECODE": "1"}
        done = subprocess.run([sys.executable, "-B", str(SCRIPT), "render"],
                              capture_output=True, text=True, env=env)
        return done.returncode, done.stdout, done.stderr

    def write(self, values) -> None:
        self.file.write_text(values if isinstance(values, str) else json.dumps(values),
                             encoding="utf-8")

    def stop(self, key: str) -> str:
        return f"**Stop.** Set `{key}` in `{self.file}` before you use this skill."

    def test_the_text_keys_are_the_ones_the_skill_uses(self):
        self.assertEqual(sv.TEXT_KEYS, [("user.name", str), ("handoff.workspaces", dict),
                                        ("handoff.assignee", str)])
        self.assertEqual(list(sv.STEPS), ["handoff.assignee"])

    def test_a_full_file_prints_every_value(self):
        self.write(FULL)
        code, out, err = self.render()
        self.assertEqual(code, 0, err)
        self.assertEqual(out.splitlines(), [
            "## Values",
            "",
            "- `user.name`: Alice",
            '- `handoff.workspaces`: {"home":{"default":true,"projects":{}}}',
            "- `handoff.assignee`: 00000000-0000-0000-0000-00000000000a",
        ])
        self.assertNotIn("Stop", out)

    def test_a_missing_key_prints_the_stop_line_in_its_place(self):
        values = json.loads(json.dumps(FULL))
        del values["handoff"]["workspaces"]
        self.write(values)
        code, out, _ = self.render()
        self.assertEqual(code, 0)
        self.assertIn(self.stop("handoff.workspaces"), out.splitlines())
        self.assertNotIn("`handoff.workspaces`: ", out)
        self.assertIn("- `handoff.assignee`: ", out)

    def test_a_missing_name_stops_nothing_and_prints_nothing(self):
        values = json.loads(json.dumps(FULL))
        del values["user"]
        self.write(values)
        code, out, _ = self.render()
        self.assertEqual(code, 0)
        self.assertNotIn("user.name", out)
        self.assertNotIn("**Stop.**", out)
        self.assertIn("- `handoff.workspaces`: ", out)

    def test_an_empty_list_layout_is_a_missing_one(self):
        values = json.loads(json.dumps(FULL))
        values["handoff"]["workspaces"] = []
        self.write(values)
        _, out, _ = self.render()
        self.assertIn(self.stop("handoff.workspaces"), out)

    def test_a_mistyped_key_is_a_missing_one(self):
        values = json.loads(json.dumps(FULL))
        values["handoff"]["workspaces"] = ["home"]
        self.write(values)
        _, out, _ = self.render()
        self.assertIn(self.stop("handoff.workspaces"), out)

    def test_an_empty_layout_is_a_missing_one(self):
        values = json.loads(json.dumps(FULL))
        values["handoff"]["workspaces"] = {}
        self.write(values)
        _, out, _ = self.render()
        self.assertIn(self.stop("handoff.workspaces"), out)

    def test_a_step_key_turns_off_its_step_alone(self):
        values = json.loads(json.dumps(FULL))
        del values["handoff"]["assignee"]
        self.write(values)
        code, out, _ = self.render()
        self.assertEqual(code, 0)
        step = sv.STEPS["handoff.assignee"]
        self.assertEqual(step["step"], "assign")
        self.assertIn(f"**Step assign is off** until `handoff.assignee` is set in "
                      f"`{self.file}`: {step['without']}.", out.splitlines())
        self.assertNotIn("**Stop.**", out)

    def test_a_missing_file_is_every_key_missing(self):
        code, out, _ = self.render()
        self.assertEqual(code, 0)
        self.assertNotIn("user.name", out)
        self.assertIn(self.stop("handoff.workspaces"), out)
        self.assertIn("**Step assign is off**", out)

    def test_an_empty_file_is_every_key_missing(self):
        self.write("")
        code, out, _ = self.render()
        self.assertEqual(code, 0)
        self.assertNotIn("user.name", out)
        self.assertIn(self.stop("handoff.workspaces"), out)

    def test_a_malformed_file_is_every_key_missing(self):
        self.write("{not json")
        code, out, _ = self.render()
        self.assertEqual(code, 0)
        self.assertNotIn("user.name", out)
        self.assertIn(self.stop("handoff.workspaces"), out)

    def test_render_in_process_never_raises(self):
        with mock.patch.dict(os.environ, {"HANDOFF_CONFIG": str(self.file)}):
            self.file.mkdir()
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                self.assertEqual(sv.main(["render"]), 0)
        self.assertIn("## Values", buf.getvalue())

    def test_a_failure_inside_render_prints_a_stop_line(self):
        buf = io.StringIO()
        with mock.patch.object(sv, "render", side_effect=RuntimeError("boom")), \
                contextlib.redirect_stdout(buf):
            self.assertEqual(sv.main(["render"]), 0)
        self.assertIn("**Stop.**", buf.getvalue())
        self.assertIn("boom", buf.getvalue())

    def test_a_usage_error_exits_two(self):
        env = {"HANDOFF_CONFIG": str(self.file), "PATH": os.environ.get("PATH", "")}
        for args in ([], ["bogus"], ["render", "extra"]):
            done = subprocess.run([sys.executable, "-B", str(SCRIPT), *args],
                                  capture_output=True, text=True, env=env)
            self.assertEqual(done.returncode, 2, args)
            self.assertIn("usage", done.stderr)
            self.assertEqual(done.stdout, "")


if __name__ == "__main__":
    unittest.main()
