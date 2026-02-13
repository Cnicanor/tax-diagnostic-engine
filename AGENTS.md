# Tax Diagnostic Engine — Instruções para o Codex (Arquitetura)

## Objetivo
Construir um MVP escalável de diagnóstico tributário contínuo (CLI + Streamlit), com foco em consultores e contadores.

## Regras de arquitetura
- Separe domínio (cálculo/orquestração) de UI (app.py/main.py) e persistência (history_store.py).
- Não coloque regra de negócio no Streamlit/CLI além de validação simples e formatação.
- Prefira funções puras e módulos pequenos.
- Toda mudança deve manter compatibilidade com o que já funciona (TXT/PDF/Histórico/Streamlit).
- Sempre que alterar múltiplos arquivos, produza um plano + patch (o que muda em qual arquivo).

## Qualidade
- Use type hints e docstrings nas funções novas.
- Se criar novas funções, inclua validações e mensagens de erro claras.
- Ao final de cada tarefa, proponha como testar (comandos exatos).

## Rotina obrigatória do Codex
1) Ler os arquivos relevantes no workspace.
2) Propor plano curto (3–7 passos).
3) Implementar mudanças pequenas e testáveis.
4) Rodar/validar: `python main.py` e `py -m streamlit run app.py` quando relevante.
5) Se quebrar algo, consertar e explicar.
