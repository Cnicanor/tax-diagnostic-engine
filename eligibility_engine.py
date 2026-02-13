from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from company_profile import CompanyProfile
from regime_utils import REGIME_CODE_PRESUMIDO, REGIME_CODE_REAL, REGIME_CODE_SIMPLES
from ruleset_loader import get_eligibility_rules

STATUS_OK = "OK"
STATUS_WARNING = "WARNING"
STATUS_BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class EligibilityResult:
    regime_code: str
    status: str
    reasons: List[str]
    missing_inputs: List[str]
    assumptions: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "regime_code": self.regime_code,
            "status": self.status,
            "reasons": list(self.reasons),
            "missing_inputs": list(self.missing_inputs),
            "assumptions": list(self.assumptions),
        }


def _ruleset_error(ruleset_id: str, key: str, regime: str, impacto: str, detalhe: str) -> ValueError:
    return ValueError(
        f"ruleset_id={ruleset_id} | arquivo=eligibility_rules.json | chave={key} | "
        f"regime={regime} | impacto={impacto} | detalhe={detalhe}"
    )


def _required_dict(payload: Dict[str, Any], key: str, ruleset_id: str, regime: str, impacto: str) -> Dict[str, Any]:
    if key not in payload:
        raise _ruleset_error(ruleset_id, key, regime, impacto, "chave ausente")
    value = payload.get(key)
    if not isinstance(value, dict):
        raise _ruleset_error(ruleset_id, key, regime, impacto, "objeto inválido")
    return value


def _required_number(payload: Dict[str, Any], key: str, ruleset_id: str, regime: str, impacto: str) -> float:
    if key not in payload:
        raise _ruleset_error(ruleset_id, key, regime, impacto, "chave ausente")
    value = payload.get(key)
    if not isinstance(value, (int, float)):
        raise _ruleset_error(ruleset_id, key, regime, impacto, "valor não numérico")
    return float(value)


def _required_list(payload: Dict[str, Any], key: str, ruleset_id: str, regime: str, impacto: str) -> List[Any]:
    if key not in payload:
        raise _ruleset_error(ruleset_id, key, regime, impacto, "chave ausente")
    value = payload.get(key)
    if not isinstance(value, list):
        raise _ruleset_error(ruleset_id, key, regime, impacto, "lista inválida")
    return value


def evaluate_eligibility(profile: CompanyProfile, ruleset_id: str) -> Dict[str, EligibilityResult]:
    """
    Avalia elegibilidade por regime em modo conservador (ruleset-driven).
    """
    rules = get_eligibility_rules(ruleset_id)
    sim_rules = _required_dict(
        rules,
        "simples",
        ruleset_id,
        "Simples Nacional",
        "Não é possível avaliar elegibilidade do Simples",
    )
    pres_rules = _required_dict(
        rules,
        "presumido",
        ruleset_id,
        "Lucro Presumido",
        "Não é possível avaliar elegibilidade do Presumido",
    )
    real_rules = _required_dict(
        rules,
        "real",
        ruleset_id,
        "Lucro Real",
        "Não é possível avaliar elegibilidade do Real",
    )

    # Simples
    sim_reasons: List[str] = []
    sim_missing: List[str] = []
    sim_assumptions: List[str] = []
    limite_simples = _required_number(
        sim_rules,
        "rbt12_max",
        ruleset_id,
        "Simples Nacional",
        "Não é possível validar limite de receita",
    )
    if profile.rbt12 is None:
        sim_missing.append("RBT12")
    elif profile.rbt12 > limite_simples:
        sim_reasons.append(f"RBT12 acima do limite do Simples ({limite_simples:,.2f}).")
    if not profile.anexo_simples:
        sim_missing.append("Anexo do Simples")
    elif profile.anexo_simples == "III/V" and profile.fator_r is None and profile.folha_12m is None:
        sim_missing.append("fator_r ou folha_12m para III/V")

    sim_status = STATUS_OK
    if sim_reasons or sim_missing:
        sim_status = STATUS_BLOCKED
    if profile.anexo_simples is None:
        sim_assumptions.append("Comparativo não inferiu anexo automaticamente para Simples.")

    # Presumido
    pres_reasons: List[str] = []
    pres_missing: List[str] = []
    pres_assumptions: List[str] = []
    limite_pres = _required_number(
        pres_rules,
        "receita_anual_max",
        ruleset_id,
        "Lucro Presumido",
        "Não é possível validar limite de receita",
    )
    if profile.receita_anual > limite_pres:
        pres_reasons.append(f"Receita anual acima do limite do Presumido ({limite_pres:,.2f}).")
    if not profile.tipo_atividade:
        pres_missing.append("Tipo de atividade")
        pres_assumptions.append("Sem tipo de atividade, o cálculo do Presumido pode usar fallback do ruleset.")

    pres_status = STATUS_OK
    if pres_reasons:
        pres_status = STATUS_BLOCKED
    elif pres_missing:
        pres_status = STATUS_WARNING

    # Real
    real_reasons: List[str] = []
    real_missing: List[str] = []
    real_assumptions: List[str] = []
    if any("Margem de lucro não informada" in ass for ass in profile.assumptions):
        real_assumptions.append("Margem de lucro foi assumida por default no perfil normalizado.")
        real_status = STATUS_WARNING
    else:
        real_status = STATUS_OK
    _required_list(
        real_rules,
        "warnings",
        ruleset_id,
        "Lucro Real",
        "Não é possível carregar configuração mínima do Real",
    )

    return {
        REGIME_CODE_SIMPLES: EligibilityResult(
            regime_code=REGIME_CODE_SIMPLES,
            status=sim_status,
            reasons=sim_reasons,
            missing_inputs=sim_missing,
            assumptions=sim_assumptions,
        ),
        REGIME_CODE_PRESUMIDO: EligibilityResult(
            regime_code=REGIME_CODE_PRESUMIDO,
            status=pres_status,
            reasons=pres_reasons,
            missing_inputs=pres_missing,
            assumptions=pres_assumptions,
        ),
        REGIME_CODE_REAL: EligibilityResult(
            regime_code=REGIME_CODE_REAL,
            status=real_status,
            reasons=real_reasons,
            missing_inputs=real_missing,
            assumptions=real_assumptions,
        ),
    }
