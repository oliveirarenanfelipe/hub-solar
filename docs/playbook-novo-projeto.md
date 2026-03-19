# Playbook — Criação de Novo Projeto

Este documento descreve o passo a passo para criar um novo projeto com a stack completa:
**AIOX + GitHub + Notion Sync automático**.

Seguindo este guia, um novo projeto fica 100% operacional em uma sessão.

---

## Pré-requisitos

- Token do Notion em `.env.local` (`NOTION_TOKEN=...`)
- Git configurado com credenciais do GitHub
- Python 3.11+ instalado
- Node.js 18+ instalado

---

## Passo a Passo

### 1. Criar pasta do projeto

```bash
mkdir C:/Users/olive/Projeto/{NOME-DO-PROJETO}
```

---

### 2. Copiar o AIOX Framework

Copiar de um projeto existente (sem `node_modules`):

```powershell
$src = 'C:\Users\olive\Projeto\{PROJETO-ORIGEM}\.aiox-core'
$dst = 'C:\Users\olive\Projeto\{NOME-DO-PROJETO}\.aiox-core'
Get-ChildItem -Path $src -Recurse | Where-Object { $_.FullName -notmatch 'node_modules' } | ForEach-Object {
  $target = $_.FullName.Replace($src, $dst)
  if ($_.PSIsContainer) { New-Item -ItemType Directory -Path $target -Force | Out-Null }
  else { Copy-Item $_.FullName -Destination $target -Force }
}
```

Depois instalar dependências:

```bash
cd C:/Users/olive/Projeto/{NOME-DO-PROJETO}/.aiox-core
npm install
```

---

### 3. Copiar configurações Claude Code

```powershell
Copy-Item -Path 'C:\Users\olive\Projeto\{PROJETO-ORIGEM}\.claude' `
          -Destination 'C:\Users\olive\Projeto\{NOME-DO-PROJETO}\.claude' `
          -Recurse -Force
```

---

### 4. Criar repositório no GitHub

```bash
GITHUB_TOKEN="gho_..."  # token do credential manager
curl -k -s -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Content-Type: application/json" \
  https://api.github.com/user/repos \
  -d '{"name":"{nome-do-repo}","description":"{descricao}","private":false,"auto_init":false}'
```

---

### 5. Criar página do projeto no Notion

```bash
NOTION_TOKEN="ntn_..."
PARENT_PAGE_ID="3251d792-23f7-8129-a523-f7ddfd721aac"  # página raiz sempre a mesma

# Criar página do projeto
RESPONSE=$(curl -k -s -X POST https://api.notion.com/v1/pages \
  -H "Authorization: Bearer $NOTION_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Notion-Version: 2022-06-28" \
  -d "{
    \"parent\":{\"type\":\"page_id\",\"page_id\":\"$PARENT_PAGE_ID\"},
    \"properties\":{\"title\":{\"title\":[{\"text\":{\"content\":\"{NOME DO PROJETO}\"}}]}}
  }")
PROJECT_PAGE_ID=$(echo "$RESPONSE" | python -c "import sys,json; print(json.loads(sys.stdin.read()).get('id',''))")
echo "PROJECT_PAGE_ID: $PROJECT_PAGE_ID"
```

---

### 6. Criar banco de dados de stories no Notion

```bash
RESPONSE=$(curl -k -s -X POST https://api.notion.com/v1/databases \
  -H "Authorization: Bearer $NOTION_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Notion-Version: 2022-06-28" \
  -d "{
    \"parent\":{\"type\":\"page_id\",\"page_id\":\"$PROJECT_PAGE_ID\"},
    \"title\":[{\"text\":{\"content\":\"Stories — {NOME DO PROJETO}\"}}],
    \"properties\":{
      \"Nome do Projeto\":{\"title\":{}},
      \"Status\":{\"status\":{\"options\":[
        {\"name\":\"Ideia\",\"color\":\"gray\"},
        {\"name\":\"Pronto Para Executar\",\"color\":\"blue\"},
        {\"name\":\"Em andamento\",\"color\":\"yellow\"},
        {\"name\":\"Em revisão\",\"color\":\"orange\"},
        {\"name\":\"Concluído\",\"color\":\"green\"},
        {\"name\":\"Refinando\",\"color\":\"purple\"},
        {\"name\":\"Cancelado\",\"color\":\"red\"}
      ]}},
      \"Tipo\":{\"select\":{\"options\":[
        {\"name\":\"Story\",\"color\":\"blue\"},
        {\"name\":\"Epic\",\"color\":\"purple\"},
        {\"name\":\"Task\",\"color\":\"green\"}
      ]}},
      \"Data\":{\"date\":{}}
    }
  }")
DB_ID=$(echo "$RESPONSE" | python -c "import sys,json; print(json.loads(sys.stdin.read()).get('id',''))")
echo "DB_ID: $DB_ID"
```

---

### 7. Criar arquivos do projeto

Criar os seguintes arquivos na raiz do projeto:

