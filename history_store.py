import json
import os
from datetime import datetime
from typing import Any, Dict, List

from audit_metadata import build_audit_metadata
from dto import DiagnosticInput
from report_formatters import (
    render_comparativo_section,
    render_detalhes_regime,
    render_eligibilidade_section,
    render_recomendacao_section,
)
from ruleset_loader import DEFAULT_RULESET_ID, get_simples_tables
from regime_utils import (
    REGIME_CODE_SIMPLES,
    REGIME_MODEL_MANUAL,
    REGIME_MODEL_TABELADO,
    canonicalize_regime,
)
from report_builder import montar_relatorio_executivo

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TRIBUTOS_DAS = ("IRPJ", "CSLL", "PIS", "COFINS", "CPP", "ICMS", "ISS")


def _history_path(pasta: str = "data", arquivo: str = "history.jsonl") -> str:
    return os.path.join(BASE_DIR, pasta, arquivo)


def append_event(event: Dict[str, Any], pasta: str = "data", arquivo: str = "history.jsonl") -> str:
    caminho = _history_path(pasta=pasta, arquivo=arquivo)
    os.makedirs(os.path.dirname(caminho), exist_ok=True)

    payload = {
        **event,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }

    with open(caminho, "a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")

    return caminho


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _bloco_partilha_simples(detalhes_regime: Dict[str, Any]) -> str:
    linhas = ["=== SIMPLES NACIONAL — PARTILHA DO DAS (ESTIMATIVA) ==="]
    percentuais = detalhes_regime.get("breakdown_percentuais")
    valores = detalhes_regime.get("breakdown_das")

    if not isinstance(percentuais, dict) or not isinstance(valores, dict):
        linhas.append("partilha indisponível (evento legado)")
        return "\n".join(linhas) + "\n"

    linhas.append("Tributo | Percentual | Valor (R$)")
    linhas.append("-----------------------------------")
    for tributo in TRIBUTOS_DAS:
        p = _to_float(percentuais.get(tributo))
        v = _to_float(valores.get(tributo))
        linhas.append(f"{tributo} | {round(p * 100, 4)}% | R$ {v:,.2f}")
    return "\n".join(linhas) + "\n"


