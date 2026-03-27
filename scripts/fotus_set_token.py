"""
Fotus — Atualização manual do token (intervenção mensal)
=========================================================
Uso: python scripts/fotus_set_token.py
Cole o token quando pedido. Salva localmente e no Gist.
"""
import json, sys, base64, time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

CONFIG = json.loads(Path("scripts/hub_config.json").read_text(encoding="utf-8"))
TOKEN_FILE = Path(CONFIG["fotus"]["token_file"])

print("\n=== Atualização de Token Fotus ===")
print("Cole o accessToken abaixo (Opera → F12 → Application → Local Storage):\n")

token = input("> ").strip()
if not token.startswith("eyJ"):
    print("✗ Token inválido (deve começar com 'eyJ')")
    sys.exit(1)

# Decodificar exp
try:
    part = token.split(".")[1]
    part += "=" * (4 - len(part) % 4)
    payload = json.loads(base64.b64decode(part))
    mins = (payload.get("exp", 0) - time.time()) / 60
    print(f"✓ Token válido — expira em {mins:.0f} min")
except Exception:
    pass

# Salvar local
data = {"accessToken": token}
TOKEN_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
print(f"✓ Salvo em {TOKEN_FILE}")

# Salvar no Gist
try:
    import urllib.request, urllib.parse
    gh = CONFIG["github"]
    req = urllib.request.Request(
        f"https://api.github.com/gists/{gh['gist_id']}",
        data=json.dumps({"files": {"fotus_token.json": {"content": json.dumps(data, indent=2)}}}).encode(),
        headers={
            "Authorization": f"Bearer {gh['pat']}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "X-HTTP-Method-Override": "PATCH",
        },
        method="PATCH",
    )
    with urllib.request.urlopen(req) as r:
        r.read()
    print("✓ Salvo no Gist (cloud keeper vai continuar automaticamente)")
except Exception as e:
    print(f"⚠ Erro ao salvar no Gist: {e} (token local salvo, rode novamente se necessário)")

print("\nPronto! O cloud keeper vai renovar automaticamente daqui em diante.\n")
