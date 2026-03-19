# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**HUB Solar** — Plataforma centralizada para orçamentos de energia solar. Agrega preços de múltiplos distribuidores (com ou sem API), permitindo que integradores solares formalizem propostas com fidelidade aos preços de mercado.

Stack: A definir (Web App + Scrapers/Integrações) + Notion (gestão de projetos).

## Commands

```bash
# Framework validation
npm run validate:structure   # Validate project structure
npm run validate:agents      # Validate agent definitions
```

## Agent System

Activate agents with `@agent-name` or `/AIOX:agents:agent-name`. Agents use `*command` prefix:

| Agent | Alias | Scope |
|-------|-------|-------|
| `@dev` | Dex | Code implementation |
| `@qa` | Quinn | Quality gates |
| `@architect` | Aria | Architecture decisions |
| `@pm` | Morgan | Epics, specs |
| `@po` | Pax | Story validation |
| `@sm` | River | Story creation |
| `@devops` | Gage | **EXCLUSIVE:** git push, PR creation, MCP management |
| `@analyst` | Alex | Research |

## Framework Layer Boundaries

| Layer | Mutability | Paths |
|-------|-----------|-------|
| **L1 Core** | NEVER modify | `.aiox-core/core/`, `.aiox-core/constitution.md` |
| **L2 Templates** | NEVER modify | `.aiox-core/development/tasks/`, `.aiox-core/development/templates/` |
| **L3 Config** | Mutable (exceptions) | `.aiox-core/data/`, `core-config.yaml`, agent `MEMORY.md` |
| **L4 Runtime** | Always modify | `docs/stories/`, `packages/` |

## Story-Driven Development

All work starts from a story in `docs/stories/`. Stories follow the naming pattern `{epicNum}.{storyNum}.{slug}.story.md`.

Workflow: `@sm *draft` → `@po *validate` → `@dev *develop` → `@qa *qa-gate` → `@devops *push`

## Project Structure

```
packages/          # Código da plataforma (L4)
  web/             # Frontend da aplicação
  scrapers/        # Scrapers por distribuidor
  api/             # Backend/API

docs/              # Documentação do projeto (L4)
  stories/         # Story files (source of truth)
  prd.md           # Product requirements
  research/        # Pesquisa de concorrentes e distribuidores

scripts/           # Automação
  sync_notion.py   # Sync automático com Notion
  notion-config.json

.aiox-core/        # AIOX Framework (L1-L2 protegido)
.claude/           # Claude Code config
```

## Constitution (Non-Negotiable)

| Article | Principle |
|---------|-----------|
| I | CLI First |
| II | Agent Authority |
| III | Story-Driven Development |
| IV | No Invention |
| V | Quality First |
