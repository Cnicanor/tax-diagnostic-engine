from __future__ import annotations

from typing import Any, Dict, List, Optional

from company_profile import CompanyProfile, MODO_CONSERVADOR, MODO_ESTRATEGICO


def _row_label(row: Dict[str, Any]) -> str:
    return str(row.get("regime_display", row.get("regime_code", "Regime")))


def _as_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _dedupe(items: List[str]) -> List[str]:
    return list(dict.fromkeys([str(item) for item in items if str(item).strip()]))


def _excluded_entry(row: Dict[str, Any], reason: str) -> Dict[str, str]:
    return {
        "regime": _row_label(row),
        "status": str(row.get("eligibility_status", "N/D")),
        "reason": reason,
    }


def _next_steps_from_alerts(alerts: List[str], regime_code: str) -> List[str]:
    steps: List[str] = []
    alert_text = " | ".join(alerts).lower()
    if "tipo de atividade" in alert_text:
        steps.append("Informar tipo_atividade para reduzir incerteza no Presumido.")
    if "anexo do simples" in alert_text:
        steps.append("Informar anexo_simples para validar elegibilidade/cenario do Simples.")
    if "fator_r" in alert_text or "folha_12m" in alert_text:
        steps.append("Informar fator_r ou folha_12m para Simples III/V.")
    if regime_code == "REAL" and "credito" in alert_text:
        steps.append("Informar despesas_creditaveis ou percentual_credito_estimado no Lucro Real.")
    return steps


def recommend_conservative(profile: CompanyProfile, comparison: Dict[str, Any]) -> Dict[str, Any]:
    rows = comparison.get("rows", []) if isinstance(comparison.get("rows"), list) else []
    conservative_candidates: List[Dict[str, Any]] = []
    not_recommended_reasons: List[str] = []
    faltantes: List[str] = []
    excluded_regimes: List[Dict[str, str]] = []

    for row in rows:
        status = str(row.get("eligibility_status", ""))
        critical = row.get("critical_alerts", [])
        imposto = _as_float(row.get("imposto_total"))
        alerts = [str(a) for a in row.get("alerts", [])] if isinstance(row.get("alerts"), list) else []

        if status == "OK" and not critical and isinstance(imposto, float):
            conservative_candidates.append(row)
            continue

        label = _row_label(row)
        if alerts:
            not_recommended_reasons.append(f"{label}: {'; '.join(str(a) for a in alerts)}")
            faltantes.extend(str(a) for a in alerts)
            excluded_regimes.append(_excluded_entry(row, "; ".join(alerts)))
        else:
            reason = f"Elegibilidade nao OK ({status})."
            not_recommended_reasons.append(f"{label}: {reason}")
            excluded_regimes.append(_excluded_entry(row, reason))

    if not conservative_candidates:
        faltantes = _dedupe(faltantes)
        return {
            "modo": MODO_CONSERVADOR,
            "status": "NEGADA",
            "candidate_policy": "OK_only",
            "regime_recomendado": None,
            "justificativa": [
                "Nao posso recomendar com seguranca no modo conservador.",
                "No modo conservador, apenas regimes com elegibilidade OK entram como candidatos. Regimes com WARNING/BLOCKED sao excluidos.",
                "Faltam dados obrigatorios ou ha bloqueios de elegibilidade.",
            ],
            "excluded_regimes": excluded_regimes,
            "por_que_nao_outros": not_recommended_reasons,
            "faltantes": faltantes,
            "proximos_passos": [
                "Completar dados faltantes do regime bloqueado.",
                "Reexecutar comparativo apos saneamento de elegibilidade.",
            ],
        }

    escolhido = min(conservative_candidates, key=lambda r: float(r["imposto_total"]))
    escolhido_label = _row_label(escolhido)

    por_que_nao_outros: List[str] = []
    for row in rows:
        if row is escolhido:
            continue
        label = _row_label(row)
        imposto = _as_float(row.get("imposto_total"))
        if imposto is None:
            por_que_nao_outros.append(f"{label}: sem calculo por bloqueio/insuficiencia de dados.")
            continue
        if float(row["imposto_total"]) >= float(escolhido["imposto_total"]):
            por_que_nao_outros.append(
                f"{label}: imposto estimado maior ou igual ao recomendado ({float(row['imposto_total']):,.2f})."
            )
        else:
            status = str(row.get("eligibility_status", "N/D"))
            if status != "OK":
                por_que_nao_outros.append(
                    f"{label}: imposto menor, mas excluido por politica conservadora (status {status})."
                )

    return {
        "modo": MODO_CONSERVADOR,
        "status": "RECOMENDADA",
        "candidate_policy": "OK_only",
        "regime_recomendado": escolhido.get("regime_code"),
        "regime_recomendado_display": escolhido_label,
        "justificativa": [
            "No modo conservador, apenas regimes com elegibilidade OK entram como candidatos. Regimes com WARNING/BLOCKED sao excluidos.",
            "Regime elegivel com menor imposto estimado entre candidatos seguros.",
            f"Regime recomendado: {escolhido_label}.",
        ],
        "excluded_regimes": excluded_regimes,
        "por_que_nao_outros": por_que_nao_outros,
        "faltantes": [],
        "proximos_passos": [
            "Validar premissas com documentacao fiscal real antes da decisao final.",
        ],
    }


