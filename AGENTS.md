# AGENTS — Tax Diagnostic Engine

## Objetivo
Padronizar o fluxo orientado a Issues/PRs com guardrails técnicos para manter compliance, auditabilidade e previsibilidade de entrega.

## Papéis
- `Executor (Codex)`: implementa mudanças técnicas e documentação.
- `Reviewer`: valida arquitetura, riscos, compatibilidade e escopo.
- `QA/CI`: valida testes, ruleset audit e higiene de repositório.
- `Release (opcional)`: versionamento/tag/changelog e publicação.

## Regras do Executor (obrigatórias)
- Trabalhar sempre via PR (branch dedicada + PR para `main`).
- Rodar sempre:
  - `python -m unittest -v`
  - `python tools/ruleset_audit.py`
- Não alterar matemática/regras de cálculo sem autorização explícita.
- Em mudanças de ruleset:
  - atualizar baseline correspondente (`rulesets/<RULESET_ID>/evidence/*`)
  - manter `ruleset_audit.py` com status `PASS`.
- Não inserir artefatos gerados no Git (`__pycache__`, `build`, `dist`, `outputs`, `*.jsonl`, PDFs gerados).

## Guardrails de Arquitetura
- Separar domínio (motor/regimes/orquestração) de UI (`app.py`/`main.py`) e persistência (`history_store.py`).
- Evitar regra de negócio na UI além de validação de entrada/formatação.
- Preservar compatibilidade com histórico append-only.
- Não expor dict cru em relatório (`Detalhes do regime: { ... }` é proibido).

## Fluxo de Trabalho (exemplo)
- Criar branch: `git checkout -b chore/exemplo`.
- Implementar mudanças com escopo objetivo.
- Executar validações locais:
  - `python -m unittest -v`
  - `python tools/ruleset_audit.py`
- Commit com mensagem objetiva (Conventional Commits).
- Abrir PR para `main` com checklist preenchido e evidências.

## Definition of Done (DoD)
- Testes passando.
- Ruleset audit passando.
- Sem artefatos gerados no PR.
- Impacto, riscos e evidências descritos no PR.
