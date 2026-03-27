#!/usr/bin/env python3
"""
setup_notion.py — Cria projeto HUB Solar Etapa 2 no Notion e popula notion-config.json.

Uso (uma vez só):
  NOTION_TOKEN=ntn_xxx python etapa-2/scripts/setup_notion.py

O que faz:
  1. Cria página "HUB Solar — Etapa 2" no Notion (página raiz ou subpágina)
  2. Cria database "Tasks" dentro dela
  3. Salva os IDs em etapa-2/scripts/notion-config.json
"""

import os
import json
import sys
from pathlib import Path
import urllib.request
import urllib.error

SCRIPT_DIR  = Path(__file__).parent
CONFIG_FILE = SCRIPT_DIR / "notion-config.json"

STATUS_MAP = {
    "Draft":      "Ideia",
    "Ready":      "Pronto Para Executar",
    "InProgress": "Em andamento",
    "InReview":   "Em revisão",
    "Done":       "Concluído",
    "Approved":   "Concluído",
    "Blocked":    "Refinando",
    "Abortado":   "Cancelado",
    "Cancelled":  "Cancelado",
}

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
        err = e.read().decode()[:500]
        print(f"  [ERRO] {method} {path}: {e.code} — {err}")
        return None

def create_project_page(token, parent_page_id=None):
    """Cria página do projeto. Se parent_page_id, cria como subpágina; senão, cria na raiz do workspace."""
    if parent_page_id:
        parent = {"type": "page_id", "page_id": parent_page_id}
    else:
        parent = {"type": "workspace", "workspace": True}

    data = {
        "parent": parent,
        "properties": {
            "title": {
                "title": [{"type": "text", "text": {"content": "HUB Solar — Etapa 2"}}]
            }
        },
        "children": [
            {
                "type": "heading_1",
                "heading_1": {
                    "rich_text": [{"type": "text", "text": {"content": "HUB Solar — Etapa 2"}}]
                }
            },
            {
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": "Build phase: engines de coleta, Supabase, módulo de cotação. 9 distribuidores validados prontos para produção."}}]
                }
            }
        ]
    }
    resp = notion_request(token, "POST", "/pages", data)
    if resp and "id" in resp:
        return resp["id"]
    return None

def create_tasks_database(token, project_page_id):
    """Cria database 'Tasks' dentro da página do projeto."""
    data = {
        "parent": {"type": "page_id", "page_id": project_page_id},
        "title": [{"type": "text", "text": {"content": "Tasks"}}],
        "properties": {
            "Name": {"title": {}},
            "Status": {
                "status": {
                    "options": [
                        {"name": "Ideia",              "color": "gray"},
                        {"name": "Pronto Para Executar","color": "blue"},
                        {"name": "Em andamento",        "color": "yellow"},
                        {"name": "Em revisão",          "color": "orange"},
                        {"name": "Concluído",           "color": "green"},
                        {"name": "Refinando",           "color": "purple"},
                        {"name": "Cancelado",           "color": "red"},
                    ],
                    "groups": [
                        {"name": "To-do",       "color": "gray",   "option_ids": []},
                        {"name": "In progress", "color": "yellow", "option_ids": []},
                        {"name": "Complete",    "color": "green",  "option_ids": []},
                    ]
                }
            },
            "Epic": {"select": {
                "options": [
                    {"name": "1. Infraestrutura", "color": "blue"},
                    {"name": "2. Pendências",     "color": "orange"},
                    {"name": "3. Módulo Cotação", "color": "green"},
                ]
            }},
        }
    }
    resp = notion_request(token, "POST", "/databases", data)
    if resp and "id" in resp:
        return resp["id"]
    return None

def main():
    token = os.environ.get("NOTION_TOKEN", "").strip()
    if not token:
        # Tenta ler do .env na raiz do projeto
        env_file = SCRIPT_DIR.parent.parent / ".env"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if line.startswith("NOTION_TOKEN="):
                    token = line.split("=", 1)[1].strip()
                    break

    if not token:
        print("ERRO: NOTION_TOKEN não encontrado. Defina via variável de ambiente ou .env")
        sys.exit(1)

    # ID da página atual do HUB Solar (etapa-1) para criar etapa-2 como subpágina
    # Se não quiser subpágina, deixar None
    PARENT_PAGE_ID = "3281d792-23f7-81fa-9cf1-cdda8cc3e2e0"  # projeto HUB Solar etapa-1

    print("Criando página 'HUB Solar — Etapa 2' no Notion...")
    project_id = create_project_page(token, PARENT_PAGE_ID)
    if not project_id:
        print("Falhou ao criar página. Tentando na raiz do workspace...")
        project_id = create_project_page(token, None)
    if not project_id:
        print("ERRO: não foi possível criar a página do projeto.")
        sys.exit(1)
    print(f"  Página criada: {project_id}")

    print("Criando database 'Tasks'...")
    tasks_db_id = create_tasks_database(token, project_id)
    if not tasks_db_id:
        print("ERRO: não foi possível criar o database.")
        sys.exit(1)
    print(f"  Database criado: {tasks_db_id}")

    config = {
        "project_page_id": project_id,
        "tasks_database_id": tasks_db_id,
        "story_map": {},
        "status_map": STATUS_MAP
    }
    CONFIG_FILE.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nConfiguração salva em {CONFIG_FILE}")
    print("\nPróximo passo: python etapa-2/scripts/sync_notion.py")

if __name__ == "__main__":
    main()
