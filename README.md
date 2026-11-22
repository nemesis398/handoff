# handoff

A [Claude Code](https://claude.com/claude-code) skill that writes and resumes
session handoffs on a [Plane](https://plane.so) board. The goal is a parent
work item, the next steps are its sub-items, and the state, the files, the
changes, the dead ends and the resume checks are one comment on the parent.

A handoff is not a summary of the conversation. It records where the work
stands, grounded in the output of `git status` and the tests, so that a session
with no memory of this one can pick it up in its first minute.

## What it does

- **Writes a handoff** when you say handoff, wrap up, save state or park this:
  the goal, one sub-item per next step matched by exact title, and one marked
  comment with the rest.
- **Resumes one.** The `SessionStart` hook shows the open items of the
  directory's project, the stream this session claimed, and after a compaction
  the newest handoff comment.
- **Advises when to compact.** From 200k tokens the `Stop` hook tells you, at
  the first natural break in the work, whether to `/compact`, hand off and
  compact, hand off and `/clear`, or `/clear`. The advice is addressed to you,
  never to the model.

## Install

```text
/plugin marketplace add nemesis398/handoff
/plugin install handoff@handoff
```

The plugin registers its three hooks itself (`hooks/hooks.json`). Each one ends
in `|| true`, so a missing or broken script never blocks a prompt.

## What it needs

- **`python3`** on the `PATH`.
- **Plane MCP tools in the session** for writing. The skill creates and updates
  the items and posts the comment through the Plane MCP server connected to
  your session; the plugin brings none of its own.
- **A gateway for the hooks**, named by `plane.mcpUrl` (or `PLANE_MCP_URL`), and
  the Plane token in `PLANE_API_TOKEN`. The hooks only read the board, and
  they expect a stateless HTTP MCP endpoint: each read is one JSON-RPC
  `tools/call` POST with the headers `Authorization: Bearer <token>` and
  `x-workspace-slug: <workspace>`, to the tools `state`, `workitem` and
  `workitem_comment`, each taking an `action` argument such as `list`.
- **A large context window** for the compaction advice. Its bands, 200k and
  400k tokens, are tuned for auto-compaction at about 487k, which is what a
  500k window leaves. `HANDOFF_SOFT_TOKENS` and `HANDOFF_HARD_TOKENS` move
  them for a smaller window.

The run state lives in `~/.local/state/agent-handoff/`: the stream each
session claimed and the advisor's marks. It is per machine and never synced.

## Configure

The values live in one JSON file, the one `HANDOFF_CONFIG` names, else
`${XDG_CONFIG_HOME:-~/.config}/handoff/config.json`. It holds no secret.

```json
{
  "user": { "name": "Alice" },
  "plane": { "mcpUrl": "https://plane.example.org/mcp" },
  "handoff": {
    "assignee": "00000000-0000-0000-0000-000000000000",
    "workspaces": {
      "home": {
        "default": true,
        "projects": {
          "NOTES": {
            "id": "00000000-0000-0000-0000-000000000000",
            "name": "Notes",
            "dirs": ["/home/alice/Notes"]
          }
        }
      }
    }
  }
}
```

| Key | Type | What it is |
| --- | --- | --- |
| `user.name` | string | how the skill names the user; optional, shown only when set |
| `handoff.workspaces` | object | the board layout: workspaces, their projects, and the directories each project is the default for; `default: true` marks the workspace `claim` takes without `--workspace` |
| `handoff.assignee` | string, a Plane member id | the member every new item is assigned to; without it the assign step is off and items are created unassigned |
| `plane.mcpUrl` | string, a URL | Plane's MCP gateway; `PLANE_MCP_URL` wins over it |

The skill opens with these values. A key it needs that is not set tells the
model to stop and names the key and the file; a key one step needs turns off
that step alone. A missing, empty or malformed file is the same as every key
missing, and never fails a session: the `SessionStart` hook then injects
nothing and says on stderr which key to set where.

`HANDOFF_DISABLED=1` silences every hook for a session. A repository that keeps
its own handoffs opts out with a `handoff.json` marker in its `.claude`
directory that names `project` as the owner.

## Tests

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s skills/handoff/tests
```

They never reach Plane: the transport is stubbed and the gateway points at an
unreachable address. `evals/` holds trigger cases for `claude plugin eval`,
which run against a model on your own account. `--allow-tools` lets the skill's
values command run inside the eval sandbox, and `--no-publish` keeps the report
on your machine instead of uploading it:

```sh
claude plugin eval . --runs 3 --allow-tools 'Bash(python3:*)' --no-publish
```

CI runs the tests, checks the manifests and the Markdown, and that no em dash
slipped in.

## License

[MIT](LICENSE)