def recommend_strategic(profile: CompanyProfile, comparison: Dict[str, Any]) -> Dict[str, Any]:
    rows = comparison.get("rows", []) if isinstance(comparison.get("rows"), list) else []
    candidates: List[Dict[str, Any]] = []
    excluded_regimes: List[Dict[str, str]] = []
    next_steps: List[str] = []
    faltantes: List[str] = list(profile.missing_inputs)

    for row in rows:
        status = str(row.get("eligibility_status", "N/D"))
        regime_display = _row_label(row)
        regime_code = str(row.get("regime_code", ""))
        imposto = _as_float(row.get("imposto_total"))
        carga = _as_float(row.get("carga_efetiva_percentual"))
        alerts = [str(a) for a in row.get("alerts", [])] if isinstance(row.get("alerts"), list) else []

        if status == "BLOCKED" or imposto is None:
            reason = "; ".join(alerts) if alerts else f"Elegibilidade {status}."
            excluded_regimes.append(_excluded_entry(row, reason))
            faltantes.extend(alerts)
            next_steps.extend(_next_steps_from_alerts(alerts, regime_code))
            continue

        candidates.append(
            {
                "regime_code": regime_code,
                "regime_display": regime_display,
                "status_elegibilidade": status,
                "imposto_total": imposto,
                "carga_efetiva": carga,
                "alerts": alerts,
                "detalhes_regime": row.get("detalhes_regime", {}),
            }
        )

    if not candidates:
        return {
            "modo": MODO_ESTRATEGICO,
            "status": "INCONCLUSIVA",
            "candidate_policy": "OK_and_WARNING",
            "ranking": [],
            "excluded_regimes": excluded_regimes,
            "justificativa": [
                "Nao ha regimes com dados suficientes para ranking estrategico.",
                "Todos os regimes estao BLOCKED ou sem calculo valido.",
            ],
            "next_steps": _dedupe(next_steps + ["Revisar elegibilidade e completar campos obrigatorios."]),
            "faltantes": _dedupe(faltantes),
        }

    min_imposto = min(c["imposto_total"] for c in candidates)
    for candidate in candidates:
        score = 100.0
        tradeoffs: List[str] = []
        imposto = candidate["imposto_total"]
        status = candidate["status_elegibilidade"]
        alerts = candidate["alerts"]
        regime_code = candidate["regime_code"]

        score -= ((imposto - min_imposto) / max(min_imposto, 1.0)) * 60.0
        if status == "WARNING":
            score -= 20.0
            tradeoffs.append("Elegibilidade WARNING: requer validacao adicional.")
        if alerts:
            score -= min(20.0, float(len(alerts) * 5))
            tradeoffs.append(f"Alertas ativos: {'; '.join(alerts)}")
            faltantes.extend(alerts)
            next_steps.extend(_next_steps_from_alerts(alerts, regime_code))

        detalhes = candidate.get("detalhes_regime")
        if isinstance(detalhes, dict) and regime_code == "REAL":
            criterio = str(detalhes.get("criterio_credito_pis_cofins", "")).strip()
            if criterio in ("despesas_creditaveis", "percentual_credito_estimado"):
                score -= 8.0
                tradeoffs.append("Credito de PIS/COFINS estimado adiciona risco de variacao.")
                next_steps.append("Conferir memoria de calculo de creditos no Lucro Real.")
            if criterio == "nao_informado_assumido_zero":
                tradeoffs.append("Credito de PIS/COFINS assumido como zero.")
                next_steps.append("Informar despesas_creditaveis para calibrar creditos no Lucro Real.")

        candidate["score"] = round(score, 2)
        candidate["tradeoffs"] = tradeoffs

    ranking_sorted = sorted(candidates, key=lambda c: (-float(c["score"]), float(c["imposto_total"])))

    missing_critical = bool(profile.missing_inputs)
    all_warning = all(str(item.get("status_elegibilidade")) == "WARNING" for item in ranking_sorted)
    inconclusiva = all_warning and missing_critical

    if inconclusiva:
        return {
            "modo": MODO_ESTRATEGICO,
            "status": "INCONCLUSIVA",
            "candidate_policy": "OK_and_WARNING",
            "ranking": ranking_sorted,
            "excluded_regimes": excluded_regimes,
            "justificativa": [
                "Ranking estrategico calculado, mas faltam campos criticos para recomendacao condicional segura.",
            ],
            "next_steps": _dedupe(next_steps + ["Completar campos criticos antes de decidir."]),
            "faltantes": _dedupe(faltantes),
        }

    top = ranking_sorted[0]
    return {
        "modo": MODO_ESTRATEGICO,
        "status": "CONDICIONAL",
        "candidate_policy": "OK_and_WARNING",
        "regime_recomendado": top.get("regime_code"),
        "regime_recomendado_display": top.get("regime_display"),
        "ranking": ranking_sorted,
        "excluded_regimes": excluded_regimes,
        "justificativa": [
            "Recomendacao condicional baseada em ranking economico com penalidades de risco/compliance.",
            f"Top 1 estrategico: {top.get('regime_display')}.",
        ],
        "next_steps": _dedupe(next_steps + ["Validar o Top 1 com evidencias fiscais antes da decisao final."]),
        "faltantes": _dedupe(faltantes),
    }


def build_recommendation(profile: CompanyProfile, comparison: Dict[str, Any]) -> Dict[str, Any]:
    if profile.modo_analise == MODO_ESTRATEGICO:
        return recommend_strategic(profile, comparison)
    return recommend_conservative(profile, comparison)
