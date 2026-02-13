from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

from ruleset_loader import DEFAULT_RULESET_ID


@dataclass(frozen=True)
class DiagnosticInput:
    nome_empresa: str
    receita_anual: float
    regime: str  # compat legado; UI atual usa: Simples Nacional | Lucro Presumido | Lucro Real
    regime_code: Optional[str] = None   # SIMPLES | PRESUMIDO | REAL
    regime_model: Optional[str] = None  # tabelado | manual | padrao
    aliquota_simples: Optional[float] = None  # decimal (ex: 0.085)
    margem_lucro: Optional[float] = None      # decimal (ex: 0.10)
    tipo_atividade: Optional[str] = None
    rbt12: Optional[float] = None
    receita_base_periodo: Optional[float] = None
    anexo_simples: Optional[str] = None  # I | II | III | IV | V | III/V
    fator_r: Optional[float] = None
    folha_12m: Optional[float] = None
    despesas_creditaveis: Optional[float] = None
    percentual_credito_estimado: Optional[float] = None
    periodicidade: Optional[str] = "anual"  # mensal | trimestral | anual
    competencia: Optional[str] = None
    ruleset_id: Optional[str] = DEFAULT_RULESET_ID
    modo_analise: Optional[str] = "conservador"  # conservador | estrategico
    cenarios: Optional[Dict[str, float]] = None


@dataclass(frozen=True)
class ScenarioResult:
    nome_cenario: str
    aliquota_reforma: float
    imposto_reforma: float
    diferenca: float
    impacto_percentual: float
    classificacao: str
    recomendacao: str


@dataclass(frozen=True)
class DiagnosticOutput:
    nome_empresa: str
    receita_anual: float
    regime: str
    detalhes_regime: Dict[str, Any]
    imposto_atual: float
    resultados: List[ScenarioResult]
    relatorio_texto: str

    def to_event(self) -> Dict[str, Any]:
        return asdict(self)
