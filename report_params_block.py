from __future__ import annotations

from typing import Any, Dict, List

from regime_utils import REGIME_CODE_PRESUMIDO, REGIME_CODE_REAL, REGIME_CODE_SIMPLES, REGIME_MODEL_MANUAL


def _to_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _fmt_currency(value: Any) -> str | None:
    numeric = _to_float(value)
    if numeric is None:
        return None
    return f"R$ {numeric:,.2f}"


def _fmt_percent(value: Any, casas: int = 2) -> str | None:
    numeric = _to_float(value)
    if numeric is None:
        return None
    return f"{numeric * 100:.{casas}f}%"


def _append_if(lines: List[str], label: str, value: str | None) -> None:
    if value is None:
        return
    text = str(value).strip()
    if not text:
        return
    lines.append(f"{label}: {text}")


def _rotulo_tipo_atividade(tipo: Any) -> str:
    valor = str(tipo or "").strip()
    mapa = {
        "Comercio": "Comércio",
        "Industria": "Indústria",
        "Servicos (geral)": "Serviços (geral)",
        "Outros": "Outros",
        "Nao informado": "Não informado",
        "Não informado": "Não informado",
    }
    if not valor:
        return "Não informado"
    return mapa.get(valor, valor)


def _rotulo_base_pis_cofins(chave: Any) -> str:
    raw = str(chave or "").strip()
    if raw == "receita_base_periodo":
        return "Receita base do período"
    if raw == "receita_anual":
        return "Receita anual"
    return raw or "Receita anual"


def _bloco_parametros_tecnicos(detalhes_regime: Dict[str, Any]) -> str:
    """
    Renderiza bloco padronizado de parâmetros técnicos por regime, sem dump de dict.
    """
    regime_code = str(detalhes_regime.get("regime_code", "")).upper()
    regime_model = str(detalhes_regime.get("regime_model", "")).lower()
    lines: List[str] = ["=== PARÂMETROS DO CÁLCULO ==="]

    if regime_code == REGIME_CODE_SIMPLES:
        if regime_model == REGIME_MODEL_MANUAL:
            _append_if(lines, "Modelo", "Legado/manual (alíquota efetiva informada)")
            _append_if(lines, "Alíquota efetiva", _fmt_percent(detalhes_regime.get("aliquota_efetiva"), 4))
            return "\n".join(lines) + "\n"

        _append_if(lines, "Anexo aplicado", str(detalhes_regime.get("anexo_aplicado", "")).strip() or None)
        _append_if(lines, "Faixa", str(detalhes_regime.get("faixa", "")).strip() or None)
        _append_if(lines, "Alíquota nominal", _fmt_percent(detalhes_regime.get("aliquota_nominal"), 4))
        _append_if(lines, "Parcela a deduzir", _fmt_currency(detalhes_regime.get("parcela_deduzir")))
        _append_if(lines, "Alíquota efetiva", _fmt_percent(detalhes_regime.get("aliquota_efetiva"), 4))
        _append_if(lines, "RBT12", _fmt_currency(detalhes_regime.get("rbt12")))
        if detalhes_regime.get("fator_r") is not None:
            _append_if(lines, "Fator R", _fmt_percent(detalhes_regime.get("fator_r"), 2))
        _append_if(
            lines,
            "Limite de elegibilidade",
            _fmt_currency(detalhes_regime.get("limite_elegibilidade_simples")),
        )
        return "\n".join(lines) + "\n"

    if regime_code == REGIME_CODE_PRESUMIDO:
        _append_if(lines, "Tipo de atividade considerado", _rotulo_tipo_atividade(detalhes_regime.get("tipo_atividade_considerado")))
        _append_if(lines, "Percentual de presunção", _fmt_percent(detalhes_regime.get("percentual_presuncao")))
        _append_if(lines, "Base presumida", _fmt_currency(detalhes_regime.get("base_presumida")))
        _append_if(lines, "IRPJ", _fmt_percent(detalhes_regime.get("aliquota_irpj")))
        _append_if(lines, "CSLL", _fmt_percent(detalhes_regime.get("aliquota_csll")))
        _append_if(lines, "PIS", _fmt_percent(detalhes_regime.get("aliquota_pis")))
        _append_if(lines, "COFINS", _fmt_percent(detalhes_regime.get("aliquota_cofins")))
        _append_if(lines, "Limite adicional IRPJ", _fmt_currency(detalhes_regime.get("limite_adicional_irpj_utilizado")))
        periodicidade = detalhes_regime.get("periodicidade_aplicada_adicional_irpj") or detalhes_regime.get("periodicidade")
        _append_if(lines, "Periodicidade aplicada", str(periodicidade).strip() if periodicidade is not None else None)
        return "\n".join(lines) + "\n"

    if regime_code == REGIME_CODE_REAL:
        _append_if(lines, "Margem de lucro estimada", _fmt_percent(detalhes_regime.get("margem_lucro_estimada")))
        _append_if(lines, "IRPJ", _fmt_percent(detalhes_regime.get("irpj")))
        _append_if(lines, "CSLL", _fmt_percent(detalhes_regime.get("csll")))

        base_pis_label = _rotulo_base_pis_cofins(detalhes_regime.get("base_pis_cofins_usada"))
        base_pis_valor = _fmt_currency(detalhes_regime.get("valor_base_pis_cofins"))
        if base_pis_valor:
            _append_if(lines, "Base PIS/COFINS usada", f"{base_pis_label} ({base_pis_valor})")

        _append_if(lines, "Alíquota PIS", _fmt_percent(detalhes_regime.get("pis_nao_cumulativo"), 2))
        _append_if(lines, "Alíquota COFINS", _fmt_percent(detalhes_regime.get("cofins_nao_cumulativo"), 2))
        _append_if(
            lines,
            "Débito PIS/COFINS",
            _fmt_currency(detalhes_regime.get("debito_pis_cofins_nao_cumulativo")),
        )

        credito_limitado = bool(detalhes_regime.get("credito_limitado_ao_debito", False))
        if credito_limitado:
            _append_if(
                lines,
                "Crédito PIS/COFINS original",
                _fmt_currency(detalhes_regime.get("credito_pis_cofins_original")),
            )
            _append_if(
                lines,
                "Crédito PIS/COFINS utilizado",
                _fmt_currency(detalhes_regime.get("credito_pis_cofins_utilizado")),
            )
        else:
            _append_if(
                lines,
                "Crédito aplicado",
                _fmt_currency(
                    detalhes_regime.get(
                        "credito_pis_cofins_utilizado",
                        detalhes_regime.get("credito_pis_cofins"),
                    )
                ),
            )

        _append_if(
            lines,
            "Critério de crédito",
            str(detalhes_regime.get("criterio_credito_pis_cofins", "")).strip() or None,
        )
        return "\n".join(lines) + "\n"

    lines.append("Parâmetros técnicos indisponíveis para este evento.")
    return "\n".join(lines) + "\n"
