from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

TRIBUTOS_DAS = ("IRPJ", "CSLL", "PIS", "COFINS", "CPP", "ICMS", "ISS")
PARTILHA_SOMA_TOLERANCIA = 1e-6


def _ruleset_error(
    ruleset_id: str,
    arquivo: str,
    chave: str,
    regime: str,
    impacto: str,
    detalhe: str = "",
) -> ValueError:
    msg = (
        f"ruleset_id={ruleset_id} | arquivo={arquivo} | chave={chave} | "
        f"regime={regime} | impacto={impacto}"
    )
    if detalhe:
        msg += f" | detalhe={detalhe}"
    return ValueError(msg)


def _required_number(
    payload: Dict[str, Any],
    key: str,
    *,
    ruleset_id: str,
    arquivo: str,
    regime: str,
    impacto: str,
) -> float:
    if key not in payload:
        raise _ruleset_error(ruleset_id, arquivo, key, regime, impacto, "chave ausente")
    value = payload[key]
    if not isinstance(value, (int, float)):
        raise _ruleset_error(ruleset_id, arquivo, key, regime, impacto, "valor nao numerico")
    return float(value)


def _required_object(
    payload: Dict[str, Any],
    key: str,
    *,
    ruleset_id: str,
    arquivo: str,
    regime: str,
    impacto: str,
) -> Dict[str, Any]:
    if key not in payload:
        raise _ruleset_error(ruleset_id, arquivo, key, regime, impacto, "chave ausente")
    value = payload[key]
    if not isinstance(value, dict):
        raise _ruleset_error(ruleset_id, arquivo, key, regime, impacto, "objeto invalido")
    return value


def presuncao_por_tipo_atividade(
    tipo: Optional[str],
    percentual_map: Dict[str, Any],
    fallback_key: str = "Comercio",
) -> float:
    """Retorna percentual de presuncao conforme tipo de atividade usando valores do ruleset."""
    if not isinstance(percentual_map, dict) or not percentual_map:
        raise ValueError("ruleset inválido: percentual_presuncao ausente ou inválido.")

    aliases = {
        "comercio": "Comercio",
        "comércio": "Comercio",
        "industria": "Industria",
        "indústria": "Industria",
        "servicos (geral)": "Servicos (geral)",
        "serviços (geral)": "Servicos (geral)",
        "servicos": "Servicos (geral)",
        "serviços": "Servicos (geral)",
        "outros": "Outros",
        "outro": "Outros",
    }

    if not tipo:
        if fallback_key not in percentual_map:
            raise ValueError(f"ruleset inválido: chave de fallback '{fallback_key}' ausente em percentual_presuncao.")
        return float(percentual_map[fallback_key])

    canonico = aliases.get(tipo.strip().lower(), tipo)
    if canonico in percentual_map:
        return float(percentual_map[canonico])

    if fallback_key not in percentual_map:
        raise ValueError(
            f"tipo_atividade '{tipo}' não mapeado e fallback '{fallback_key}' ausente no ruleset."
        )
    return float(percentual_map[fallback_key])


def imposto_simples(receita_anual: float, aliquota_efetiva: float) -> float:
    return receita_anual * aliquota_efetiva


def escolher_faixa_por_rbt12(tabela_anexo: List[Dict[str, Any]], rbt12: float) -> Tuple[float, float, int]:
    """Seleciona faixa do anexo do Simples com base no RBT12."""
    if rbt12 <= 0:
        raise ValueError("rbt12 deve ser maior que zero.")
    if not isinstance(tabela_anexo, list) or not tabela_anexo:
        raise ValueError("Tabela do anexo vazia.")

    for idx, faixa in enumerate(tabela_anexo, start=1):
        if not isinstance(faixa, dict):
            raise ValueError("Tabela do anexo inválida: faixa deve ser objeto.")
        limite = faixa.get("limite_superior")
        if not isinstance(limite, (int, float)):
            raise ValueError("Tabela do anexo inválida: limite_superior ausente ou inválido.")
        if rbt12 <= float(limite):
            aliq_nom = faixa.get("aliquota_nominal")
            pd = faixa.get("parcela_deduzir")
            if not isinstance(aliq_nom, (int, float)) or not isinstance(pd, (int, float)):
                raise ValueError("Tabela do anexo inválida: aliquota_nominal/parcela_deduzir ausente ou inválido.")
            return float(aliq_nom), float(pd), idx

    ultima = tabela_anexo[-1]
    if not isinstance(ultima, dict):
        raise ValueError("Tabela do anexo inválida: ultima faixa inválida.")
    aliq_nom = ultima.get("aliquota_nominal")
    pd = ultima.get("parcela_deduzir")
    if not isinstance(aliq_nom, (int, float)) or not isinstance(pd, (int, float)):
        raise ValueError("Tabela do anexo inválida: aliquota_nominal/parcela_deduzir ausente ou inválido.")
    return float(aliq_nom), float(pd), len(tabela_anexo)


