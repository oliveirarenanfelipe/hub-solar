"""
Fotus Solar — Cloud Keeper (GitHub Actions)
============================================
Lê o token do Gist privado, renova via API Fotus, salva de volta no Gist.
Roda a cada 45 min no GitHub Actions — mantém o token vivo 24/7, PC desligado ou não.

Variáveis de ambiente necessárias (GitHub Actions secrets):
  GITHUB_PAT   — Personal Access Token com escopo gist
  GIST_ID      — ID do gist privado
  TELEGRAM_TOKEN / TELEGRAM_CHAT_ID — para alertas
"""

import os, sys, json, requests, base64, time
from datetime import datetime, timezone

BASE_FOTUS = "https://api-d0983.cloud.solaryum.com.br"

def log(msg):
    print(f"{datetime.now().strftime('%H:%M:%S')}  {msg}", flush=True)


def telegram_alert(msg: str, urgente=False):
    token = os.environ.get("TELEGRAM_TOKEN")
    chat  = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        return
    prefix = "🔴" if urgente else "🟡"
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat, "text": f"{prefix} *HUB Solar*\n\n{msg}", "parse_mode": "Markdown"},
            timeout=10,
        )
    except Exception:
        pass


def ler_token_gist(pat: str, gist_id: str) -> dict:
    r = requests.get(
        f"https://api.github.com/gists/{gist_id}",
        headers={"Authorization": f"Bearer {pat}", "Accept": "application/vnd.github+json"},
        timeout=15,
    )
    r.raise_for_status()
    content = r.json()["files"]["fotus_token.json"]["content"]
    return json.loads(content)


def salvar_token_gist(pat: str, gist_id: str, data: dict):
    requests.patch(
        f"https://api.github.com/gists/{gist_id}",
        headers={"Authorization": f"Bearer {pat}", "Accept": "application/vnd.github+json"},
        json={"files": {"fotus_token.json": {"content": json.dumps(data, indent=2)}}},
        timeout=15,
    ).raise_for_status()


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
            new_token = data.get("accessToken") or data.get("token")
            return new_token, data
        log(f"Refresh HTTP {r.status_code}: {r.text[:100]}")
        return None, {}
    except Exception as e:
        log(f"Erro refresh: {e}")
        return None, {}


def main():
    pat     = os.environ.get("GITHUB_PAT")
    gist_id = os.environ.get("GIST_ID")

    if not pat or not gist_id:
        log("ERRO: GITHUB_PAT ou GIST_ID não configurados.")
        sys.exit(1)

    log("=== Fotus Cloud Keeper ===")

    # Ler token atual do Gist
    try:
        data = ler_token_gist(pat, gist_id)
        token = data.get("accessToken") or data.get("token")
    except Exception as e:
        log(f"Erro ao ler Gist: {e}")
        telegram_alert(f"Cloud Keeper: erro ao ler Gist.\n`{e}`", urgente=True)
        sys.exit(1)

    mins = minutos_restantes(token)
    log(f"Token atual: {mins:.1f} min restantes")

    if mins <= 0:
        log("Token EXPIRADO no Gist.")
        telegram_alert(
            "Fotus: token *expirado* no Gist ☠️\n\n"
            "Abra o Opera, acesse app.fotus.com.br, pressione F12\n"
            "→ Application → Local Storage → copie `accessToken`\n\n"
            "Depois rode: `python scripts/fotus_set_token.py`\n"
            "e cole o token quando pedido.",
            urgente=True
        )
        sys.exit(1)

    # Renovar
    new_token, extra = refresh_token(token)
    if not new_token:
        log("Refresh falhou.")
        telegram_alert("Fotus Cloud Keeper: refresh falhou. Verificando próxima execução.", urgente=False)
        sys.exit(1)

    new_mins = minutos_restantes(new_token)
    new_data = {"accessToken": new_token}
    if "expirationDate" in extra:
        new_data["expirationDate"] = extra["expirationDate"]
    if "expiresIn" in extra:
        new_data["expiresIn"] = extra["expiresIn"]

    salvar_token_gist(pat, gist_id, new_data)
    log(f"✓ Token renovado e salvo no Gist. Novo prazo: {new_mins:.0f} min")


if __name__ == "__main__":
    main()
