from datetime import date, datetime
from typing import Any, Dict, List

from dto import DiagnosticInput
from regime_utils import (
    REGIME_CODE_PRESUMIDO,
    REGIME_CODE_REAL,
    REGIME_CODE_SIMPLES,
    REGIME_MODEL_MANUAL,
    REGIME_MODEL_TABELADO,
    canonicalize_regime,
)
from ruleset_loader import DEFAULT_RULESET_ID, load_ruleset
from tools.ruleset_audit import get_integrity_summary

# Mantido para compatibilidade legada; nao usar como fonte principal de ruleset atual.
RULESET_ID = "BR_TAX_V1"


def _calculo_tipo_por_regime(regime_code: str, regime_model: str) -> str:
    if regime_code == REGIME_CODE_SIMPLES and regime_model == REGIME_MODEL_MANUAL:
        return "estimativa_parametrizada"
    if regime_code == REGIME_CODE_SIMPLES and regime_model == REGIME_MODEL_TABELADO:
        return "estimativa_parametrizada"
    if regime_code == REGIME_CODE_PRESUMIDO:
        return "estimativa_parametrizada"
    if regime_code == REGIME_CODE_REAL:
        return "estimativa"
    return "estimativa"


def _sources_por_regime(regime_code: str, regime_model: str, ruleset_id: str) -> List[str]:
    sources = [
        f"Parametros e tabelas carregados do ruleset: {ruleset_id}.",
        "Regras de elegibilidade carregadas de eligibility_rules.json do ruleset.",
    ]

    if regime_code == REGIME_CODE_SIMPLES and regime_model == REGIME_MODEL_MANUAL:
        sources.extend(
            [
                "Simples Nacional legado/manual: aliquota efetiva informada no evento historico.",
                "Cenarios pos-reforma deste MVP usam aliquotas parametrizadas para analise comparativa.",
            ]
        )
        return sources

    if regime_code == REGIME_CODE_SIMPLES:
        sources.extend(
            [
                "Simples Nacional: calculo por anexo/faixa com formula da aliquota efetiva.",
                "Tabelas dos Anexos I a V sao lidas de simples_tables.json do ruleset.",
                "Simples Partilha: fonte = ruleset.simples_tables.json (percentuais por tributo).",
                "Cenarios pos-reforma deste MVP usam aliquotas parametrizadas para analise comparativa.",
            ]
        )
        return sources

    if regime_code == REGIME_CODE_PRESUMIDO:
        sources.extend(
            [
                "IRPJ/CSLL (regras gerais): adicional de IRPJ com limite por periodicidade definido no ruleset.",
                "PIS/COFINS cumulativo no Presumido: parametros lidos do ruleset.",
                "Percentual de presuncao por tipo de atividade e lido do ruleset.",
            ]
        )
        return sources

    sources.extend(
        [
            "Lucro Real neste MVP: estimativa por margem para IRPJ/CSLL.",
            "Parametros de IRPJ/CSLL/PIS/COFINS no Lucro Real sao lidos de real_params.json do ruleset.",
            "Cenarios pos-reforma deste MVP usam aliquotas parametrizadas para analise comparativa.",
        ]
    )
    return sources


def _resolve_ruleset_id(detalhes_regime: Dict[str, Any], inp: DiagnosticInput) -> str:
    requested = None
    if isinstance(inp.ruleset_id, str) and inp.ruleset_id.strip():
        requested = inp.ruleset_id.strip()
    elif isinstance(detalhes_regime, dict):
        val = detalhes_regime.get("ruleset_id")
        if isinstance(val, str) and val.strip():
            requested = val.strip()

    target = requested or DEFAULT_RULESET_ID

    metadata = load_ruleset(target)
    rid = metadata.get("ruleset_id", target)
    if not isinstance(rid, str) or not rid.strip():
        raise ValueError(f"Ruleset '{target}' invalido: ruleset_id ausente em metadata.")
    return rid.strip()


def _load_ruleset_metadata_subset(ruleset_id: str) -> Dict[str, Any]:
    metadata = load_ruleset(ruleset_id)
    return {
        "ruleset_id": metadata.get("ruleset_id", ruleset_id),
        "vigencia_inicio": metadata.get("vigencia_inicio"),
        "vigencia_fim": metadata.get("vigencia_fim"),
        "descricao": metadata.get("descricao"),
    }


def _references_from_metadata(ruleset_id: str) -> List[str]:
    metadata = load_ruleset(ruleset_id)
    fontes = metadata.get("fontes_oficiais")
    if not isinstance(fontes, list):
        raise ValueError(f"ruleset '{ruleset_id}' invalido: fontes_oficiais ausente em metadata.json.")

    refs: List[str] = []
    for item in fontes:
        if not isinstance(item, dict):
            continue
        identificador = str(item.get("identificador", "N/D"))
        referencia = str(item.get("referencia", "N/D"))
        url = str(item.get("url", "")).strip()
        if url:
            refs.append(f"{identificador} - {referencia} - {url}")
        else:
            refs.append(f"{identificador} - {referencia}")

    if not refs:
        raise ValueError(f"ruleset '{ruleset_id}' invalido: fontes_oficiais vazio em metadata.json.")
    return refs


