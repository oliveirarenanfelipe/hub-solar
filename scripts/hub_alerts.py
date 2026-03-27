"""
HUB Solar — Módulo de alertas Telegram
Uso: from hub_alerts import alerta, alerta_urgente
"""

import urllib.request, urllib.parse, json, logging
from pathlib import Path

_CONFIG_FILE = Path("scripts/hub_config.json")
_log = logging.getLogger("hub-alerts")


def _cfg():
    try:
        return json.loads(_CONFIG_FILE.read_text(encoding="utf-8"))["telegram"]
    except Exception as e:
        _log.error(f"hub_config.json não encontrado ou inválido: {e}")
        return None


def enviar(mensagem: str, urgente: bool = False) -> bool:
    cfg = _cfg()
    if not cfg:
        return False
    prefix = "🔴" if urgente else "🟡"
    texto = f"{prefix} *HUB Solar*\n\n{mensagem}"
    try:
        url = f"https://api.telegram.org/bot{cfg['bot_token']}/sendMessage"
        data = urllib.parse.urlencode({
            "chat_id": cfg["chat_id"],
            "text": texto,
            "parse_mode": "Markdown",
        }).encode()
        with urllib.request.urlopen(url, data, timeout=10) as r:
            return json.load(r).get("ok", False)
    except Exception as e:
        _log.error(f"Falha ao enviar alerta Telegram: {e}")
        return False


def alerta(mensagem: str) -> bool:
    """Alerta informativo (🟡)"""
    _log.warning(f"ALERTA: {mensagem}")
    return enviar(mensagem, urgente=False)


def alerta_urgente(mensagem: str) -> bool:
    """Alerta crítico (🔴) — requer ação imediata"""
    _log.error(f"URGENTE: {mensagem}")
    return enviar(mensagem, urgente=True)