def aliquota_efetiva_simples(rbt12: float, aliq_nom: float, pd: float) -> float:
    """Calcula aliquota efetiva do Simples: (RBT12*AliqNom - PD) / RBT12."""
    if rbt12 <= 0:
        raise ValueError("rbt12 deve ser maior que zero.")
    efetiva = ((rbt12 * aliq_nom) - pd) / rbt12
    return max(0.0, efetiva)


def _partilha_por_faixa(
    faixa_payload: Dict[str, Any],
    *,
    ruleset_id: str,
    regime: str,
) -> Dict[str, float]:
    percentuais_raw = faixa_payload.get("percentuais_partilha")
    if not isinstance(percentuais_raw, dict):
        raise _ruleset_error(
            ruleset_id,
            "simples_tables.json",
            "percentuais_partilha",
            regime,
            "Nao e possivel calcular partilha do DAS",
            "objeto ausente/invalid",
        )

    percentuais: Dict[str, float] = {}
    for tributo in TRIBUTOS_DAS:
        if tributo not in percentuais_raw:
            raise _ruleset_error(
                ruleset_id,
                "simples_tables.json",
                f"percentuais_partilha.{tributo}",
                regime,
                "Nao e possivel calcular partilha do DAS",
                "tributo ausente na faixa",
            )
        value = percentuais_raw[tributo]
        if not isinstance(value, (int, float)):
            raise _ruleset_error(
                ruleset_id,
                "simples_tables.json",
                f"percentuais_partilha.{tributo}",
                regime,
                "Nao e possivel calcular partilha do DAS",
                "percentual nao numerico",
            )
        numeric = float(value)
        if numeric < 0:
            raise _ruleset_error(
                ruleset_id,
                "simples_tables.json",
                f"percentuais_partilha.{tributo}",
                regime,
                "Nao e possivel calcular partilha do DAS",
                "percentual negativo",
            )
        percentuais[tributo] = numeric

    soma = sum(percentuais.values())
    if abs(soma - 1.0) > PARTILHA_SOMA_TOLERANCIA:
        raise _ruleset_error(
            ruleset_id,
            "simples_tables.json",
            "percentuais_partilha",
            regime,
            "Nao e possivel calcular partilha do DAS",
            f"soma dos percentuais invalida: {soma}",
        )

    return percentuais


def _breakdown_das(percentuais: Dict[str, float], imposto_total: float) -> Dict[str, float]:
    breakdown: Dict[str, float] = {}
    for tributo, percentual in percentuais.items():
        breakdown[tributo] = imposto_total * percentual
    return breakdown


