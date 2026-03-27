"""
Fotus Solar — Login automático com estado Playwright persistente
================================================================
Fluxo:
  1. Se existir scripts/fotus_browser_state.json → usa o estado salvo (cf_clearance
     do último login manual). Cloudflare não desafia. Totalmente silencioso.
  2. Se não existir (primeira vez) → abre browser visível para login manual,
     salva o estado completo (cookies + localStorage) e captura o token.

O cf_clearance dura ~1 ano. Login manual necessário ~1x/ano ou se cookies forem limpos.

Uso:
  python scripts/fotus_login_auto.py            # login automático (ou manual se necessário)
  python scripts/fotus_login_auto.py --force-manual  # forçar login manual para renovar estado
"""

import asyncio, json, sys, logging, base64
from pathlib import Path
from datetime import datetime, timezone

sys.stdout.reconfigure(encoding="utf-8")
logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("fotus-login")

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("Instale: pip install playwright && playwright install chromium")
    sys.exit(1)

CONFIG_FILE    = Path("scripts/hub_config.json")
TOKEN_FILE     = Path("scripts/fotus_token.json")
BROWSER_STATE  = Path("scripts/fotus_browser_state.json")


def load_config():
    return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))


def salvar_token(token: str):
    extra = {}
    try:
        part = token.split(".")[1]
        part += "=" * (4 - len(part) % 4)
        payload = json.loads(base64.b64decode(part))
        exp = payload.get("exp", 0)
        extra["expirationDate"] = datetime.fromtimestamp(exp, tz=timezone.utc).isoformat()
        extra["expiresIn"] = 3600
    except Exception:
        pass
    TOKEN_FILE.write_text(json.dumps({"accessToken": token, **extra}, indent=2), encoding="utf-8")
    log.info(f"✓ Token salvo em {TOKEN_FILE}")


async def capturar_token_da_pagina(page) -> str | None:
    """Tenta extrair token JWT do localStorage/sessionStorage."""
    return await page.evaluate("""() => {
        const stores = [localStorage, sessionStorage];
        for (const store of stores) {
            for (let k of Object.keys(store)) {
                const v = store.getItem(k) || '';
                if (v.startsWith('eyJ') && v.length > 50) return v;
            }
        }
        return null;
    }""")


async def login_com_estado_salvo(cfg: dict) -> str | None:
    """
    Login silencioso usando estado de browser previamente salvo.
    O cf_clearance nos cookies garante que o Cloudflare não vai desafiar.
    """
    fotus_cfg = cfg["fotus"]
    log.info("Usando estado de browser salvo (headless)...")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        )
        ctx = await browser.new_context(
            storage_state=str(BROWSER_STATE),
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/128.0.0.0 Safari/537.36 OPR/114.0.0.0"
            ),
            viewport={"width": 1280, "height": 800},
            locale="pt-BR",
        )

        token_capturado = None

        async def on_response(response):
            nonlocal token_capturado
            if token_capturado:
                return
            try:
                if any(p in response.url for p in ["Autenticacao", "autenticacao", "login", "token"]):
                    body = await response.json()
                    t = body.get("accessToken") or body.get("token")
                    if t and t.startswith("eyJ"):
                        token_capturado = t
                        log.info("✓ Token capturado via resposta de API")
            except Exception:
                pass

        page = await ctx.new_page()
        page.on("response", on_response)

        log.info(f"Navegando para {fotus_cfg['portal_url']}...")
        await page.goto(fotus_cfg["portal_url"], wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(3)

        url_atual = page.url
        log.info(f"URL atual: {url_atual}")

        # Se já está logado (redirecionou para dashboard)
        if "login" not in url_atual.lower():
            log.info("Sessão ativa detectada. Capturando token...")
            token_capturado = await capturar_token_da_pagina(page)

        # Se foi para login, preencher credenciais
        if not token_capturado and "login" in url_atual.lower():
            log.info("Sessão expirada. Preenchendo credenciais...")
            try:
                await page.fill("input[type='email'], input[name='email']", fotus_cfg["email"])
                await asyncio.sleep(0.5)
                await page.fill("input[type='password']", fotus_cfg["senha"])
                await asyncio.sleep(0.5)
                await page.click("button[type='submit'], button:has-text('Entrar')")
                await asyncio.sleep(6)
                token_capturado = await capturar_token_da_pagina(page)
            except Exception as e:
                log.warning(f"Erro ao preencher login: {e}")

        if token_capturado:
            # Salvar estado atualizado
            await ctx.storage_state(path=str(BROWSER_STATE))
            log.info("✓ Estado do browser atualizado")

        await browser.close()
        return token_capturado


async def login_manual(cfg: dict) -> str | None:
    """
    Login manual com browser visível.
    Salva o estado completo (incluindo cf_clearance) para uso futuro.
    """
    fotus_cfg = cfg["fotus"]

    try:
        from hub_alerts import alerta_urgente
        alerta_urgente(
            "Fotus: login manual necessário.\n\n"
            "Abri o browser para você fazer login em *app.fotus.com.br*.\n"
            "Após logar, o sistema captura tudo automaticamente.\n"
            "Você tem 5 minutos."
        )
    except Exception:
        pass

    log.info("=" * 50)
    log.info("  LOGIN MANUAL NECESSÁRIO")
    log.info(f"  Email: {fotus_cfg['email']}")
    log.info(f"  Senha: {fotus_cfg['senha']}")
    log.info("  Faça login no browser que vai abrir.")
    log.info("=" * 50)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False, slow_mo=100)
        ctx = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/128.0.0.0 Safari/537.36 OPR/114.0.0.0"
            ),
            viewport={"width": 1280, "height": 800},
        )
        page = await ctx.new_page()
        await page.goto(fotus_cfg["portal_url"])
        log.info("Browser aberto. Aguardando login (5 min)...")

        for i in range(150):
            await asyncio.sleep(2)
            try:
                token = await capturar_token_da_pagina(page)
                if token:
                    log.info("✓ Token capturado após login manual")
                    # Salvar estado completo do browser (cf_clearance + cookies)
                    await ctx.storage_state(path=str(BROWSER_STATE))
                    log.info(f"✓ Estado do browser salvo em {BROWSER_STATE}")
                    log.info("  Próximos logins serão automáticos por ~1 ano.")
                    await browser.close()
                    return token
            except Exception:
                pass
            if i % 15 == 0 and i > 0:
                log.info(f"Aguardando login... ({i*2}s)")

        await browser.close()
        log.error("Timeout: nenhum token capturado após 5 min.")
        return None


async def main():
    force_manual = "--force-manual" in sys.argv
    cfg = load_config()

    log.info("=== Fotus Login Automático ===")

    if not force_manual and BROWSER_STATE.exists():
        token = await login_com_estado_salvo(cfg)
        if token:
            salvar_token(token)
            log.info("Concluído (automático).")
            return
        log.warning("Login com estado salvo falhou. Tentando login manual...")

    # Login manual (primeira vez ou fallback)
    token = await login_manual(cfg)
    if token:
        salvar_token(token)
        try:
            from hub_alerts import alerta
            alerta("Fotus: token obtido via login manual ✅\nPróximos logins serão automáticos.")
        except Exception:
            pass
        log.info("Concluído (manual). Estado salvo para uso futuro.")
    else:
        log.error("Falha ao capturar token.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
