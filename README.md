# 🕵️ Senior Scout 360 v3.0

## Arquitetura Multi-Agent Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│                        STREAMLIT UI                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │  Sidebar  │  │  Dossiê  │  │  Charts  │  │  Export  │    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │
├─────────────────────────────────────────────────────────────┤
│                   DOSSIER ORCHESTRATOR                        │
│  Pipeline: CNPJ → Recon → Finance → Intel → Análise → QG   │
├─────────────────────────────────────────────────────────────┤
│                        SERVICES                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ gemini_svc   │  │ cnpj_svc    │  │ market_estimator    │ │
│  │ (5 agentes)  │  │ (BrasilAPI) │  │ (SAS 4.0)          │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ cache_svc    │  │ req_queue   │  │ quality_gate        │ │
│  │ (L1+L2)     │  │ (TokenBkt)  │  │ (Auditor)          │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│                    UTILS & TYPES                             │
│  types.py │ market_intelligence.py │ (Knowledge Base)       │
└─────────────────────────────────────────────────────────────┘
```

## Modelos Utilizados

| Tarefa | Modelo | Motivo |
|--------|--------|--------|
| Recon Operacional | `gemini-2.5-flash` | Search rápido + thinking |
| Sniper Financeiro | `gemini-2.5-flash` | Search rápido + thinking |
| Intel de Mercado | `gemini-2.5-flash` | Search rápido |
| Análise Estratégica | `gemini-2.5-pro` | Raciocínio profundo (8k thinking budget) |
| Auditoria de Qualidade | `gemini-2.5-pro` | Avaliação crítica |
| Busca Mágica CNPJ | `gemini-2.5-flash` | Search pontual |

## Pipeline de 6 Passos

1. **Consulta CNPJ** — BrasilAPI com retry + cache + fallback ReceitaWS
2. **Recon Operacional** — Flash + Google Search: hectares, culturas, verticalização
3. **Sniper Financeiro** — Flash + Google Search: CRAs, Fiagros, governança
4. **Intel de Mercado** — Flash + Google Search: notícias, sinais de compra
5. **Análise Estratégica** — Pro (deep thinking): dossiê em 4 seções
6. **Quality Gate** — Determinístico + Pro: auditoria de qualidade

## Setup

```bash
pip install -r requirements.txt
streamlit run app.py
```

Configurar API Key em `.streamlit/secrets.toml`:
```toml
GEMINI_API_KEY = "sua-chave-aqui"
```
