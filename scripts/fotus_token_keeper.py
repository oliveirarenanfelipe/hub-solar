"""
Fotus Solar — Token Keeper
==========================
Mantém o token Fotus sempre válido:
  1. Tenta renovar via /api/Autenticacao/RenovarAcesso (rápido, sem browser)
  2. Se falhar: tenta login automático via perfil Opera GX
  3. Se falhar: envia alerta Telegram para login manual e aguarda token novo

Uso:
  python scripts/fotus_token_keeper.py          # loop contínuo (30 min)
  python scripts/fotus_token_keeper.py --once   # renova uma vez e sai
  python scripts/fotus_token_keeper.py --check  # só verifica status, não renova
"""

import requests, json, time, base64, sys, asyncio, logging
from pathlib import Path
from datetime import datetime, timezone

sys.stdout.reconfigure(encoding="utf-8")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("fotus-keeper")

TOKEN_FILE   = Path("scripts/fotus_token.json")
CONFIG_FILE  = Path("scripts/hub_config.json")
CONFIG_FILE  = Path("scripts/hub_config.json")
BASE         = "https://api-d0983.cloud.solaryum.com.br"
REFRESH_URL  = BASE + "/api/Autenticacao/RenovarAcesso"
INTERVAL_MIN = 30    # renovar a cada 30 min
WARN_MIN     = 15    # tentar renovar se restarem menos de 15 min
CRITICO_MIN  = 5     # alerta urgente se restarem menos de 5 min


def load_token() -> str | None:
    """Lê token local. Se expirado, tenta buscar do Gist (cloud keeper)."""
    token = _read_local_token()
    if token and minutos_restantes(token) > 0:
        return token
    # Token local expirado ou ausente — buscar do Gist
    log.info("Token local expirado. Buscando do Gist...")
    token = _read_gist_token()
    if token and minutos_restantes(token) > 0:
        # Salvar local para próximas leituras
        save_token(token)
        log.info("✓ Token atualizado do Gist")
        return token
    return token  # pode ser None ou expirado


def _read_local_token() -> str | None:
    if not TOKEN_FILE.exists():
        return None
    try:
        data = json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
        return data.get("accessToken") or data.get("token")
    except Exception:
        return None


