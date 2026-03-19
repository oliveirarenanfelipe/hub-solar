"""
Teste de integração Solfácil — fluxo completo via GraphQL
Etapa 1: Autenticar via SSO (Keycloak)
Etapa 2: searchProductsAssembleKit → confirmar disponibilidade
Etapa 3: assembleKit (mutation) → cart_id
Etapa 4: getCustomCartById → preços reais por item
"""

import urllib.request
import urllib.parse
import json
import ssl

# SSL sem verificação (Windows)
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# ─── Configurações ────────────────────────────────────────────────────────────
SSO_URL = "https://sso.solfacil.com.br/realms/General/protocol/openid-connect/token"
GRAPHQL_URL = "https://kong.solfacil.com.br/prd-bff-store/api/graphql"
EMAIL = "renan@fysol.com.br"
PASSWORD = "7zqP_xa5Xn-qf:Y"

# Headers simulando o browser (necessário — a API verifica Origin)
BROWSER_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "Origin": "https://loja.solfacil.com.br",
    "Referer": "https://loja.solfacil.com.br/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

# Parâmetros do kit (mesmos usados no browser)
KIT_PARAMS = {
    "region": "MG",
    "inverter_manufacturer": "GOODWE",
    "inverter_nominal_power": "5.0kW",
    "inverter_type": "Hybrid",
    "network_type": "Monofásico",
    "structure_installation": "Fibrocimento",
    "power": 6.0,
    "dc_id": 0,
    "channel": "autoservico",
}


