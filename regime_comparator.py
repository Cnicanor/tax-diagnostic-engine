from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from company_profile import CompanyProfile
from dto import DiagnosticInput
from eligibility_engine import STATUS_BLOCKED, STATUS_OK, EligibilityResult, evaluate_eligibility
from regime_utils import (
    REGIME_CODE_PRESUMIDO,
    REGIME_CODE_REAL,
    REGIME_CODE_SIMPLES,
    REGIME_DISPLAY_PRESUMIDO,
    REGIME_DISPLAY_REAL,
    REGIME_DISPLAY_SIMPLES,
)


@dataclass(frozen=True)
class ComparatorRow:
    regime_code: str
    regime_display: str
    eligibility_status: str
    imposto_total: Optional[float]
    carga_efetiva_percentual: Optional[float]
    alerts: List[str]
    critical_alerts: List[str]
    detalhes_regime: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "regime_code": self.regime_code,
            "regime_display": self.regime_display,
            "eligibility_status": self.eligibility_status,
            "imposto_total": self.imposto_total,
            "carga_efetiva_percentual": self.carga_efetiva_percentual,
            "alerts": list(self.alerts),
            "critical_alerts": list(self.critical_alerts),
            "detalhes_regime": dict(self.detalhes_regime),
        }


def _display_by_code(code: str) -> str:
    if code == REGIME_CODE_SIMPLES:
        return REGIME_DISPLAY_SIMPLES
    if code == REGIME_CODE_PRESUMIDO:
        return REGIME_DISPLAY_PRESUMIDO
    return REGIME_DISPLAY_REAL


def _input_for_regime(profile: CompanyProfile, regime_code: str) -> DiagnosticInput:
    if regime_code == REGIME_CODE_SIMPLES:
        return DiagnosticInput(
            nome_empresa=profile.nome_empresa,
            receita_anual=profile.receita_anual,
            regime=REGIME_DISPLAY_SIMPLES,
            regime_code=REGIME_CODE_SIMPLES,
            regime_model="tabelado",
            periodicidade=profile.periodicidade,
            competencia=profile.competencia,
            ruleset_id=profile.ruleset_id,
            rbt12=profile.rbt12,
            receita_base_periodo=profile.receita_base_periodo,
            anexo_simples=profile.anexo_simples,
            fator_r=profile.fator_r,
            folha_12m=profile.folha_12m,
            modo_analise=profile.modo_analise,
        )
    if regime_code == REGIME_CODE_PRESUMIDO:
        return DiagnosticInput(
            nome_empresa=profile.nome_empresa,
            receita_anual=profile.receita_anual,
            regime=REGIME_DISPLAY_PRESUMIDO,
            regime_code=REGIME_CODE_PRESUMIDO,
            regime_model="padrao",
            periodicidade=profile.periodicidade,
            competencia=profile.competencia,
            ruleset_id=profile.ruleset_id,
            tipo_atividade=profile.tipo_atividade,
            modo_analise=profile.modo_analise,
        )
    return DiagnosticInput(
        nome_empresa=profile.nome_empresa,
        receita_anual=profile.receita_anual,
        regime=REGIME_DISPLAY_REAL,
        regime_code=REGIME_CODE_REAL,
        regime_model="padrao",
        periodicidade=profile.periodicidade,
        competencia=profile.competencia,
        ruleset_id=profile.ruleset_id,
        margem_lucro=profile.margem_lucro,
        receita_base_periodo=profile.receita_base_periodo,
        modo_analise=profile.modo_analise,
    )


def compare_regimes(profile: CompanyProfile, ruleset_id: str) -> Dict[str, Any]:
    """
    Compara regimes preservando matemática atual e usando elegibilidade conservadora.
    Regimes BLOCKED são retornados sem cálculo, com justificativa explícita.
    """
    from tax_engine import DiagnosticService

    eligibility = evaluate_eligibility(profile, ruleset_id)
    service = DiagnosticService()

    rows: List[ComparatorRow] = []
    for regime_code in (REGIME_CODE_SIMPLES, REGIME_CODE_PRESUMIDO, REGIME_CODE_REAL):
        elig: EligibilityResult = eligibility[regime_code]
        alerts = list(elig.reasons) + list(elig.missing_inputs)
        critical_alerts: List[str] = []

        if elig.status == STATUS_BLOCKED:
            critical_alerts.extend(alerts)
            rows.append(
                ComparatorRow(
                    regime_code=regime_code,
                    regime_display=_display_by_code(regime_code),
                    eligibility_status=elig.status,
                    imposto_total=None,
                    carga_efetiva_percentual=None,
                    alerts=alerts,
                    critical_alerts=critical_alerts,
                    detalhes_regime={},
                )
            )
            continue

        inp = _input_for_regime(profile, regime_code)
        try:
            imposto, detalhes = service._imposto_atual_por_regime(inp)
        except ValueError as exc:
            msg = str(exc)
            # Falhas de ruleset são críticas e devem interromper execução.
            if "ruleset_id=" in msg and "arquivo=" in msg and "chave=" in msg:
                raise
            critical_alerts.append(msg)
            rows.append(
                ComparatorRow(
                    regime_code=regime_code,
                    regime_display=_display_by_code(regime_code),
                    eligibility_status=STATUS_BLOCKED,
                    imposto_total=None,
                    carga_efetiva_percentual=None,
                    alerts=alerts + [msg],
                    critical_alerts=critical_alerts,
                    detalhes_regime={},
                )
            )
            continue

        carga = (float(imposto) / float(profile.receita_anual)) * 100.0 if profile.receita_anual > 0 else None
        if elig.status != STATUS_OK:
            critical_alerts.extend(alerts)
        rows.append(
            ComparatorRow(
                regime_code=regime_code,
                regime_display=_display_by_code(regime_code),
                eligibility_status=elig.status,
                imposto_total=float(imposto),
                carga_efetiva_percentual=carga,
                alerts=alerts,
                critical_alerts=critical_alerts,
                detalhes_regime=detalhes,
            )
        )

    return {
        "eligibility": {k: v.to_dict() for k, v in eligibility.items()},
        "rows": [r.to_dict() for r in rows],
    }
