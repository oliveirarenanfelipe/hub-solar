#!/usr/bin/env python3
"""
sync_notion.py — Sincroniza stories locais com o Notion automaticamente.

Uso:
  GitHub Actions: roda automaticamente a cada push em docs/stories/
  Local:          NOTION_TOKEN=xxx python scripts/sync_notion.py

Config do projeto: scripts/notion-config.json
Estado anterior:  scripts/state.json (commitado automaticamente pelo bot)

Custo: $0 — sem IA, apenas chamadas diretas à API do Notion.
Multi-projeto: cada projeto tem seu proprio notion-config.json.
"""

import os
import re
import json
import sys
from datetime import date
from pathlib import Path
import urllib.request
import urllib.error

# ─── PATHS ────────────────────────────────────────────────────────────────────

SCRIPT_DIR  = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
CONFIG_FILE = SCRIPT_DIR / "notion-config.json"
STATE_FILE  = SCRIPT_DIR / "state.json"
STORIES_DIR = PROJECT_DIR / "docs" / "stories"

# ─── LOAD CONFIG ──────────────────────────────────────────────────────────────

def load_config() -> dict:
    if not CONFIG_FILE.exists():
        print(f"ERRO: {CONFIG_FILE} nao encontrado.")
        sys.exit(1)
    return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))

# ─── NOTION API ───────────────────────────────────────────────────────────────

def notion_request(token, method, path, data=None):
    url = f"https://api.notion.com/v1{path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"  [ERRO] {method} {path}: {e.code} — {e.read().decode()[:300]}")
        return None

def update_status(token, page_id, status_name):
    notion_request(token, "PATCH", f"/pages/{page_id}", {
        "properties": {"Status": {"status": {"name": status_name}}}
    })

def append_log(token, page_id, text):
    notion_request(token, "PATCH", f"/blocks/{page_id}/children", {
        "children": [{
            "type": "bulleted_list_item",
            "bulleted_list_item": {
                "rich_text": [{"type": "text", "text": {"content": text}}]
            }
        }]
    })

# ─── STORY PARSER ─────────────────────────────────────────────────────────────

def parse_story(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")

    status_match = re.search(r"^## Status\s*\n(\w+)", text, re.MULTILINE)
    status = status_match.group(1).strip() if status_match else "Unknown"

    completed = len(re.findall(r"- \[x\]", text, re.IGNORECASE))
    total     = len(re.findall(r"- \[[ x]\]", text, re.IGNORECASE))

    changelog_match = re.search(
        r"\|\s*(\d{4}-\d{2}-\d{2})\s*\|[^|]*\|\s*([^|]+?)\s*\|",
        text
    )
    last_date = changelog_match.group(1) if changelog_match else ""
    last_desc = changelog_match.group(2).strip() if changelog_match else ""

    title_match = re.search(r"^# (.+)$", text, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else path.stem

    return {
        "status":    status,
        "completed": completed,
        "total":     total,
        "last_date": last_date,
        "last_desc": last_desc,
        "title":     title,
    }

def extract_story_id(filename: str) -> str:
    m = re.match(r"^(\d+\.\d+)\.", filename)
    return m.group(1) if m else ""

# ─── STATE ────────────────────────────────────────────────────────────────────

def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {}

def save_state(state: dict):
    STATE_FILE.write_text(
        json.dumps(state, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

# ─── SAVE CONFIG ──────────────────────────────────────────────────────────────

def save_config(config: dict):
    CONFIG_FILE.write_text(
        json.dumps(config, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

def create_page(token, database_id, title, status_name="Ideia") -> str:
    """Cria uma entrada no banco de dados Tasks e retorna o page_id gerado."""
    resp = notion_request(token, "POST", "/pages", {
        "parent": {"database_id": database_id},
        "properties": {
            "title": {
                "title": [{"type": "text", "text": {"content": title}}]
            },
            "Status": {"status": {"name": status_name}}
        }
    })
    if resp and "id" in resp:
        return resp["id"]
    return ""

# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    token = os.environ.get("NOTION_TOKEN", "").strip()
    if not token:
        print("ERRO: variavel NOTION_TOKEN nao definida.")
        print("  Local:   export NOTION_TOKEN=ntn_xxx")
        print("  Actions: adicione NOTION_TOKEN em Settings > Secrets")
        sys.exit(1)

    config         = load_config()
    story_map      = config["story_map"]
    status_map     = config["status_map"]
    project_id     = config["project_page_id"]
    tasks_db_id    = config.get("tasks_database_id", "")
    today          = date.today().isoformat()

    state   = load_state()
    changed = []
    config_updated = False

    if not tasks_db_id:
        print("ERRO: tasks_database_id nao configurado em notion-config.json")
        sys.exit(1)

    print(f"Verificando stories em {STORIES_DIR}...")

    for story_file in sorted(STORIES_DIR.glob("*.story.md")):
        story_id = extract_story_id(story_file.name)
        if not story_id:
            continue

        current = parse_story(story_file)

        # Auto-criar página no Notion se story_id for novo ou ainda sem page_id
        if story_id not in story_map or not story_map.get(story_id):
            print(f"  [{story_id}] Pagina nao encontrada — criando no Notion...")
            notion_status_name = status_map.get(current["status"], "Ideia")
            new_page_id = create_page(token, tasks_db_id, current["title"], notion_status_name)
            if new_page_id:
                story_map[story_id] = new_page_id
                config_updated = True
                print(f"  [{story_id}] Pagina criada: {new_page_id}")
            else:
                print(f"  [{story_id}] ERRO ao criar pagina — pulando.")
                continue

        previous = state.get(story_id, {})

        status_changed   = current["status"]    != previous.get("status")
        progress_changed = current["completed"] != previous.get("completed")

        if not status_changed and not progress_changed:
            continue

        page_id            = story_map[story_id]
        notion_status_name = status_map.get(current["status"], current["status"])

        prev_status = previous.get("status", "novo")
        print(f"  [{story_id}] {prev_status} -> {current['status']} | {current['completed']}/{current['total']} tasks")

        if status_changed:
            update_status(token, page_id, notion_status_name)

        log = f"{today}: {current['status']} | {current['completed']}/{current['total']} tasks"
        if current["last_desc"]:
            log += f" — {current['last_desc']}"
        append_log(token, page_id, log)

        changed.append(f"{story_id} ({current['status']})")

        state[story_id] = {
            "status":    current["status"],
            "completed": current["completed"],
            "last_date": current["last_date"],
        }

    if config_updated:
        save_config(config)
        print(f"\nnotion-config.json atualizado com novos page_ids.")

    if changed:
        summary = f"{today}: Sync automatico — {', '.join(changed)}"
        append_log(token, project_id, summary)
        print(f"\nNotion atualizado: {len(changed)} story(ies) sincronizadas.")
    else:
        print("Nenhuma alteracao detectada. Notion ja esta em dia.")

    save_state(state)

if __name__ == "__main__":
    main()