def post_form(url, fields):
    body = urllib.parse.urlencode(fields).encode("utf-8")
    req = urllib.request.Request(
        url, data=body, method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    with urllib.request.urlopen(req, context=ctx) as r:
        return json.loads(r.read())


def gql(operation, query, variables, token):
    headers = {**BROWSER_HEADERS, "Authorization": f"Bearer {token}"}
    body = json.dumps({"operationName": operation, "query": query, "variables": variables}).encode("utf-8")
    req = urllib.request.Request(GRAPHQL_URL, data=body, method="POST", headers=headers)
    with urllib.request.urlopen(req, context=ctx) as r:
        return json.loads(r.read())


# ─── Etapa 1: Autenticar ──────────────────────────────────────────────────────
print("=== Etapa 1: Autenticando ===")
try:
    auth = post_form(SSO_URL, {
        "grant_type": "password",
        "client_id": "ecommerce",
        "username": EMAIL,
        "password": PASSWORD,
    })
    token = auth.get("access_token")
    if not token:
        print("ERRO: token não retornado. Resposta:", auth)
        exit(1)
    print(f"OK — token obtido ({len(token)} chars)")
except Exception as e:
    print(f"ERRO: {e}")
    exit(1)


# ─── Etapa 2: searchProductsAssembleKit ───────────────────────────────────────
print("\n=== Etapa 2: searchProductsAssembleKit ===")
SEARCH_QUERY = """
query searchProductsAssembleKit(
  $region: String!
  $inverter_manufacturer: String
  $inverter_nominal_power: String
  $structure_installation: String
  $network_type: String
  $inverter_type: String
) {
  searchProductsAssembleKit(
    region: $region
    inverter_manufacturer: $inverter_manufacturer
    inverter_nominal_power: $inverter_nominal_power
    structure_installation: $structure_installation
    network_type: $network_type
    inverter_type: $inverter_type
  ) {
    canAssembleKit
    dc_id
    facets {
      filter_name
      title
      options {
        value
        count
      }
    }
  }
}
"""

dc_id = KIT_PARAMS["dc_id"]
try:
    result = gql("searchProductsAssembleKit", SEARCH_QUERY, {
        "region": KIT_PARAMS["region"],
        "inverter_manufacturer": KIT_PARAMS["inverter_manufacturer"],
        "inverter_nominal_power": KIT_PARAMS["inverter_nominal_power"],
        "inverter_type": KIT_PARAMS["inverter_type"],
        "network_type": KIT_PARAMS["network_type"],
        "structure_installation": KIT_PARAMS["structure_installation"],
    }, token)

    if "errors" in result:
        print("ERRO GraphQL:", json.dumps(result["errors"], indent=2, ensure_ascii=False))
    else:
        data = result.get("data", {}).get("searchProductsAssembleKit", {})
        can = data.get("canAssembleKit")
        dc_id = data.get("dc_id", dc_id)
        facets = data.get("facets", [])
        print(f"OK — canAssembleKit: {can}, dc_id: {dc_id}, facets: {len(facets)}")
        for f in facets:
            print(f"  {f.get('title')}: {[o.get('value') for o in f.get('options', [])]}")
except Exception as e:
    print(f"ERRO: {e}")


# ─── Etapa 3: assembleKit (mutation) ─────────────────────────────────────────
print("\n=== Etapa 3: assembleKit ===")
ASSEMBLE_MUTATION = """
mutation assembleKit(
  $region: String!
  $dc_id: Int!
  $channel: String!
  $power: Float
  $inverter_manufacturer: String
  $inverter_nominal_power: String
  $structure_installation: String
  $network_type: String
  $inverter_type: String
) {
  assembleKit(
    region: $region
    dc_id: $dc_id
    channel: $channel
    power: $power
    inverter_manufacturer: $inverter_manufacturer
    inverter_nominal_power: $inverter_nominal_power
    structure_installation: $structure_installation
    network_type: $network_type
    inverter_type: $inverter_type
  ) {
    cart_id
    dc_id
    region
  }
}
"""

cart_id = None
try:
    result = gql("assembleKit", ASSEMBLE_MUTATION, {
        "channel": KIT_PARAMS["channel"],
        "region": KIT_PARAMS["region"],
        "dc_id": dc_id,
        "power": KIT_PARAMS["power"],
        "inverter_manufacturer": KIT_PARAMS["inverter_manufacturer"],
        "inverter_nominal_power": KIT_PARAMS["inverter_nominal_power"],
        "inverter_type": KIT_PARAMS["inverter_type"],
        "network_type": KIT_PARAMS["network_type"],
        "structure_installation": KIT_PARAMS["structure_installation"],
    }, token)

    if "errors" in result:
        print("ERRO GraphQL:", json.dumps(result["errors"], indent=2, ensure_ascii=False))
    else:
        assemble = result.get("data", {}).get("assembleKit", {})
        cart_id = assemble.get("cart_id")
        print(f"OK — cart_id: {cart_id}, dc_id: {assemble.get('dc_id')}, region: {assemble.get('region')}")
except Exception as e:
    print(f"ERRO: {e}")


# ─── Etapa 4: getCustomCartById ───────────────────────────────────────────────
print("\n=== Etapa 4: getCustomCartById ===")
if not cart_id:
    print("PULANDO — sem cart_id")
else:
    CART_QUERY = """
    query getCustomCartById($cart_id: UUID!, $summarized: Boolean) {
      getCartById(cart_id: $cart_id, summarized: $summarized) {
        id
        dc_id
        region
        assembled_kit
        items {
          sku
          description
          amount
          price
          price_raw
          price_from
          discount_rate
          total
          subtotal
        }
        subtotal
        total
      }
    }
    """

    try:
        result = gql("getCustomCartById", CART_QUERY, {
            "cart_id": cart_id,
            "summarized": False,
        }, token)

        if "errors" in result:
            print("ERRO GraphQL:", json.dumps(result["errors"], indent=2, ensure_ascii=False))
        else:
            cart = result.get("data", {}).get("getCartById", {})
            items = cart.get("items", [])
            print(f"OK — {len(items)} itens | total: R$ {cart.get('total')} | subtotal: R$ {cart.get('subtotal')}")
            print(f"  dc_id: {cart.get('dc_id')} | region: {cart.get('region')} | assembled_kit: {cart.get('assembled_kit')}")
            print("\n  Itens do kit:")
            for item in items:
                print(f"    SKU: {item.get('sku')}")
                print(f"    Desc: {item.get('description')}")
                print(f"    Qtd: {item.get('amount')} | Preço unit: R$ {item.get('price')} | price_raw: {item.get('price_raw')} | price_from: {item.get('price_from')}")
                print(f"    Total item: R$ {item.get('total')} | Desconto: {item.get('discount_rate')}%")
                print()
    except Exception as e:
        print(f"ERRO: {e}")

print("=== Fim do teste ===")
