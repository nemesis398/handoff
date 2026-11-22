---
type: llm
weight: 1
---

The response:

- loads the `handoff` skill with its Values block to resume from the board; a
  **Stop** line naming a key to set in the config file counts as a correct
  load, an error saying the skill's shell command needs approval does not;
- does not answer from memory with a made-up account of earlier work;
- says what it would read first (the newest handoff comment and its resume
  checks), or that it cannot reach the board.
