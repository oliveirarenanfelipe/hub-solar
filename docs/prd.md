# PRD — HUB Solar

## Visão Geral

O **HUB Solar** é uma plataforma interna para centralizar preços de distribuidores de energia solar e gerar propostas profissionais com fidelidade aos preços de mercado.

O problema central: hoje o processo de orçamento é manual, sujeito a desatualização de preços e limitado aos distribuidores que o integrador conhece. O HUB Solar resolve isso agregando dados de múltiplos distribuidores — com ou sem API disponível.

---

## Problema

1. **Preços desatualizados**: Tabelas de preços são atualizadas com frequência pelos distribuidores
2. **Cobertura limitada**: Sem acesso sistematizado, o integrador só cotiza com 1-2 distribuidores conhecidos
3. **Processo manual**: Cópias de planilhas, PDFs de catálogos, consultas por WhatsApp
4. **Proposta não profissional**: Sem um sistema, a proposta ao cliente fica informal e pouco confiável

---

## Solução

Plataforma web que:
1. **Agrega preços** de múltiplos distribuidores (via API, scraping ou upload manual)
2. **Monta kits** automaticamente baseado na demanda do cliente
3. **Gera proposta** profissional com preços em tempo real
4. **Compara distribuidores** para encontrar a melhor margem

---

## Distribuidores Alvo (fase 1)

| Distribuidor | Tipo de Acesso | Status |
|---|---|---|
| A definir via pesquisa | API / Scraping / Manual | Pendente |

---

## Concorrentes Analisados

### SolarApp (solarapp.com.br)
- Gerador de propostas + kits
- Integração manual de distribuidores
- Freemium, monetiza em transações

### Suns Brasil (sunsbrasil.com.br)
- Marketplace completo (600+ integradores)
- CRM + financiamentos + homologação
- Ecossistema mais completo do mercado

### Gaps identificados nos concorrentes
- Integração automática de preços em tempo real é fraca
- Foco em integradores grandes, não autônomos
- Sem comparação lado a lado de distribuidores
- Sem suporte para distribuidores sem API

---

## Épicos Planejados

| Épico | Nome | Descrição |
|---|---|---|
| 0 | Discovery | Pesquisa de distribuidores, mapeamento de fontes de preço, definição de arquitetura |
| 1 | Core Platform | App base: cadastro, autenticação, estrutura de dados |
| 2 | Integração Distribuidores | Conectores por distribuidor (API/scraper/manual) |
| 3 | Gerador de Propostas | Engine de montagem de kits + PDF de proposta |
| 4 | Dashboard & Comparação | Visão consolidada de preços e margens |

---

## Stack Técnica (a definir no Épico 0)

A ser definida após Brownfield Discovery + pesquisa. Candidatos:
- **Frontend**: Next.js / React
- **Backend**: Node.js / Python (FastAPI)
- **DB**: PostgreSQL (Supabase)
- **Scrapers**: Playwright / Puppeteer
- **Infra**: Railway / Vercel

---

## Métricas de Sucesso

- Tempo para gerar uma proposta: < 2 minutos
- Cobertura de distribuidores: 5+ na fase 1
- Fidelidade de preço: delta < 2% em relação ao preço real
- Propostas geradas por mês: meta a definir

---

*Documento vivo — atualizar conforme o projeto evolui.*
