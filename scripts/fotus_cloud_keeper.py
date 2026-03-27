"""
Fotus Solar — Cloud Keeper (GitHub Actions)
============================================
Roda a cada 45 min no GitHub Actions.

Fluxo:
  1. Lê token + offset do Gist
  2. Verifica mensagens novas no Telegram — se você mandou um token, usa ele
  3. Se token válido: renova via API Fotus e salva no Gist
  4. Se token expirado e nenhum novo chegou: alerta Telegram pedindo o token

Intervenção manual: basta mandar o accessToken no chat do @hubsolar_bot.
De qualquer lugar, qualquer dispositivo.
"""

import os, sys, json, requests, base64, time
from datetime import datetime, timezone

BASE_FOTUS = "https://api-d0983.cloud.solaryum.com.br"


def log(msg):
    print(f"{datetime.now().strftime('%H:%M:%S')}  {msg}", flush=True)


# ── Telegram ────────────────────────────────────────────────────────────────

def tg_send(msg: str, urgente=False):
    bot   = os.environ.get("TELEGRAM_TOKEN")
    chat  = os.environ.get("TELEGRAM_CHAT_ID")
    if not bot or not chat:
        return
    prefix = "🔴" if urgente else "✅"
    try:
        requests.post(
            f"https://api.telegram.org/bot{bot}/sendMessage",
            json={"chat_id": chat, "text": f"{prefix} *HUB Solar*\n\n{msg}", "parse_mode": "Markdown"},
            timeout=10,
        )
    except Exception:
        pass


def tg_check_novo_token(offset: int) -> tuple[str | None, int]:
    """
    Verifica mensagens novas no Telegram.
    Se encontrar uma que começa com 'eyJ' (JWT), retorna o token e o novo offset.
    """
    bot  = os.environ.get("TELEGRAM_TOKEN")
    chat = os.environ.get("TELEGRAM_CHAT_ID")
    if not bot or not chat:
        return None, offset
    try:
        r = requests.get(
            f"https://api.telegram.org/bot{bot}/getUpdates",
            params={"offset": offset, "limit": 20, "timeout": 5},
            timeout=15,
        )
        updates = r.json().get("result", [])
        novo_token = None
        novo_offset = offset
        for u in updates:
            novo_offset = u["update_id"] + 1
            texto = u.get("message", {}).get("text", "").strip()
            if texto.startswith("eyJ") and len(texto) > 100:
                novo_token = texto
                log(f"✓ Token recebido via Telegram (update {u['update_id']})")
        return novo_token, novo_offset
    except Exception as e:
        log(f"Erro ao verificar Telegram: {e}")
        return None, offset


# ── Gist ────────────────────────────────────────────────────────────────────

def gist_ler(pat: str, gist_id: str) -> dict:
    r = requests.get(
        f"https://api.github.com/gists/{gist_id}",
        headers={"Authorization": f"Bearer {pat}", "Accept": "application/vnd.github+json"},
        timeout=15,
    )
    r.raise_for_status()
    return json.loads(r.json()["files"]["fotus_token.json"]["content"])


def gist_salvar(pat: str, gist_id: str, data: dict):
    requests.patch(
        f"https://api.github.com/gists/{gist_id}",
        headers={"Authorization": f"Bearer {pat}", "Accept": "application/vnd.github+json"},
        json={"files": {"fotus_token.json": {"content": json.dumps(data, indent=2)}}},
        timeout=15,
    ).raise_for_status()


# ── Fotus ───────────────────────────────────────────────────────────────────

def minutos_restantes(token: str) -> float:
    try:
        part = token.split(".")[1]
        part += "=" * (4 - len(part) % 4)
        payload = json.loads(base64.b64decode(part))
        return (payload.get("exp", 0) - time.time()) / 60
    except Exception:
        return -1


def refresh_token(token: str) -> tuple[str | None, dict]:
    try:
        r = requests.get(
            BASE_FOTUS + "/api/Autenticacao/RenovarAcesso",
            headers={
                "Authorization": f"Bearer {token}",
                "Origin": "https://app.fotus.com.br",
                "Referer": "https://app.fotus.com.br/",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            },
            timeout=15,
        )
        if r.status_code == 200:
            data = r.json()
            return data.get("accessToken") or data.get("token"), data
        log(f"Refresh HTTP {r.status_code}: {r.text[:100]}")
        return None, {}
    except Exception as e:
        log(f"Erro refresh: {e}")
        return None, {}


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    pat     = os.environ.get("GITHUB_PAT")
    gist_id = os.environ.get("GIST_ID")
    if not pat or not gist_id:
        log("ERRO: GITHUB_PAT ou GIST_ID não configurados.")
        sys.exit(1)

    log("=== Fotus Cloud Keeper ===")

    # 1. Ler estado do Gist
    try:
        data = gist_ler(pat, gist_id)
    except Exception as e:
        log(f"Erro ao ler Gist: {e}")
        tg_send(f"Cloud Keeper: erro ao ler Gist.\n`{e}`", urgente=True)
        sys.exit(1)

    token  = data.get("accessToken") or data.get("token")
    offset = data.get("telegram_offset", 0)
    mins   = minutos_restantes(token)
    log(f"Token atual: {mins:.1f} min restantes")

    # 2. Verificar se chegou token novo via Telegram
    novo_token_tg, novo_offset = tg_check_novo_token(offset)
    if novo_token_tg:
        token = novo_token_tg
        mins  = minutos_restantes(token)
        log(f"Usando token recebido via Telegram. Válido por {mins:.0f} min.")
        tg_send("Token recebido e aceito! Sistema voltou automaticamente. ✅")

    # 3. Se token ainda expirado (não chegou nenhum novo)
    if mins <= 0:
        log("Token EXPIRADO. Aguardando token via Telegram.")
        tg_send(
            "Fotus: token *expirado* ☠️\n\n"
            "Mande o token aqui neste chat para reativar.\n\n"
            "Como obter:\n"
            "1. Acesse app.fotus.com.br (Opera ou celular)\n"
            "2. F12 → Application → Local Storage\n"
            "3. Copie o valor de `accessToken`\n"
            "4. Cole aqui\n\n"
            "Sistema volta automaticamente em até 45 min.",
            urgente=True,
        )
        # Salvar offset atualizado mesmo sem token novo
        data["telegram_offset"] = novo_offset
        gist_salvar(pat, gist_id, data)
        sys.exit(1)

    # 4. Renovar token via API
    new_token, extra = refresh_token(token)
    if not new_token:
        log("Refresh falhou.")
        tg_send("Fotus: refresh falhou. Tentando na próxima execução (45 min).")
        sys.exit(1)

    new_mins = minutos_restantes(new_token)
    new_data = {
        "accessToken": new_token,
        "telegram_offset": novo_offset,
    }
    if "expirationDate" in extra:
        new_data["expirationDate"] = extra["expirationDate"]
    if "expiresIn" in extra:
        new_data["expiresIn"] = extra["expiresIn"]

    gist_salvar(pat, gist_id, new_data)
    log(f"✓ Token renovado. Novo prazo: {new_mins:.0f} min")


if __name__ == "__main__":
    main()
