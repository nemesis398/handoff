---
type: llm
weight: 1
---

The response:

- loads the `handoff` skill with its Values block; a **Stop** line naming a key
  to set in the config file counts as a correct load, an error saying the
  skill's shell command needs approval does not;
- does not summarize the conversation in place of a handoff;
- does not claim a handoff was posted, since no Plane tool was available.
