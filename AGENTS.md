# handoff: agent rules

handoff is a public Claude Code plugin. Keep it that way.

- **Public boundary.** Nothing private or local goes into the tree or
  its history: no names, private hostnames, paths, Plane ids or project names.
  Descriptions say "the user". Values come only from `HANDOFF_CONFIG` or
  `${XDG_CONFIG_HOME:-~/.config}/handoff/config.json`, through
  `skills/handoff/scripts/skill_values.py`.
- **Hooks never fail a session.** Every adapter exits 0 whatever happens, every
  hook command ends in `|| true`, and a missing key stops only what needs it.
- **Tests.** `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s skills/handoff/tests`
  from the repository root. Nothing writes `__pycache__`.
- **Never call the Plane API from a test.** The tests stub the transport and
  point the gateway at an unreachable address.
- **Em dash.** None in any file. CI fails on one.
- **Commits.** Conventional Commits, signed.
- **Checks before a commit.** The tests, `claude plugin validate .`,
  markdownlint, and the em-dash check.
