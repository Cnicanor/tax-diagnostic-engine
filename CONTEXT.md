# CONTEXT — Tax Diagnostic Engine

## Resumo do Produto
Motor de diagnóstico tributário contínuo (CLI + Streamlit) com foco em consultoria e contabilidade, preparado para evolução SaaS e compliance auditável.

## Arquitetura Atual (alto nível)
- `rulesets` versionados em `rulesets/<RULESET_ID>/`.
- `ruleset_loader.py`: carrega metadados, parâmetros fiscais e baselines.
- `tools/ruleset_audit.py`: valida estrutura + baseline parity + hashes (integridade).
- `regimes.py`: cálculos de Simples, Presumido e Real (com guardrails).
- `tax_engine.py`: orquestra diagnóstico, cenários, snapshots e relatório final.
- `eligibility_engine.py`: elegibilidade por regime (ruleset-driven).
- `regime_comparator.py`: comparativo multi-regime.
- `recommendation_engine.py`: recomendação conservadora/estratégica.
- `report_formatters.py` + `report_params_block.py`: renderização sem dict cru.
- `history_store.py`: persistência append-only e reconstrução/refresh de relatório.
- `app.py`/`main.py`: interfaces de apresentação.
- Modo DEMO Streamlit via `TDE_DEMO=1`.

## Regras Tributárias Atuais (resumo)
- Simples Nacional com partilha do DAS (tabelado por ruleset).
- Lucro Presumido com adicional de IRPJ e parâmetros por ruleset.
- Lucro Real estimado com PIS/COFINS não cumulativo e guardrails de crédito.

## Execução Local (Windows PowerShell)
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Rodar Aplicação
```powershell
python main.py
py -m streamlit run app.py
```

## Validação Obrigatória
```powershell
python -m unittest -v
python tools/ruleset_audit.py
```

## Padrões de Relatório
- Proibido `Detalhes do regime: {dict cru}`.
- Usar blocos renderizados por `report_formatters.py` / `report_params_block.py`.
- Manter formatação consistente (moeda/percentual) e seção de auditoria.

## Convenções de Commit e PR
- Padrão de commit: Conventional Commits (ex.: `feat:`, `fix:`, `chore:`).
- Todo trabalho via PR para `main`.
- PR deve conter:
  - escopo objetivo
  - evidências de testes
  - evidências de ruleset audit
  - impacto esperado e riscos
  - checklist DoD completo.