def build_audit_metadata(inp: DiagnosticInput, detalhes_regime: Dict[str, Any]) -> Dict[str, Any]:
    """Monta metadados de auditoria para rastreabilidade do calculo no relatorio e historico."""
    regime_info = canonicalize_regime(inp.regime, regime_code=inp.regime_code, regime_model=inp.regime_model)
    regime_code = regime_info["regime_code"]
    regime_model = regime_info["regime_model"]
    ruleset_id = _resolve_ruleset_id(detalhes_regime, inp)

    assumptions: List[str] = [
        "Valores tratados como anuais; periodicidade registrada, mas a matematica ainda e anual.",
        "Adicional IRPJ aplica limite conforme periodicidade (mensal/trimestral/anual); calculo ainda usa base anual (aproximacao).",
    ]
    limitations: List[str] = [
        "Nao cobre excecoes setoriais (monofasico, ST, aliquota zero, regimes especiais).",
        "Nao calcula creditos de PIS/COFINS (nao cumulativo).",
        "Nao valida elegibilidade completa de regimes.",
        "Apuracao por periodo (mensal/trimestral) para toda a matematica tributaria ainda esta em roadmap.",
    ]
    alerts: List[str] = []

    origem_evento = detalhes_regime.get("origem_evento") if isinstance(detalhes_regime, dict) else None
    origem_evento_text = origem_evento.strip() if isinstance(origem_evento, str) else ""

    if regime_code == REGIME_CODE_SIMPLES and regime_model == REGIME_MODEL_TABELADO:
        assumptions.extend(
            [
                "Simples: calculo tabelado por anexo/faixa com base no RBT12 informado.",
                "Fator R e aplicado apenas quando o anexo informado e III/V.",
                "Se receita_base_periodo nao for informada, usa-se a receita anual como base de calculo.",
            ]
        )
    elif regime_code == REGIME_CODE_SIMPLES and regime_model == REGIME_MODEL_MANUAL:
        assumptions.append("Evento legado/manual: aliquota efetiva informada manualmente no historico.")
        if not origem_evento_text:
            alerts.append("Origem do evento: legado/manual (migração).")
    elif regime_code == REGIME_CODE_PRESUMIDO:
        assumptions.append("Lucro Presumido utiliza percentuais por tipo de atividade conforme ruleset.")
    elif regime_code == REGIME_CODE_REAL:
        assumptions.append("Lucro Real estimado por margem (nao substitui apuracao contabil/fiscal).")
        assumptions.append("PIS/COFINS nao cumulativo aplicado sobre base de receita do periodo (ou receita anual quando nao informada).")
        criterio_credito = (
            detalhes_regime.get("criterio_credito_pis_cofins")
            if isinstance(detalhes_regime, dict)
            else None
        )
        if criterio_credito == "nao_informado_assumido_zero":
            assumptions.append("Creditos de PIS/COFINS nao informados; assumidos como zero.")
        else:
            assumptions.append("Creditos de PIS/COFINS estimados conforme dados de entrada informados.")
        if bool(detalhes_regime.get("credito_limitado_ao_debito", False)):
            alerts.append(
                "Crédito de PIS/COFINS informado excede o débito; crédito foi limitado ao débito para evitar valor negativo."
            )
        limitations.append("Creditos dependem da estrutura de custos/insumos e documentacao fiscal; estimativa simplificada.")

    alerta_elegibilidade = detalhes_regime.get("alerta_elegibilidade") if isinstance(detalhes_regime, dict) else None
    if isinstance(alerta_elegibilidade, str) and alerta_elegibilidade.strip():
        alerts.append(alerta_elegibilidade.strip())

    if origem_evento_text:
        if origem_evento_text.endswith("."):
            alerts.append(f"Origem do evento: {origem_evento_text}")
        else:
            alerts.append(f"Origem do evento: {origem_evento_text}.")

    profile_assumptions = detalhes_regime.get("profile_assumptions") if isinstance(detalhes_regime, dict) else None
    if isinstance(profile_assumptions, list):
        assumptions.extend(str(item) for item in profile_assumptions if str(item).strip())

    recommendation_snapshot = detalhes_regime.get("recommendation_snapshot") if isinstance(detalhes_regime, dict) else None
    if isinstance(recommendation_snapshot, dict):
        mode = recommendation_snapshot.get("modo")
        status = recommendation_snapshot.get("status")
        assumptions.append(f"Recomendação executada em modo: {mode}.")
        if status == "NEGADA":
            alerts.append("Recomendação conservadora negada por elegibilidade/insuficiência de dados.")

    integrity = get_integrity_summary(ruleset_id)
    if integrity.get("status") != "PASS":
        alerts.append("Integridade do ruleset/baseline em FAIL. Verificar auditoria de compliance.")

    # Mantem alertas unicos preservando ordem.
    alerts = list(dict.fromkeys(alerts))

    return {
        "ruleset_id": ruleset_id,
        "ruleset_metadata": _load_ruleset_metadata_subset(ruleset_id),
        "as_of_date": date.today().isoformat(),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "calculo_tipo": _calculo_tipo_por_regime(regime_code, regime_model),
        "sources": _sources_por_regime(regime_code, regime_model, ruleset_id),
        "references": _references_from_metadata(ruleset_id),
        "integrity": integrity,
        "assumptions": assumptions,
        "limitations": limitations,
        "alerts": alerts,
    }
