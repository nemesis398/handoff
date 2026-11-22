# Changelog

## 0.1.0

- The handoff skill as a plugin of its own: the skill, its scripts and tests,
  and the three hooks (`SessionStart`, `Stop`, `PreCompact`) in
  `hooks/hooks.json`.
- Values come from `HANDOFF_CONFIG`, else
  `${XDG_CONFIG_HOME:-~/.config}/handoff/config.json`, and the SKILL.md opens
  with them through `skill_values.py render`.
- New key `handoff.assignee`: the Plane member every new item is assigned to.
  Without it the assign step is off and items are created unassigned.
- A missing, empty or malformed config file never fails a session: the
  `SessionStart` hook injects nothing and names the key and the file in one
  line on stderr; `Stop` and `PreCompact` need no key.