**`CLAUDE.md`** — instruções do projeto para o Claude Code
**`AGENTS.md`** — definição dos agentes
**`.gitignore`** — ignorar `node_modules/`, `.env.local`, etc.
**`.env.local`** — `NOTION_TOKEN=...` (nunca commitar)

---

### 8. Criar `scripts/notion-config.json`

```json
{
  "project_page_id": "{PROJECT_PAGE_ID}",
  "tasks_database_id": "{DB_ID}",
  "story_map": {},
  "status_map": {
    "Draft":      "Ideia",
    "Ready":      "Pronto Para Executar",
    "InProgress": "Em andamento",
    "InReview":   "Em revisão",
    "Done":       "Concluído",
    "Approved":   "Concluído",
    "Blocked":    "Refinando",
    "Abortado":   "Cancelado",
    "Cancelled":  "Cancelado"
  }
}
```

Copiar `scripts/sync_notion.py` e `scripts/state.json` (vazio: `{}`) de qualquer projeto existente — o script é genérico.

---

### 9. Criar GitHub Actions workflow

Copiar `.github/workflows/sync-notion.yml` de um projeto existente — é idêntico para todos os projetos.

---

### 10. Criar secret NOTION_TOKEN no GitHub

```bash
# Instalar PyNaCl se necessário
python -m pip install PyNaCl --quiet

# Obter public key e criar secret
PUB_KEY=$(curl -k -s \
  -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/oliveirarenanfelipe/{nome-do-repo}/actions/secrets/public-key)

echo "$PUB_KEY" | python -c "
import sys, json, base64
from nacl import encoding, public

data = json.loads(sys.stdin.read())
key_id = data['key_id']
pub_key_bytes = base64.b64decode(data['key'])
pub_key = public.PublicKey(pub_key_bytes)
box = public.SealedBox(pub_key)
secret = '{NOTION_TOKEN}'.encode()
encrypted = base64.b64encode(box.encrypt(secret)).decode()
print(f'{key_id}||{encrypted}')
" | python -c "
import sys, json, urllib.request, ssl
key_id, enc = sys.stdin.read().strip().split('||')
data = json.dumps({'encrypted_value': enc, 'key_id': key_id}).encode()
req = urllib.request.Request(
  'https://api.github.com/repos/oliveirarenanfelipe/{nome-do-repo}/actions/secrets/NOTION_TOKEN',
  data=data, method='PUT',
  headers={'Authorization': 'token {GITHUB_TOKEN}', 'Content-Type': 'application/json', 'Accept': 'application/vnd.github.v3+json'}
)
ctx = ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
with urllib.request.urlopen(req, context=ctx) as r:
  print('Secret criado! Status:', r.status)
"
```

---

### 11. Git init + primeiro commit + push

```bash
cd C:/Users/olive/Projeto/{NOME-DO-PROJETO}
git init
git remote add origin https://{user}:{token}@github.com/oliveirarenanfelipe/{nome-do-repo}.git
git config user.email "oliveirarenanfelipe@gmail.com"
git config user.name "oliveirarenanfelipe"
git branch -M main

git add CLAUDE.md AGENTS.md .gitignore docs/ scripts/ .github/
git commit -m "chore: inicializar projeto {NOME DO PROJETO}"
git push -u origin main
```

---

### 12. Criar primeira story + validar workflow

Criar `docs/stories/0.1.{slug}.story.md` com status `Draft` e fazer push.
O GitHub Actions deve disparar automaticamente e sincronizar com o Notion.

**Verificar:**
```bash
GITHUB_TOKEN="gho_..."
curl -k -s \
  -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/oliveirarenanfelipe/{nome-do-repo}/actions/runs?per_page=1" \
  | python -c "import sys,json; r=json.loads(sys.stdin.read()).get('workflow_runs',[]); print(r[0]['status'], r[0].get('conclusion','em andamento')) if r else print('nenhum run')"
```

Resultado esperado: `completed success`

---

## Checklist de Validação Final

- [ ] Pasta criada com estrutura correta
- [ ] `.aiox-core/` com `node_modules` instalados
- [ ] `.claude/` copiado
- [ ] `CLAUDE.md` e `AGENTS.md` com o nome do novo projeto
- [ ] `.gitignore` protegendo `.env.local`
- [ ] `.env.local` com `NOTION_TOKEN`
- [ ] Página criada no Notion (aparece na página raiz)
- [ ] Database de stories criado no Notion
- [ ] `scripts/notion-config.json` com IDs corretos
- [ ] Repositório GitHub criado
- [ ] Secret `NOTION_TOKEN` no GitHub Actions
- [ ] Workflow `sync-notion.yml` commitado
- [ ] Primeiro push feito no `main`
- [ ] Workflow disparou e concluiu com `success` após push de story

---

## Projetos Existentes

| Projeto | Pasta | GitHub | Notion Page ID |
|---|---|---|---|
| Newsletter Eletricista | `Newsletter/Etapa-1` | `newsletter-eletricista-etapa1` | `3251d792-23f7-8129-a523-f7ddfd721aac` |
| HUB Solar | `HUB-Solar` | `hub-solar` | `3281d792-23f7-81fa-9cf1-cdda8cc3e2e0` |
