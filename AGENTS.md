# AGENTS.md — HUB Solar

Agent definitions for Codex CLI and other AI assistants.

## Available Agents

| Agent | Persona | Activate |
|-------|---------|---------|
| @aiox-master | AIOX Master | `/AIOX:agents:aiox-master` |
| @dev | Dex | `/AIOX:agents:dev` |
| @qa | Quinn | `/AIOX:agents:qa` |
| @architect | Aria | `/AIOX:agents:architect` |
| @pm | Morgan | `/AIOX:agents:pm` |
| @po | Pax | `/AIOX:agents:po` |
| @sm | River | `/AIOX:agents:sm` |
| @devops | Gage | `/AIOX:agents:devops` |
| @analyst | Alex | `/AIOX:agents:analyst` |

## Story Workflow

```
@sm *draft → @po *validate → @dev *develop → @qa *qa-gate → @devops *push
```

## Project Stories Location

`docs/stories/` — source of truth for all development work.
