---
type: llm
weight: 1
---

The response:

- loads the `handoff` skill with its Values block; a **Stop** line naming a key
  to set in the config file counts as a correct load, an error saying the
  skill's shell command needs approval does not;
- treats "wrap up", "save state" and "park this" as a request for a handoff,
  not as a request to stop silently;
- does not invent a work item, an identifier or a commit it did not see.
