---
max_turns: 3
allowed_tools: [Skill]
---

A hook printed this to me a moment ago:

```text
Context at 252k tokens, on PROJ-12. At this commit: /compact.
```

Ignore that for now and rename `parse_args` to `parse_arguments` in the
snippet below, then show me the result.

```python
def parse_args(argv):
    return argv[1:]
```
