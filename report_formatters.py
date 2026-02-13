from __future__ import annotations

from typing import Any, Dict, List

from formatters import formatar_percentual, formatar_reais
from report_params_block import _bloco_parametros_tecnicos


def render_detalhes_regime(regime_code: str, detalhes_regime: Dict[str, Any]) -> str:
    payload = dict(detalhes_regime or {})
    payload.setdefault("regime_code", regime_code)
    return _bloco_parametros_tecnicos(payload)


def render_eligibilidade_section(eligibility_map: Dict[str, Any]) -> str:
    lines: List[str] = ["=== ELEGIBILIDADE ==="]
    if not isinstance(eligibility_map, dict) or not eligibility_map:
        lines.append("Sem dados de elegibilidade.")
        return "\n".join(lines)

    for regime_code, data in eligibility_map.items():
        status = str((data or {}).get("status", "N/D"))
        lines.append(f"- {regime_code}: {status}")
        reasons = data.get("reasons") if isinstance(data, dict) else None
        missing = data.get("missing_inputs") if isinstance(data, dict) else None
        if isinstance(reasons, list):
            for reason in reasons:
                lines.append(f"  motivo: {reason}")
        if isinstance(missing, list):
            for item in missing:
                lines.append(f"  faltante: {item}")
    return "\n".join(lines)


def render_comparativo_section(rows: List[Dict[str, Any]]) -> str:
    lines: List[str] = ["=== COMPARATIVO ENTRE REGIMES ==="]
    if not isinstance(rows, list) or not rows:
        lines.append("Sem dados para comparativo.")
        return "\n".join(lines)

    lines.append("Regime | Elegibilidade | Imposto | Carga Efetiva")
    lines.append("------------------------------------------------")
    for row in rows:
        regime_display = str(row.get("regime_display", row.get("regime_code", "N/D")))
        status = str(row.get("eligibility_status", "N/D"))
        imposto = row.get("imposto_total")
        carga = row.get("carga_efetiva_percentual")
        imposto_txt = formatar_reais(float(imposto)) if isinstance(imposto, (int, float)) else "N/D"
        carga_txt = formatar_percentual(float(carga), ja_percentual=True) if isinstance(carga, (int, float)) else "N/D"
        lines.append(f"{regime_display} | {status} | {imposto_txt} | {carga_txt}")

        alerts = row.get("alerts")
        if isinstance(alerts, list) and alerts:
            lines.append("  observacoes:")
            for alert in alerts:
                lines.append(f"  - {alert}")
    return "\n".join(lines)


def _render_conservative_recommendation(recommendation: Dict[str, Any]) -> str:
    lines: List[str] = ["=== RECOMENDAÇÃO (MODO CONSERVADOR) ==="]
    if not isinstance(recommendation, dict) or not recommendation:
        lines.append("Sem recomendacao disponivel.")
        return "\n".join(lines)

    status = str(recommendation.get("status", "N/D"))
    regime = recommendation.get("regime_recomendado_display") or recommendation.get("regime_recomendado")

    lines.append("Politica de candidatos: OK_only")
    lines.append(
        "No modo conservador, apenas regimes com elegibilidade OK entram como candidatos. Regimes com WARNING/BLOCKED sao excluidos."
    )
    lines.append(f"Status: {status}")
    if regime:
        lines.append(f"Regime recomendado: {regime}")

    excluded = recommendation.get("excluded_regimes")
    if isinstance(excluded, list) and excluded:
        lines.append("Regimes excluidos:")
        for item in excluded:
            if not isinstance(item, dict):
                continue
            label = str(item.get("regime", "Regime"))
            item_status = str(item.get("status", "N/D"))
            reason = str(item.get("reason", "Sem motivo informado."))
            lines.append(f"- {label} ({item_status}): {reason}")

    for key, title in (
        ("justificativa", "Justificativa"),
        ("por_que_nao_outros", "Por que nao os outros"),
        ("faltantes", "Faltantes"),
        ("proximos_passos", "Proximos passos"),
    ):
        values = recommendation.get(key)
        if isinstance(values, list) and values:
            lines.append(f"{title}:")
            for item in values:
                lines.append(f"- {item}")

    return "\n".join(lines)