def _reconstruir_partilha_simples_refresh(payload: Dict[str, Any], detalhes_regime: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(detalhes_regime, dict):
        return detalhes_regime
    if detalhes_regime.get("regime_code") != REGIME_CODE_SIMPLES:
        return detalhes_regime
    if detalhes_regime.get("regime_model") != REGIME_MODEL_TABELADO:
        return detalhes_regime
    if isinstance(detalhes_regime.get("breakdown_percentuais"), dict) and isinstance(detalhes_regime.get("breakdown_das"), dict):
        return detalhes_regime

    ruleset_id = str(detalhes_regime.get("ruleset_id") or DEFAULT_RULESET_ID)
    tabelas = get_simples_tables(ruleset_id)
    anexos = tabelas.get("anexos")
    if not isinstance(anexos, dict):
        return detalhes_regime

    anexo = str(detalhes_regime.get("anexo_aplicado") or detalhes_regime.get("anexo_informado") or "").strip().upper()
    if anexo not in anexos:
        return detalhes_regime
    faixas = anexos.get(anexo)
    if not isinstance(faixas, list) or not faixas:
        return detalhes_regime

    faixa_idx: int | None = None
    faixa_raw = detalhes_regime.get("faixa")
    if isinstance(faixa_raw, (int, float)):
        idx = int(faixa_raw) - 1
        if 0 <= idx < len(faixas):
            faixa_idx = idx
    if faixa_idx is None:
        rbt12 = _to_float(detalhes_regime.get("rbt12"))
        for idx, faixa_obj in enumerate(faixas):
            if not isinstance(faixa_obj, dict):
                continue
            limite = faixa_obj.get("limite_superior")
            if isinstance(limite, (int, float)) and rbt12 <= float(limite):
                faixa_idx = idx
                break
    if faixa_idx is None:
        return detalhes_regime

    faixa_obj = faixas[faixa_idx]
    if not isinstance(faixa_obj, dict):
        return detalhes_regime
    percentuais_raw = faixa_obj.get("percentuais_partilha")
    if not isinstance(percentuais_raw, dict):
        return detalhes_regime

    percentuais: Dict[str, float] = {}
    for tributo in TRIBUTOS_DAS:
        val = percentuais_raw.get(tributo)
        if not isinstance(val, (int, float)):
            return detalhes_regime
        num = float(val)
        if num < 0:
            return detalhes_regime
        percentuais[tributo] = num

    soma = sum(percentuais.values())
    if abs(soma - 1.0) > 1e-6:
        return detalhes_regime

    imposto_total = _to_float(payload.get("imposto_atual"))
    breakdown_das = {k: imposto_total * v for k, v in percentuais.items()}
    detalhes_regime["breakdown_percentuais"] = percentuais
    detalhes_regime["breakdown_das"] = breakdown_das
    detalhes_regime["partilha_reconstruida_no_refresh"] = True
    return detalhes_regime


def _bloco_periodo_detalhes(detalhes_regime: Dict[str, Any]) -> str:
    linhas: List[str] = []
    periodicidade = detalhes_regime.get("periodicidade")
    competencia = detalhes_regime.get("competencia")
    if periodicidade is not None:
        linhas.append(f"Periodicidade considerada: {periodicidade}")
    if competencia is not None:
        linhas.append(f"Competência: {competencia}")
    if not linhas:
        return ""
    return "\n".join(linhas) + "\n"


def _formatar_data_hora_br(iso_text: Any) -> str | None:
    if not iso_text:
        return None
    try:
        dt = datetime.fromisoformat(str(iso_text))
    except (TypeError, ValueError):
        return None
    return dt.strftime("%d/%m/%Y %H:%M:%S")


def _bloco_auditoria(audit: Dict[str, Any]) -> str:
    ruleset_metadata = audit.get("ruleset_metadata") if isinstance(audit.get("ruleset_metadata"), dict) else {}
    ruleset_id = str(audit.get("ruleset_id", ruleset_metadata.get("ruleset_id", "N/D")))
    vigencia_inicio = ruleset_metadata.get("vigencia_inicio", "N/D")
    vigencia_fim = ruleset_metadata.get("vigencia_fim", "N/D")
    descricao_ruleset = ruleset_metadata.get("descricao", "N/D")
    as_of_date = str(audit.get("as_of_date", "N/D"))
    calculo_tipo = str(audit.get("calculo_tipo", "N/D"))
    generated_at = str(audit.get("generated_at", "N/D"))

    integrity = audit.get("integrity") if isinstance(audit.get("integrity"), dict) else {}
    integrity_status = integrity.get("status", "N/D")
    integrity_ruleset_hash = integrity.get("ruleset_hash", "N/D")
    integrity_baseline_hash = integrity.get("baseline_hash", "N/D")
    checked_files = integrity.get("checked_files", []) if isinstance(integrity.get("checked_files"), list) else []

    sources = audit.get("sources") if isinstance(audit.get("sources"), list) else []
    references = audit.get("references") if isinstance(audit.get("references"), list) else []
    assumptions = audit.get("assumptions") if isinstance(audit.get("assumptions"), list) else []
    limitations = audit.get("limitations") if isinstance(audit.get("limitations"), list) else []
    alerts = audit.get("alerts") if isinstance(audit.get("alerts"), list) else []

    linhas = [
        "=== AUDITORIA (BASE NORMATIVA & PREMISSAS) ===",
        f"Ruleset: {ruleset_id}",
        f"Vigência: {vigencia_inicio} até {vigencia_fim}",
        f"Descrição do ruleset: {descricao_ruleset}",
        f"As of date: {as_of_date}",
        f"Tipo de cálculo: {calculo_tipo}",
        f"Gerado em (ISO): {generated_at}",
        f"Integridade ruleset/baseline: {integrity_status}",
        f"Hash ruleset: {integrity_ruleset_hash}",
        f"Hash baseline: {integrity_baseline_hash}",
        f"Arquivos verificados: {', '.join(checked_files) if checked_files else 'N/D'}",
        "Fontes:",
    ]
    linhas.extend(f"- {s}" for s in sources)
    if references:
        linhas.append("Referências oficiais:")
        linhas.extend(f"- {r}" for r in references)
    linhas.append("Premissas:")
    linhas.extend(f"- {s}" for s in assumptions)
    linhas.append("Limitações:")
    linhas.extend(f"- {s}" for s in limitations)
    if alerts:
        linhas.append("Alertas:")
        linhas.extend(f"- {s}" for s in alerts)
    return "\n".join(linhas)


def _rodape_relatorio(audit: Dict[str, Any] | None) -> str:
    if not isinstance(audit, dict):
        return "Relatório gerado em: (não disponível — evento legado)"
    data_hora = _formatar_data_hora_br(audit.get("generated_at"))
    if not data_hora:
        return "Relatório gerado em: (não disponível — evento legado)"
    return f"Relatório gerado em: {data_hora}"


def has_audit(event: Dict[str, Any]) -> bool:
    payload = normalize_event(event)
    detalhes = payload.get("detalhes_regime", {})
    audit = detalhes.get("audit") if isinstance(detalhes, dict) else None
    if not isinstance(audit, dict):
        return False
    return bool(audit.get("ruleset_id")) and bool(audit.get("generated_at"))


def _diagnostic_input_from_event(payload: Dict[str, Any]) -> DiagnosticInput:
    detalhes = payload.get("detalhes_regime", {})
    tipo_atividade = detalhes.get("tipo_atividade_considerado")
    if isinstance(tipo_atividade, str) and tipo_atividade.strip().lower() in ("nao informado", "não informado", ""):
        tipo_atividade = None

    competencia = detalhes.get("competencia")
    if isinstance(competencia, str) and competencia.strip().lower() in ("nao informada", "não informada", ""):
        competencia = None

    aliquota_simples = detalhes.get("aliquota_efetiva")
    margem_lucro = detalhes.get("margem_lucro_estimada")
    try:
        aliquota_simples = float(aliquota_simples) if aliquota_simples is not None else None
    except (TypeError, ValueError):
        aliquota_simples = None
    try:
        margem_lucro = float(margem_lucro) if margem_lucro is not None else None
    except (TypeError, ValueError):
        margem_lucro = None

    rbt12 = detalhes.get("rbt12")
    receita_base_periodo = detalhes.get("receita_base_periodo")
    fator_r = detalhes.get("fator_r")
    folha_12m = detalhes.get("folha_12m")
    despesas_creditaveis = detalhes.get("despesas_creditaveis")
    percentual_credito_estimado = detalhes.get("percentual_credito_estimado")

    try:
        rbt12 = float(rbt12) if rbt12 is not None else None
    except (TypeError, ValueError):
        rbt12 = None
    try:
        receita_base_periodo = float(receita_base_periodo) if receita_base_periodo is not None else None
    except (TypeError, ValueError):
        receita_base_periodo = None
    try:
        fator_r = float(fator_r) if fator_r is not None else None
    except (TypeError, ValueError):
        fator_r = None
    try:
        folha_12m = float(folha_12m) if folha_12m is not None else None
    except (TypeError, ValueError):
        folha_12m = None
    try:
        despesas_creditaveis = float(despesas_creditaveis) if despesas_creditaveis is not None else None
    except (TypeError, ValueError):
        despesas_creditaveis = None
    try:
        percentual_credito_estimado = (
            float(percentual_credito_estimado) if percentual_credito_estimado is not None else None
        )
    except (TypeError, ValueError):
        percentual_credito_estimado = None

    anexo_simples = detalhes.get("anexo_informado") or detalhes.get("anexo_aplicado")
    anexo_simples = str(anexo_simples) if isinstance(anexo_simples, str) else None
    ruleset_id = detalhes.get("ruleset_id")
    ruleset_id = str(ruleset_id) if isinstance(ruleset_id, str) else None

    return DiagnosticInput(
        nome_empresa=str(payload.get("nome_empresa", "")),
        receita_anual=_to_float(payload.get("receita_anual")),
        regime=str(payload.get("regime", "")),
        regime_code=str(detalhes.get("regime_code")) if detalhes.get("regime_code") else None,
        regime_model=str(detalhes.get("regime_model")) if detalhes.get("regime_model") else None,
        aliquota_simples=aliquota_simples,
        margem_lucro=margem_lucro,
        tipo_atividade=tipo_atividade if isinstance(tipo_atividade, str) else None,
        rbt12=rbt12,
        receita_base_periodo=receita_base_periodo,
        anexo_simples=anexo_simples,
        fator_r=fator_r,
        folha_12m=folha_12m,
        despesas_creditaveis=despesas_creditaveis,
        percentual_credito_estimado=percentual_credito_estimado,
        periodicidade=str(detalhes.get("periodicidade", "anual")),
        competencia=competencia if isinstance(competencia, str) else None,
        ruleset_id=ruleset_id,
        modo_analise=str(detalhes.get("modo_analise")) if detalhes.get("modo_analise") else "conservador",
        cenarios=None,
    )


def build_refreshed_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Monta novo payload de evento com relatorio_texto regenerado no formato atual.
    Nao recalcula imposto: reusa os dados persistidos do proprio evento.
    """
    payload = normalize_event(event)
    refreshed = dict(payload)
    detalhes = dict(refreshed.get("detalhes_regime", {}))

    legacy_original = str(refreshed.get("regime_original", "")).lower()
    if "simples nacional (v1" in legacy_original:
        detalhes["origem_evento"] = "legado/manual (migração)"
        detalhes["regime_model"] = REGIME_MODEL_MANUAL

    if "simples nacional (v2" in legacy_original or detalhes.get("regime_model") == REGIME_MODEL_TABELADO:
        detalhes = _reconstruir_partilha_simples_refresh(refreshed, detalhes)

    refreshed["regime"] = detalhes.get("regime_display", refreshed.get("regime", ""))
    refreshed["detalhes_regime"] = detalhes

    inp = _diagnostic_input_from_event(refreshed)
    refreshed["detalhes_regime"]["audit"] = build_audit_metadata(inp, refreshed["detalhes_regime"])
    refreshed["relatorio_texto"] = build_report_from_event(refreshed)
    refreshed["evento_tipo"] = "report_refresh"
    return refreshed


def normalize_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normaliza eventos antigos/novos para um contrato unico consumivel na UI.
    Mantem compatibilidade com chaves historicas (cenarios) e atuais (resultados).
    """
    payload = dict(event or {})
    resultados = payload.get("resultados")
    cenarios = payload.get("cenarios")

    if not isinstance(resultados, list):
        resultados = cenarios if isinstance(cenarios, list) else []
    if not isinstance(cenarios, list):
        cenarios = resultados

    payload["resultados"] = resultados
    payload["cenarios"] = cenarios

    payload.setdefault("timestamp", "")
    payload.setdefault("nome_empresa", "")
    payload["receita_anual"] = _to_float(payload.get("receita_anual"))
    payload["imposto_atual"] = _to_float(payload.get("imposto_atual"))

    detalhes = payload.get("detalhes_regime")
    detalhes = detalhes if isinstance(detalhes, dict) else {}

    regime_original = payload.get("regime", "")
    regime_info = canonicalize_regime(regime_original, detalhes.get("regime_code"), detalhes.get("regime_model"))

    if isinstance(regime_original, str) and regime_original.strip() and regime_original.strip() != regime_info["regime_display"]:
        payload["regime_original"] = regime_original

    detalhes.setdefault("regime_code", regime_info["regime_code"])
    detalhes.setdefault("regime_model", regime_info["regime_model"])
    detalhes.setdefault("regime_display", regime_info["regime_display"])

    payload["regime"] = regime_info["regime_display"]
    payload["detalhes_regime"] = detalhes
    return payload


def build_report_from_event(event: Dict[str, Any]) -> str:
    """
    Reconstrói relatório textual a partir do evento salvo, sem recalcular cenários.
    """
    payload = normalize_event(event)
    resultados = payload.get("resultados", [])

    relatorio = montar_relatorio_executivo(
        nome_empresa=payload.get("nome_empresa", ""),
        receita_anual=_to_float(payload.get("receita_anual")),
        aliquota_atual=0.0,
        imposto_atual=_to_float(payload.get("imposto_atual")),
        resultados=resultados,
    )

    regime = payload.get("regime", "")
    detalhes = payload.get("detalhes_regime", {})
    regime_code = detalhes.get("regime_code")
    regime_model = detalhes.get("regime_model")

    if regime:
        cab = f"\nRegime atual: {regime}\n"
        cab += _bloco_periodo_detalhes(detalhes)
        cab += render_detalhes_regime(str(regime_code or ""), detalhes)
        if regime_code == REGIME_CODE_SIMPLES and regime_model == REGIME_MODEL_TABELADO:
            cab += _bloco_partilha_simples(detalhes)
        if regime_code == REGIME_CODE_SIMPLES and regime_model == REGIME_MODEL_MANUAL:
            cab += _bloco_partilha_simples(detalhes)
        relatorio = relatorio.replace("Receita anual informada:", cab + "Receita anual informada:", 1)

    eligibility_snapshot = detalhes.get("eligibility_snapshot") if isinstance(detalhes, dict) else None
    comparison_snapshot = detalhes.get("comparison_snapshot") if isinstance(detalhes, dict) else None
    recommendation_snapshot = detalhes.get("recommendation_snapshot") if isinstance(detalhes, dict) else None
    if isinstance(eligibility_snapshot, dict):
        relatorio += "\n\n" + render_eligibilidade_section(eligibility_snapshot)
    if isinstance(comparison_snapshot, list):
        relatorio += "\n\n" + render_comparativo_section(comparison_snapshot)
    if isinstance(recommendation_snapshot, dict):
        relatorio += "\n\n" + render_recomendacao_section(recommendation_snapshot)

    audit = detalhes.get("audit") if isinstance(detalhes, dict) else None
    if isinstance(audit, dict):
        integrity = audit.get("integrity") if isinstance(audit.get("integrity"), dict) else {}
        if integrity.get("status") == "FAIL":
            relatorio = "ALERTA DE INTEGRIDADE: ruleset/baseline com divergencia (compliance FAIL).\n\n" + relatorio
        relatorio += "\n\n" + _bloco_auditoria(audit)
    relatorio += "\n" + _rodape_relatorio(audit if isinstance(audit, dict) else None)
    return relatorio


def get_event_report_text(event: Dict[str, Any]) -> str:
    """
    Retorna relatório salvo quando disponível; caso contrário, reconstrói pelos dados persistidos.
    """
    payload = normalize_event(event)
    texto = payload.get("relatorio_texto")
    if isinstance(texto, str) and texto.strip():
        return texto
    return build_report_from_event(payload)


def list_events(limit: int = 50, pasta: str = "data", arquivo: str = "history.jsonl") -> List[Dict[str, Any]]:
    caminho = _history_path(pasta=pasta, arquivo=arquivo)
    if not os.path.exists(caminho):
        return []

    with open(caminho, "r", encoding="utf-8") as f:
        linhas = [l.strip() for l in f.readlines() if l.strip()]

    eventos: List[Dict[str, Any]] = []
    for linha in linhas[-limit:]:
        try:
            eventos.append(normalize_event(json.loads(linha)))
        except json.JSONDecodeError:
            continue

    eventos.reverse()  # mais recentes primeiro
    return eventos