def imposto_simples_tabelado(
    receita_base: float,
    rbt12: float,
    anexo: str,
    tabelas: Dict[str, Any],
    fator_r: Optional[float] = None,
    folha_12m: Optional[float] = None,
    limite_elegibilidade: Optional[float] = None,
    fator_r_limite: Optional[float] = None,
    ruleset_id: str = "N/D",
) -> Tuple[float, Dict[str, Any]]:
    """
    Calcula Simples Nacional tabelado por anexo/faixa com suporte a Fator R (III/V)
    e retorna partilha estimada do DAS por tributo.
    """
    regime = "Simples Nacional"
    if receita_base <= 0:
        raise ValueError("receita_base deve ser maior que zero.")
    if rbt12 <= 0:
        raise ValueError("rbt12 deve ser maior que zero.")
    if not isinstance(tabelas, dict):
        raise _ruleset_error(
            ruleset_id,
            "simples_tables.json",
            "anexos",
            regime,
            "Nao e possivel calcular DAS",
            "arquivo invalido",
        )

    anexos = _required_object(
        tabelas,
        "anexos",
        ruleset_id=ruleset_id,
        arquivo="simples_tables.json",
        regime=regime,
        impacto="Nao e possivel calcular DAS",
    )
    if limite_elegibilidade is None:
        limite_elegibilidade = _required_number(
            tabelas,
            "limite_elegibilidade_simples",
            ruleset_id=ruleset_id,
            arquivo="simples_tables.json",
            regime=regime,
            impacto="Nao e possivel validar elegibilidade do Simples",
        )
    if fator_r_limite is None:
        fator_r_limite = _required_number(
            tabelas,
            "fator_r_limite",
            ruleset_id=ruleset_id,
            arquivo="simples_tables.json",
            regime=regime,
            impacto="Nao e possivel determinar anexo III/V",
        )

    anexo_informado = (anexo or "").strip().upper().replace("-", "/")
    anexo_aplicado = anexo_informado
    fator_r_calculado: Optional[float] = None

    if anexo_informado == "III/V":
        if fator_r is not None:
            fator_r_calculado = float(fator_r)
        elif folha_12m is not None:
            fator_r_calculado = float(folha_12m) / rbt12
        else:
            raise ValueError("Informe fator_r ou folha_12m para anexo III/V.")
        anexo_aplicado = "III" if fator_r_calculado >= fator_r_limite else "V"

    if anexo_aplicado not in anexos:
        raise _ruleset_error(
            ruleset_id,
            "simples_tables.json",
            f"anexos.{anexo_aplicado}",
            regime,
            "Nao e possivel calcular DAS",
            "anexo nao encontrado",
        )

    tabela_anexo = anexos.get(anexo_aplicado)
    if not isinstance(tabela_anexo, list) or not tabela_anexo:
        raise _ruleset_error(
            ruleset_id,
            "simples_tables.json",
            f"anexos.{anexo_aplicado}",
            regime,
            "Nao e possivel calcular DAS",
            "tabela de faixas invalida",
        )

    aliq_nom, pd, faixa = escolher_faixa_por_rbt12(tabela_anexo, rbt12)
    faixa_payload = tabela_anexo[faixa - 1]
    if not isinstance(faixa_payload, dict):
        raise _ruleset_error(
            ruleset_id,
            "simples_tables.json",
            f"anexos.{anexo_aplicado}[{faixa - 1}]",
            regime,
            "Nao e possivel calcular DAS",
            "faixa invalida",
        )

    aliq_efetiva = aliquota_efetiva_simples(rbt12, aliq_nom, pd)
    imposto = receita_base * aliq_efetiva
    breakdown_percentuais = _partilha_por_faixa(faixa_payload, ruleset_id=ruleset_id, regime=regime)
    breakdown_das = _breakdown_das(breakdown_percentuais, imposto)

    detalhes: Dict[str, Any] = {
        "anexo_informado": anexo_informado,
        "anexo_aplicado": anexo_aplicado,
        "faixa": faixa,
        "aliquota_nominal": aliq_nom,
        "parcela_deduzir": pd,
        "aliquota_efetiva": aliq_efetiva,
        "rbt12": rbt12,
        "receita_base_periodo": receita_base,
        "limite_elegibilidade_simples": float(limite_elegibilidade),
        "fator_r_limite": float(fator_r_limite),
        "breakdown_percentuais": breakdown_percentuais,
        "breakdown_das": breakdown_das,
    }
    if fator_r_calculado is not None:
        detalhes["fator_r"] = fator_r_calculado
    elif fator_r is not None:
        detalhes["fator_r"] = float(fator_r)
    if folha_12m is not None:
        detalhes["folha_12m"] = float(folha_12m)
    if rbt12 > float(limite_elegibilidade):
        detalhes["alerta_elegibilidade"] = (
            f"RBT12 acima de R$ {float(limite_elegibilidade):,.2f}: possível desenquadramento/limite Simples."
        )

    return imposto, detalhes


def imposto_lucro_presumido(
    receita_anual: float,
    pis: float,
    cofins: float,
    percentual_presuncao: float,
    limite_adicional_irpj: float,
    irpj: float,
    adicional_irpj: float,
    csll: float,
) -> float:
    pis_cofins = receita_anual * (pis + cofins)

    base_presumida = receita_anual * percentual_presuncao
    irpj_calc = base_presumida * irpj
    excedente_adicional = max(0.0, base_presumida - limite_adicional_irpj)
    adicional_calc = excedente_adicional * adicional_irpj
    csll_calc = base_presumida * csll

    return pis_cofins + irpj_calc + adicional_calc + csll_calc