def _read_gist_token() -> str | None:
    try:
        cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        gh = cfg.get("github", {})
        pat     = gh.get("pat")
        gist_id = gh.get("gist_id")
        if not pat or not gist_id:
            return None
        import urllib.request
        req = urllib.request.Request(
            f"https://api.github.com/gists/{gist_id}",
            headers={"Authorization": f"Bearer {pat}", "Accept": "application/vnd.github+json"},
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.load(r)
        content = data["files"]["fotus_token.json"]["content"]
        return json.loads(content).get("accessToken")
    except Exception as e:
        log.warning(f"Erro ao ler Gist: {e}")
        return None


def save_token(token: str, extra: dict = {}):
    data = {"accessToken": token, **extra}
    TOKEN_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def minutos_restantes(token: str) -> float:
    try:
        part = token.split(".")[1]
        part += "=" * (4 - len(part) % 4)
        payload = json.loads(base64.b64decode(part))
        return (payload.get("exp", 0) - time.time()) / 60
    except Exception:
        return -1


def refresh_api(token: str) -> str | None:
    """Tenta renovar token via API (instantâneo, sem browser)."""
    try:
        r = requests.get(
            REFRESH_URL,
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
            extra = {k: v for k, v in data.items() if k not in ("accessToken", "token")}
            return new_token, extra
        log.warning(f"Refresh API: HTTP {r.status_code}")
        return None, {}
    except Exception as e:
        log.error(f"Erro no refresh API: {e}")
        return None, {}


def login_auto() -> str | None:
    """Login automático via perfil Opera GX."""
    try:
        from fotus_login_auto import fazer_login, load_config, salvar_token
        cfg = load_config()
        token = asyncio.run(fazer_login(cfg))
        if token:
            salvar_token(token)
        return token
    except Exception as e:
        log.error(f"Login automático falhou: {e}")
        return None


def aguardar_token_manual(timeout_min: int = 60) -> str | None:
    """Aguarda novo token ser salvo manualmente (após alerta Telegram)."""
    from hub_alerts import alerta_urgente
    alerta_urgente(
        "Fotus: token *expirado* ☠️\n\n"
        "1. Abra o Opera → app.fotus.com.br\n"
        "2. F12 → Application → Local Storage → copie `accessToken`\n"
        "3. No PowerShell:\n"
        "`cd C:\\Users\\olive\\Projeto\\HUB-Solar`\n"
        "`python scripts\\fotus_set_token.py`\n"
        "4. Cole o token quando pedido\n\n"
        "Feito! Sistema volta automaticamente."
    )
    log.error("Aguardando token manual... (verificando a cada 2 min)")
    token_atual = load_token()
    for _ in range(timeout_min // 2):
        time.sleep(120)
        novo = load_token()
        if novo and novo != token_atual:
            mins = minutos_restantes(novo)
            if mins > 0:
                log.info(f"✓ Novo token detectado! {mins:.0f} min restantes")
                return novo
    return None


def ciclo() -> bool:
    from hub_alerts import alerta, alerta_urgente

    token = load_token()
    if not token:
        alerta_urgente("Fotus: arquivo de token não encontrado. Configure scripts/fotus_token.json.")
        return False

    mins = minutos_restantes(token)
    log.info(f"Token atual: {mins:.1f} min restantes")

    # Token ainda tem tempo suficiente
    if mins > WARN_MIN:
        log.info("Token OK, sem necessidade de renovar agora.")
        return True

    # Aviso se crítico
    if mins < CRITICO_MIN:
        alerta_urgente(f"Fotus: token com apenas {mins:.0f} min restantes! Renovando agora...")
    else:
        log.info(f"Token com {mins:.1f} min — renovando preventivamente...")

    # Tentativa 1: refresh via API (token ainda válido)
    if mins > 0:
        new_token, extra = refresh_api(token)
        if new_token:
            new_mins = minutos_restantes(new_token)
            save_token(new_token, extra)
            log.info(f"✓ Token renovado via API. Novo prazo: {new_mins:.0f} min")
            return True
        log.warning("Refresh API falhou. Tentando login automático...")

    # Tentativa 2: login automático via Opera GX
    log.info("Iniciando login automático via Opera GX...")
    new_token = login_auto()
    if new_token:
        new_mins = minutos_restantes(new_token)
        alerta(f"Fotus: token renovado via login automático ✅ ({new_mins:.0f} min)")
        return True

    # Tentativa 3: aguardar intervenção manual
    log.error("Login automático falhou. Solicitando intervenção manual via Telegram.")
    new_token = aguardar_token_manual(timeout_min=60)
    if new_token:
        alerta("Fotus: token manual detectado e aceito ✅")
        return True

    alerta_urgente("Fotus: KEEPER PARADO. Token expirado e sem renovação. Reinicie manualmente.")
    return False


def check_status():
    """Apenas verifica e exibe status sem renovar."""
    token = load_token()
    if not token:
        print("✗ Token não encontrado")
        return
    mins = minutos_restantes(token)
    status = "✓ OK" if mins > WARN_MIN else ("⚠ AVISO" if mins > 0 else "✗ EXPIRADO")
    print(f"{status} — Token Fotus: {mins:.1f} min restantes")


def main():
    once  = "--once"  in sys.argv
    check = "--check" in sys.argv

    if check:
        check_status()
        return

    log.info("=" * 50)
    log.info("  Fotus Token Keeper")
    log.info(f"  Modo: {'uma vez' if once else f'loop {INTERVAL_MIN} min'}")
    log.info("=" * 50)

    ok = ciclo()
    if once or not ok:
        sys.exit(0 if ok else 1)

    while True:
        log.info(f"Próxima verificação em {INTERVAL_MIN} min. Ctrl+C para parar.")
        time.sleep(INTERVAL_MIN * 60)
        ciclo()


if __name__ == "__main__":
    main()
