"""
Teste de integração Aldo Solar (Volt) — API REST
Autenticar + listar kits solares com preços reais

Auth: Basic email:password para chamadas POST/GET normais
senhaCriptografada: Base64("00" + password)  [n=0 do algoritmo nested-base64]
"""

import urllib.request
import urllib.error
import json
import ssl
import base64
import datetime

# SSL sem verificação (Windows)
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# ─── Configurações ────────────────────────────────────────────────────────────
BASE_URL = "https://win-tasks02.aldo.com.br:8443/services/MetamorfoseVoltService"
USUARIO = "danilo@fysol.com.br"
PASSWORD = "vybdiT-vebwyb-zegto3"

# Basic auth para chamadas GET/POST
BASIC_AUTH = base64.b64encode(f"{USUARIO}:{PASSWORD}".encode()).decode()

# senhaCriptografada para auth inicial (n=0: Base64("00" + password))
SENHA_CRIPTOGRAFADA = base64.b64encode(f"00{PASSWORD}".encode()).decode()

HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Origin": "https://volt.aldo.com.br",
    "Referer": "https://volt.aldo.com.br/",
    "Authorization": f"Basic {BASIC_AUTH}",
}

# GUID do tipo de produto "GERADOR"
GERADOR_GUID = "93ed136d-d7c2-4c9a-98da-ea86d59cb6ac"


def get(path):
    req = urllib.request.Request(f"{BASE_URL}{path}", method="GET", headers=HEADERS)
    with urllib.request.urlopen(req, context=ctx) as r:
        return json.loads(r.read())


def post(path, body):
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        f"{BASE_URL}{path}", data=data, method="POST", headers=HEADERS
    )
    with urllib.request.urlopen(req, context=ctx) as r:
        return json.loads(r.read())


# ─── Etapa 1: Verificar auth ──────────────────────────────────────────────────
print("=== Etapa 1: Autenticando ===")
try:
    auth_resp = post(
        "/AutenticarUsuario",
        {"usuario": USUARIO, "senhaCriptografada": SENHA_CRIPTOGRAFADA},
    )
    user_data = auth_resp.get("data", {})
    print(f"OK — usuário: {user_data.get('nome')} ({user_data.get('email')})")
    print(f"  GUID: {user_data.get('guid')}")
except Exception as e:
    print(f"ERRO: {e}")
    exit(1)


# ─── Etapa 2: Listar filtros disponíveis ─────────────────────────────────────
print("\n=== Etapa 2: Filtros do sistema fotovoltaico ===")
try:
    filtros = get("/ListarFiltrosSistemaFotovoltaico")
    print(f"Tensões: {[t['descricao'] for t in filtros.get('tensoes', [])]}")
    print(f"Estruturas: {[e['descricao'] for e in filtros.get('estruturas', [])]}")
    print(f"Marcas inversores: {[m['descricao'] for m in filtros.get('marcas', [])]}")
    print(f"Módulos disponíveis: {len(filtros.get('produtos', []))} modelos")
except Exception as e:
    print(f"ERRO: {e}")


# ─── Etapa 3: Listar todos os kits geradores ─────────────────────────────────
print("\n=== Etapa 3: Kits geradores (ListarProdutos) ===")
try:
    resp = get(f"/ListarProdutos?TipoProdutos={GERADOR_GUID}")
    kits = resp.get("data", [])
    print(f"OK — {len(kits)} kits encontrados")
    print()
    print(f"{'SKU':12} | {'kWp':8} | {'Sistema':10} | {'Estrutura':25} | {'Preço':12} | Estoque")
    print("-" * 95)
    for k in sorted(kits, key=lambda x: x.get("potencia", 0)):
        pot = k.get("potencia", 0)
        sku = k.get("sku", "")
        sistema = k.get("sistema", {}).get("descricao", "") if k.get("sistema") else ""
        estrutura = (
            k.get("estrutura", {}).get("descricao", "") if k.get("estrutura") else ""
        )
        preco = k.get("preco", 0)
        estoque = "OK" if k.get("temEstoque") else "--"
        print(
            f"{sku:12} | {pot:7}kWp | {sistema:10} | {estrutura:25} | R${preco:10,.2f} | {estoque}"
        )
except Exception as e:
    print(f"ERRO: {e}")


# ─── Etapa 4: Detalhar primeiro kit ─────────────────────────────────────────
print("\n=== Etapa 4: Composição do primeiro kit ===")
try:
    if kits:
        k = sorted(kits, key=lambda x: x.get("potencia", 0))[0]
        print(f"Kit: {k.get('descricaoCompleta')}")
        print(f"Potência: {k.get('potencia')} kWp | Preço: R${k.get('preco'):,.2f}")
        comps = k.get("produtosComposicao", [])
        print(f"Componentes ({len(comps)} itens):")
        for c in comps:
            tipo = c.get("tipoProduto", {}).get("descricao", "")
            desc = c.get("descricaoResumida", "")
            qtd = c.get("quantidade", 1)
            preco_c = c.get("preco", 0) or c.get("precoComposicao", 0)
            print(f"  [{tipo:20}] x{qtd:3} | {desc[:60]} | R${preco_c:8,.2f}")
except Exception as e:
    print(f"ERRO: {e}")


print("\n=== Fim do teste ===")
print(f"Data: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