def imposto_lucro_real_estimado(
    receita_anual: float,
    margem_lucro: float,
    irpj: float,
    csll: float,
) -> float:
    lucro_estimado = receita_anual * margem_lucro
    return (lucro_estimado * irpj) + (lucro_estimado * csll)


def imposto_lucro_real_estimado_completo(
    *,
    receita_anual: float,
    receita_base_periodo: float,
    margem_lucro: float,
    irpj: float,
    csll: float,
    pis_nao_cumulativo: float,
    cofins_nao_cumulativo: float,
    despesas_creditaveis: Optional[float] = None,
    percentual_credito_estimado: Optional[float] = None,
) -> Tuple[float, Dict[str, Any]]:
    """
    Calcula Lucro Real estimado com componentes:
    - IRPJ/CSLL sobre lucro estimado por margem
    - PIS/COFINS nao cumulativo sobre base de receita
    - Credito opcional informado (despesas ou percentual estimado)
    """
    if receita_anual <= 0:
        raise ValueError("receita_anual deve ser maior que zero.")
    if receita_base_periodo <= 0:
        raise ValueError("receita_base_periodo deve ser maior que zero.")
    if margem_lucro < 0:
        raise ValueError("margem_lucro nao pode ser negativa.")
    if despesas_creditaveis is not None and float(despesas_creditaveis) < 0:
        raise ValueError(
            "regime=Lucro Real | impacto=Nao e possivel calcular credito de PIS/COFINS | "
            "detalhe=despesas_creditaveis deve ser >= 0"
        )
    if percentual_credito_estimado is not None and not (0.0 <= float(percentual_credito_estimado) <= 1.0):
        raise ValueError(
            "regime=Lucro Real | impacto=Nao e possivel calcular credito de PIS/COFINS | "
            "detalhe=percentual_credito_estimado deve estar entre 0 e 1"
        )

    aliquota_pis_cofins = pis_nao_cumulativo + cofins_nao_cumulativo
    lucro_estimado = receita_anual * margem_lucro
    irpj_calc = lucro_estimado * irpj
    csll_calc = lucro_estimado * csll
    debito_pis_cofins = receita_base_periodo * aliquota_pis_cofins

    credito_pis_cofins = 0.0
    criterio_credito = "nao_informado_assumido_zero"
    if despesas_creditaveis is not None:
        credito_pis_cofins = float(despesas_creditaveis) * aliquota_pis_cofins
        criterio_credito = "despesas_creditaveis"
    elif percentual_credito_estimado is not None:
        credito_pis_cofins = (receita_base_periodo * float(percentual_credito_estimado)) * aliquota_pis_cofins
        criterio_credito = "percentual_credito_estimado"

    credito_pis_cofins_original = credito_pis_cofins
    credito_pis_cofins_utilizado = min(credito_pis_cofins_original, debito_pis_cofins)
    credito_limitado_ao_debito = credito_pis_cofins_original > debito_pis_cofins

    pis_cofins_liquido = debito_pis_cofins - credito_pis_cofins_utilizado
    imposto_total = irpj_calc + csll_calc + pis_cofins_liquido

    return imposto_total, {
        "lucro_estimado": lucro_estimado,
        "irpj_calculado": irpj_calc,
        "csll_calculado": csll_calc,
        "aliquota_pis_nao_cumulativo": pis_nao_cumulativo,
        "aliquota_cofins_nao_cumulativo": cofins_nao_cumulativo,
        "debito_pis_cofins_nao_cumulativo": debito_pis_cofins,
        "credito_pis_cofins": credito_pis_cofins_utilizado,
        "credito_pis_cofins_original": credito_pis_cofins_original,
        "credito_pis_cofins_utilizado": credito_pis_cofins_utilizado,
        "credito_limitado_ao_debito": credito_limitado_ao_debito,
        "pis_cofins_nao_cumulativo_liquido": pis_cofins_liquido,
        "criterio_credito_pis_cofins": criterio_credito,
        "receita_base_periodo": receita_base_periodo,
    }
