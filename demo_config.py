from __future__ import annotations

import os
from typing import Any, Dict

from regime_utils import (
    REGIME_DISPLAY_PRESUMIDO,
    REGIME_DISPLAY_REAL,
    REGIME_DISPLAY_SIMPLES,
)

DEMO_ENV_VAR = "TDE_DEMO"


def _is_truthy(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def resolve_demo_mode(toggle_enabled: bool = False) -> bool:
    """
    Resolve o modo DEMO por OR entre variavel de ambiente e toggle da UI.
    """
    return _is_truthy(os.getenv(DEMO_ENV_VAR)) or bool(toggle_enabled)


def resolve_storage_targets(demo_mode: bool) -> Dict[str, str]:
    """
    Retorna destinos de persistencia para historico e exportacoes.
    """
    if demo_mode:
        return {
            "history_pasta": "data_demo",
            "history_arquivo": "history.jsonl",
            "outputs_txt_pasta": "outputs_demo",
            "outputs_pdf_pasta": "outputs_demo_pdfs",
        }
    return {
        "history_pasta": "data",
        "history_arquivo": "history.jsonl",
        "outputs_txt_pasta": "outputs",
        "outputs_pdf_pasta": "outputs_pdfs",
    }


def _base_demo_event() -> Dict[str, Any]:
    return {
        "nome_empresa": "Empresa DEMO",
        "receita_anual": 0.0,
        "imposto_atual": 0.0,
        "resultados": [],
        "detalhes_regime": {
            "periodicidade": "anual",
            "competencia": "2026",
        },
    }


def demo_example_event(example_key: str) -> Dict[str, Any]:
    """
    Monta payload de exemplo para pre-preenchimento da UI via session_state.
    """
    key = (example_key or "").strip().lower()

    if key == "simples":
        payload = _base_demo_event()
        payload["nome_empresa"] = "Empresa DEMO Simples"
        payload["receita_anual"] = 850000.0
        payload["regime"] = REGIME_DISPLAY_SIMPLES
        payload["detalhes_regime"].update(
            {
                "rbt12": 900000.0,
                "receita_base_periodo": 850000.0,
                "anexo_informado": "III/V",
                "fator_r": 0.30,
            }
        )
        return payload

    if key == "presumido":
        payload = _base_demo_event()
        payload["nome_empresa"] = "Empresa DEMO Presumido"
        payload["receita_anual"] = 1000000.0
        payload["regime"] = REGIME_DISPLAY_PRESUMIDO
        payload["detalhes_regime"].update(
            {
                "tipo_atividade_considerado": "Servicos (geral)",
            }
        )
        return payload

    if key == "real":
        payload = _base_demo_event()
        payload["nome_empresa"] = "Empresa DEMO Real"
        payload["receita_anual"] = 2000000.0
        payload["regime"] = REGIME_DISPLAY_REAL
        payload["detalhes_regime"].update(
            {
                "margem_lucro_estimada": 0.12,
            }
        )
        return payload

    raise ValueError(f"Exemplo DEMO desconhecido: {example_key}")
