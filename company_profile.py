from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from dto import DiagnosticInput
from input_utils import validar_competencia, validar_periodicidade
from regime_utils import canonicalize_regime
from ruleset_loader import DEFAULT_RULESET_ID

MODO_CONSERVADOR = "conservador"
MODO_ESTRATEGICO = "estrategico"


@dataclass(frozen=True)
class CompanyProfile:
    nome_empresa: str
    receita_anual: float
    periodicidade: str
    competencia: Optional[str]
    ruleset_id: str
    regime_code_atual: str
    regime_model_atual: str
    regime_display_atual: str
    modo_analise: str
    rbt12: Optional[float]
    receita_base_periodo: Optional[float]
    margem_lucro: Optional[float]
    tipo_atividade: Optional[str]
    anexo_simples: Optional[str]
    fator_r: Optional[float]
    folha_12m: Optional[float]
    assumptions: List[str]
    missing_inputs: List[str]


def _normalize_mode(value: Optional[str]) -> str:
    raw = str(value or "").strip().lower()
    if raw == MODO_ESTRATEGICO:
        return MODO_ESTRATEGICO
    return MODO_CONSERVADOR


def normalize_company_profile(inp: DiagnosticInput) -> CompanyProfile:
    """
    Normaliza perfil da empresa para comparativo/elegibilidade sem alterar cálculos fiscais.
    Defaults são explícitos e retornados em `assumptions`.
    """
    if not inp.nome_empresa.strip():
        raise ValueError("nome_empresa é obrigatório para normalizar perfil.")
    if float(inp.receita_anual) <= 0:
        raise ValueError("receita_anual deve ser maior que zero para normalizar perfil.")

    regime_info = canonicalize_regime(inp.regime, inp.regime_code, inp.regime_model)
    assumptions: List[str] = []
    missing_inputs: List[str] = []

    periodicidade = validar_periodicidade(str(inp.periodicidade or "anual"))
    competencia: Optional[str] = None
    if inp.competencia:
        ok, comp_or_err = validar_competencia(periodicidade, str(inp.competencia))
        if ok:
            competencia = comp_or_err
        else:
            assumptions.append(
                f"Competência inválida no input foi descartada ({comp_or_err}); metadado mantido sem competência."
            )

    ruleset_id = str(inp.ruleset_id or DEFAULT_RULESET_ID).strip() or DEFAULT_RULESET_ID
    modo_analise = _normalize_mode(inp.modo_analise)

    rbt12 = float(inp.rbt12) if inp.rbt12 is not None else None
    if rbt12 is None:
        rbt12 = float(inp.receita_anual)
        assumptions.append("RBT12 não informado; assumido igual à receita anual para metadados/comparativo.")
    elif rbt12 <= 0:
        raise ValueError("rbt12 deve ser maior que zero quando informado.")

    receita_base_periodo = float(inp.receita_base_periodo) if inp.receita_base_periodo is not None else None
    if receita_base_periodo is None:
        receita_base_periodo = float(inp.receita_anual)
        assumptions.append("Receita base do período não informada; assumida igual à receita anual.")
    elif receita_base_periodo <= 0:
        raise ValueError("receita_base_periodo deve ser maior que zero quando informada.")

    margem_lucro = float(inp.margem_lucro) if inp.margem_lucro is not None else None
    if margem_lucro is None:
        margem_lucro = 0.10
        assumptions.append("Margem de lucro não informada; assumida em 10% para análises de Lucro Real.")
    elif margem_lucro < 0:
        raise ValueError("margem_lucro não pode ser negativa.")

    fator_r = float(inp.fator_r) if inp.fator_r is not None else None
    if fator_r is not None and not (0.0 <= fator_r <= 1.0):
        raise ValueError("fator_r deve estar entre 0 e 1.")

    folha_12m = float(inp.folha_12m) if inp.folha_12m is not None else None
    if folha_12m is not None and folha_12m < 0:
        raise ValueError("folha_12m deve ser maior ou igual a zero.")

    anexo_simples = str(inp.anexo_simples or "").strip().upper().replace("-", "/")
    if not anexo_simples:
        anexo_simples = None

    if anexo_simples == "III/V" and fator_r is None and folha_12m is None:
        missing_inputs.append("Simples III/V requer fator_r ou folha_12m.")
    if regime_info["regime_code"] == "SIMPLES" and not anexo_simples:
        missing_inputs.append("Anexo do Simples não informado.")
    if regime_info["regime_code"] == "PRESUMIDO" and not str(inp.tipo_atividade or "").strip():
        missing_inputs.append("Tipo de atividade não informado para Presumido.")

    return CompanyProfile(
        nome_empresa=inp.nome_empresa.strip(),
        receita_anual=float(inp.receita_anual),
        periodicidade=periodicidade,
        competencia=competencia,
        ruleset_id=ruleset_id,
        regime_code_atual=regime_info["regime_code"],
        regime_model_atual=regime_info["regime_model"],
        regime_display_atual=regime_info["regime_display"],
        modo_analise=modo_analise,
        rbt12=rbt12,
        receita_base_periodo=receita_base_periodo,
        margem_lucro=margem_lucro,
        tipo_atividade=str(inp.tipo_atividade).strip() if inp.tipo_atividade else None,
        anexo_simples=anexo_simples,
        fator_r=fator_r,
        folha_12m=folha_12m,
        assumptions=assumptions,
        missing_inputs=missing_inputs,
    )