def _render_strategic_recommendation(recommendation: Dict[str, Any]) -> str:
    lines: List[str] = ["=== RECOMENDAÇÃO (MODO ESTRATÉGICO) ==="]
    status = str(recommendation.get("status", "N/D"))
    lines.append(f"Status: {status}")

    ranking = recommendation.get("ranking", [])
    if not isinstance(ranking, list) or not ranking:
        lines.append("Sem ranking disponivel para o modo estrategico.")
    else:
        lines.append("Top 3 do ranking:")
        top3 = ranking[:3]
        for idx, item in enumerate(top3, start=1):
            if not isinstance(item, dict):
                continue
            regime = str(item.get("regime_display", item.get("regime_code", "Regime")))
            status_eleg = str(item.get("status_elegibilidade", "N/D"))
            imposto = item.get("imposto_total")
            carga = item.get("carga_efetiva")
            score = item.get("score")
            imposto_txt = formatar_reais(float(imposto)) if isinstance(imposto, (int, float)) else "N/D"
            carga_txt = formatar_percentual(float(carga), ja_percentual=True) if isinstance(carga, (int, float)) else "N/D"
            score_txt = formatar_percentual(float(score), ja_percentual=True) if isinstance(score, (int, float)) else "N/D"
            lines.append(
                f"{idx}. {regime} | Elegibilidade: {status_eleg} | Imposto: {imposto_txt} | Carga: {carga_txt} | Score: {score_txt}"
            )
            tradeoffs = item.get("tradeoffs")
            if isinstance(tradeoffs, list) and tradeoffs:
                for tradeoff in tradeoffs:
                    lines.append(f"   - {tradeoff}")

        top = top3[0] if top3 else None
        if isinstance(top, dict) and status != "INCONCLUSIVA":
            lines.append(
                f"Por que o #1: {top.get('regime_display')} combina menor impacto economico ajustado pelas penalidades de risco/elegibilidade."
            )

            outros = [i for i in top3[1:] if isinstance(i, dict)]
            if outros:
                motivos = ", ".join(str(i.get("regime_display", "Regime")) for i in outros)
                lines.append(f"Por que nao os outros: scores inferiores para {motivos}.")

    excluded = recommendation.get("excluded_regimes")
    if isinstance(excluded, list) and excluded:
        lines.append("Regimes nao elegiveis (fora do ranking):")
        for item in excluded:
            if not isinstance(item, dict):
                continue
            label = str(item.get("regime", "Regime"))
            item_status = str(item.get("status", "N/D"))
            reason = str(item.get("reason", "Sem motivo informado."))
            lines.append(f"- {label} ({item_status}): {reason}")

    next_steps = recommendation.get("next_steps")
    if isinstance(next_steps, list) and next_steps:
        lines.append("Proximos passos para aumentar confiabilidade:")
        for step in next_steps:
            lines.append(f"- {step}")

    faltantes = recommendation.get("faltantes")
    if isinstance(faltantes, list) and faltantes:
        lines.append("Faltantes relevantes:")
        for item in faltantes:
            lines.append(f"- {item}")

    return "\n".join(lines)


def render_recomendacao_section(recommendation: Dict[str, Any]) -> str:
    if not isinstance(recommendation, dict) or not recommendation:
        return "=== RECOMENDAÇÃO (MODO CONSERVADOR) ===\nSem recomendacao disponivel."
    modo = str(recommendation.get("modo", "conservador")).strip().lower()
    if modo == "estrategico":
        return _render_strategic_recommendation(recommendation)
    return _render_conservative_recommendation(recommendation)
